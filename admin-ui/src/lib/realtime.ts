"use client";
/**
 * SSE client for `/api/realtime/subscribe` (ADR-0006, ADR-0014).
 *
 * Backend topic grammar (docs/11-realtime.md):
 *   tenant:{tenant_id}:model:{model}:list
 *   tenant:{tenant_id}:model:{model}:record:{record_id}
 *
 * Resource → model conversion mirrors `auto_router._model_registry`:
 *   "crm/person"   → "crm.person"
 *   "base/ir-model" → "base.ir-model"
 * (segments use dots between module and the rest, dashes inside `ir-*`.)
 *
 * The session cookie (`orbiteus_token`, ADR-0017) is httpOnly and same-
 * origin, so EventSource sends it automatically — no extra config needed.
 */
import { useEffect, useRef } from "react";
import { useAuth } from "./auth";

export interface RealtimeMessage {
  event: "record.created" | "record.updated" | "record.deleted";
  model: string;
  record_id: string;
  tenant_id: string;
  actor: string | null;
  request_id: string | null;
  ts: string | null;
  diff: Record<string, [unknown, unknown]> | null;
}

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_DELAY_MS = 30_000;

function resourceToModel(resource: string): string {
  // `resource` is the auto-router path segment, e.g. "crm/person" or
  // "base/ir-model". The model name uses a dot for the module / model
  // boundary (matches the keys registered by `auto_router.register_model`).
  const slash = resource.indexOf("/");
  if (slash < 0) return resource;
  return `${resource.slice(0, slash)}.${resource.slice(slash + 1)}`;
}

/**
 * Subscribe to mutations on a specific resource list and call `onChange`
 * every time the backend publishes a `record.created/updated/deleted`
 * event for that model under the user's tenant.
 *
 * No-ops gracefully when the user has no `tenant_id` (e.g. before auth
 * has resolved or for non-tenant-scoped endpoints).
 */
export function useRealtimeList(
  resource: string,
  onChange: (msg: RealtimeMessage) => void,
): void {
  const { user, hydrated } = useAuth();
  // Latest callback in a ref so reconnects don't recreate the EventSource
  // every render (the parent typically rebuilds the closure each render).
  const cbRef = useRef(onChange);
  useEffect(() => { cbRef.current = onChange; }, [onChange]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!hydrated) return;
    if (!user?.tenant_id) return;

    const model = resourceToModel(resource);
    const topic = `tenant:${user.tenant_id}:model:${model}:list`;
    const url = `/api/realtime/subscribe?topic=${encodeURIComponent(topic)}`;

    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      es = new EventSource(url);

      es.addEventListener("message", (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data) as RealtimeMessage;
          cbRef.current(data);
        } catch {
          /* malformed payload — ignore */
        }
      });

      es.addEventListener("open", () => { attempts = 0; });

      es.addEventListener("error", () => {
        // Browser will retry automatically on `error` for transient
        // failures, but we explicitly close + back off so a 401/403
        // doesn't loop hot.
        es?.close();
        es = null;
        if (cancelled) return;
        attempts += 1;
        const delay = Math.min(
          RECONNECT_DELAY_MS * Math.pow(1.5, attempts - 1),
          MAX_RECONNECT_DELAY_MS,
        );
        reconnectTimer = setTimeout(connect, delay);
      });
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      es?.close();
    };
  }, [resource, hydrated, user?.tenant_id]);
}
