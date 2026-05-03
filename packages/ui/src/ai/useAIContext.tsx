"use client";

import axios from "axios";
import { useCallback, useEffect, useState } from "react";

import type { AIChatMessage, AIChatResponse, AIScope } from "./types";

interface State {
  messages: AIChatMessage[];
  loading: boolean;
  error: string | null;
  hasCredential: boolean | null;
}

/**
 * AI session hook.
 *
 * - Probes `/api/ai/credentials` once to know whether AI is wired for the
 *   tenant; lets callers render a friendly empty state otherwise.
 * - `send(text)` posts to `/api/ai/chat` with the provided scope.
 */
export function useAIContext(scope: AIScope) {
  const [state, setState] = useState<State>({
    messages: [],
    loading: false,
    error: null,
    hasCredential: null,
  });

  useEffect(() => {
    let cancelled = false;
    axios
      .get("/api/ai/credentials")
      .then((res) => {
        if (cancelled) return;
        const items = res.data?.items ?? [];
        setState((s) => ({ ...s, hasCredential: items.length > 0 }));
      })
      .catch(() => {
        if (!cancelled) setState((s) => ({ ...s, hasCredential: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      setState((s) => ({
        ...s,
        loading: true,
        error: null,
        messages: [...s.messages, { role: "user", content: text }],
      }));
      try {
        const messages: AIChatMessage[] = [
          ...state.messages,
          { role: "user", content: text },
        ];
        const res = await axios.post<AIChatResponse>("/api/ai/chat", {
          scope,
          messages,
        });
        setState((s) => ({
          ...s,
          loading: false,
          messages: [
            ...s.messages,
            { role: "assistant", content: res.data.text || "" },
          ],
        }));
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
          ?.detail;
        const msg = typeof detail === "string" ? detail : "AI request failed";
        setState((s) => ({ ...s, loading: false, error: msg }));
      }
    },
    [scope, state.messages],
  );

  return { ...state, send };
}
