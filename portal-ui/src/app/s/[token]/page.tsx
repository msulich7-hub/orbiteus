"use client";

import { Alert, Container, Loader, Paper, Stack, Text, Title } from "@mantine/core";
import { useEffect, useState } from "react";

interface ResourceView {
  resource_model: string;
  resource_id: string;
  permissions: string[];
  payload: Record<string, unknown>;
}

export default function ShareLinkPage({ params }: { params: { token: string } }) {
  const [view, setView] = useState<ResourceView | null>(null);
  const [error, setError] = useState<string | null>(null);

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
  }, [params.token]);

  return (
    <Container size="md" py="xl">
      <Stack gap="md">
        <Title order={2}>Shared resource</Title>
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
