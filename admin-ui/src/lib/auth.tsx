"use client";
/**
 * Auth context — single fetch of `/api/auth/me`, exposed via `useAuth()`.
 *
 * The browser session is established by the httpOnly cookie set by
 * `/api/auth/login` (ADR-0017). Most components don't care about the user
 * id; the realtime layer however needs `tenant_id` to build topic strings
 * (`tenant:{tid}:model:{model}:list`), so we fetch the profile once at
 * mount and cache it in context for the rest of the tree.
 */
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  tenant_id: string | null;
  is_superadmin: boolean;
  is_active: boolean;
  language: string;
  timezone: string;
  totp_enabled: boolean;
  last_login: string | null;
}

export interface AuthState {
  user: AuthUser | null;
  /** True once the client effect has resolved (ok or fail). Consumers
   *  should gate any logic that depends on `user` on this flag — same
   *  pattern as `useBranding().hydrated`. */
  hydrated: boolean;
}

const DEFAULT: AuthState = { user: null, hydrated: false };
const AuthContext = createContext<AuthState>(DEFAULT);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(DEFAULT);

  useEffect(() => {
    let cancelled = false;
    api.get<AuthUser>("/auth/me", { skipGlobalErrorToast: true })
      .then(({ data }) => {
        if (!cancelled) setState({ user: data, hydrated: true });
      })
      .catch(() => {
        // 401 → middleware will redirect on the next nav anyway.
        if (!cancelled) setState({ user: null, hydrated: true });
      });
    return () => { cancelled = true; };
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
