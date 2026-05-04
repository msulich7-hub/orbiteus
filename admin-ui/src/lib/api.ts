import axios from "axios";
import { notifications } from "@mantine/notifications";

/**
 * Shared axios instance.
 *
 * - `withCredentials: true` so the browser sends the `orbiteus_token` cookie
 *   on same-origin /api/* calls (Next rewrites land both apps on the same
 *   origin via `next.config.js`).
 * - No request interceptor injects an Authorization header any more — the
 *   backend reads JWT from the httpOnly cookie set by /api/auth/login.
 *   See docs/adr/0017-httponly-cookie-session.md.
 */
export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

// Legacy localStorage cleanup: remove any token left over from the previous
// (pre-cookie) auth model so a returning user doesn't carry stale state.
if (typeof window !== "undefined") {
  try {
    window.localStorage.removeItem("token");
  } catch {
    /* ignore */
  }
}

function toastDetail(err: { response?: { data?: { detail?: unknown } } }): string {
  const d = err.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg);
  return "Request failed";
}

/** Must stay aligned with `src/proxy.ts` — pages where 401 is expected (stale cookie + /auth/me). */
function isPublicAuthSurface(pathname: string): boolean {
  if (pathname === "/login" || pathname === "/welcome" || pathname === "/forgot-password") {
    return true;
  }
  return pathname.startsWith("/reset/");
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const skip = Boolean(err.config?.skipGlobalErrorToast);

    if (status === 401 && typeof window !== "undefined") {
      // A present-but-expired `orbiteus_token` still passes the Edge proxy
      // (cookie existence only). `/auth/me` then returns 401; redirecting
      // from `/login` would reload forever — only bounce off protected UI.
      const path = window.location.pathname;
      if (!isPublicAuthSurface(path)) {
        const next = `${path}${window.location.search}`;
        const loginUrl = next && next !== "/login"
          ? `/login?next=${encodeURIComponent(next)}`
          : "/login";
        window.location.href = loginUrl;
      }
      return Promise.reject(err);
    }

    if (!skip && typeof window !== "undefined") {
      if (!err.response) {
        notifications.show({
          title: "Network error",
          message: "Connection lost. Check your network and try again.",
          color: "red",
        });
      } else if (status === 403) {
        notifications.show({
          title: "Access denied",
          message: toastDetail(err),
          color: "red",
        });
      } else if (status === 404) {
        notifications.show({
          title: "Not found",
          message: toastDetail(err),
          color: "orange",
        });
      }
    }

    return Promise.reject(err);
  }
);

export async function fetchList(resource: string, params?: Record<string, unknown>) {
  const { data } = await api.get(`/${resource}`, { params });
  return data; // { items, total, offset, limit }
}

export async function fetchOne(resource: string, id: string) {
  const { data } = await api.get(`/${resource}/${id}`);
  return data;
}

export async function createRecord(resource: string, payload: unknown) {
  const { data } = await api.post(`/${resource}`, payload);
  return data;
}

export async function updateRecord(resource: string, id: string, payload: unknown) {
  const { data } = await api.put(`/${resource}/${id}`, payload);
  return data;
}

export async function deleteRecord(resource: string, id: string) {
  await api.delete(`/${resource}/${id}`);
}

export async function fetchUiConfig(): Promise<UiConfig> {
  const { data } = await api.get("/base/ui-config");
  return data;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FieldMeta {
  name: string;
  type:
    | "text"
    | "email"
    | "tel"
    | "number"
    | "textarea"
    | "select"
    | "boolean"
    | "date"
    | "many2one"
    | "monetary"
    | "tags";
  required: boolean;
  label: string;
  /** Target model for many2one, e.g. crm.customer */
  relation?: string;
  options?: { value: string; label: string }[];
  /** ISO-4217 code for monetary fields (e.g. "PLN", "EUR"). */
  currency_code?: string;
}

export interface ModelConfig {
  name: string;
  label: string;
  fields: FieldMeta[];
  views: {
    list: string | null;
    form: string | null;
    kanban: string | null;
    search: string | null;
    calendar: string | null;
    graph: string | null;
  };
}

export interface ModuleConfig {
  name: string;
  label: string;
  category: string;
  models: ModelConfig[];
}

export interface UiConfig {
  modules: ModuleConfig[];
}
