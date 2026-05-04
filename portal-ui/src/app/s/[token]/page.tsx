"use client";

import { Alert, Badge, Container, Group, Loader, Paper, Stack, Text, Title } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useRealtimeShareResource } from "@/lib/realtime";

interface ResourceView {
  resource_model: string;
  resource_id: string;
  permissions: string[];
  /** Surfaced by `/api/portal/exchange` so the realtime hook can build the topic. */
  tenant_id: string;
  payload: Record<string, unknown>;
}

export default function ShareLinkPage({ params }: { params: { token: string } }) {
  const [view, setView] = useState<ResourceView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  // "live" badge — flashes on every realtime event so the visitor knows the
  // page reflects the latest state without a manual reload.
  const [liveAt, setLiveAt] = useState<number | null>(null);

  const reload = useCallback(() => setRefreshTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/portal/exchange?token=${encodeURIComponent(params.token)}`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail ?? "Invalid or expired share link");
        }
        return (await r.json()) as ResourceView;
      })
      .then((data) => {
        if (!cancelled) setView(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [params.token, refreshTick]);

  // Subscribe to realtime updates for this resource. When the backend
  // emits `record.updated`, refetch `/api/portal/exchange` so the page
  // reflects the new payload without forcing the visitor to reload.
  useRealtimeShareResource(
    {
      shareToken: params.token,
      tenantId: view?.tenant_id,
      model: view?.resource_model,
      recordId: view?.resource_id,
    },
    () => {
      setLiveAt(Date.now());
      reload();
    },
  );

  return (
    <Container size="md" py="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>Shared resource</Title>
          {liveAt ? (
            <Badge color="green" variant="light">
              live · last update {new Date(liveAt).toLocaleTimeString()}
            </Badge>
          ) : null}
        </Group>
        {error ? <Alert color="red" title="Cannot open the share link">{error}</Alert> : null}
        {!error && !view ? <Loader /> : null}
        {view ? (
          <Paper withBorder p="md">
            <Text fw={600}>
              {view.resource_model} / {view.resource_id}
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Permissions: {view.permissions.join(", ")}
            </Text>
            <pre style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
              {JSON.stringify(view.payload, null, 2)}
            </pre>
          </Paper>
        ) : null}
      </Stack>
    </Container>
  );
}
