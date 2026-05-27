"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  ShpComposePreview,
  ShpDispatchStatus,
  ShpDispatchWorkspace,
} from "./shpTypes";

interface UseShpComposePreviewResult {
  preview: ShpComposePreview | null;
  dispatchStatus: ShpDispatchStatus | null;
  workspace: ShpDispatchWorkspace | null;
  loading: boolean;
  error: string;
  refetch: () => Promise<void>;
}

/**
 * Loads compose-preview for an IFS shipment id.
 * Optional dispatch-status poll and workspace when `dispatch_id` is present.
 * Backend routes may 404 until SHP-004..007 — failures are non-fatal.
 */
export function useShpComposePreview(
  ifsShipmentId: string | null,
  options?: { pollDispatchStatus?: boolean; pollMs?: number },
): UseShpComposePreviewResult {
  const [preview, setPreview] = useState<ShpComposePreview | null>(null);
  const [dispatchStatus, setDispatchStatus] = useState<ShpDispatchStatus | null>(null);
  const [workspace, setWorkspace] = useState<ShpDispatchWorkspace | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!ifsShipmentId) {
      setPreview(null);
      setDispatchStatus(null);
      setWorkspace(null);
      setError("");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const { data } = await api.get<ShpComposePreview>(
        `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/compose-preview`,
        { skipGlobalErrorToast: true },
      );
      setPreview(data ?? null);

      const dispatchId = data?.dispatch_id;
      if (dispatchId) {
        try {
          const ws = await api.get<ShpDispatchWorkspace>(
            `/shipping/dispatch/${dispatchId}/workspace`,
            { skipGlobalErrorToast: true },
          );
          setWorkspace(ws.data ?? null);
        } catch {
          setWorkspace(null);
        }
      } else {
        setWorkspace(null);
      }

      if (options?.pollDispatchStatus) {
        try {
          const st = await api.get<ShpDispatchStatus>(
            `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch-status`,
            { skipGlobalErrorToast: true },
          );
          setDispatchStatus(st.data ?? null);
        } catch {
          setDispatchStatus(null);
        }
      }
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        setError("Podgląd kompozycji nie jest jeszcze dostępny (backend SHP-004).");
      } else {
        setError(
          (e as { message?: string })?.message ?? "Nie udało się wczytać podglądu wysyłki.",
        );
      }
      setPreview(null);
      setWorkspace(null);
      setDispatchStatus(null);
    } finally {
      setLoading(false);
    }
  }, [ifsShipmentId, options?.pollDispatchStatus]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!options?.pollDispatchStatus || !ifsShipmentId) return;
    const terminal = new Set(["dispatched", "failed", "queued"]);
    const queueState = dispatchStatus?.queue_state ?? preview?.state;
    if (queueState && terminal.has(String(queueState))) return;

    const ms = options.pollMs ?? 4000;
    const id = window.setInterval(() => {
      void api
        .get<ShpDispatchStatus>(
          `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch-status`,
          { skipGlobalErrorToast: true },
        )
        .then((res) => setDispatchStatus(res.data ?? null))
        .catch(() => {
          /* endpoint optional */
        });
    }, ms);
    return () => window.clearInterval(id);
  }, [
    dispatchStatus?.queue_state,
    ifsShipmentId,
    options?.pollDispatchStatus,
    options?.pollMs,
    preview?.state,
  ]);

  return {
    preview,
    dispatchStatus,
    workspace,
    loading,
    error,
    refetch: load,
  };
}
