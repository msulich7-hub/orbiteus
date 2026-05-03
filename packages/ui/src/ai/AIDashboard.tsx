"use client";

import { Button, Group, Loader, Paper, Stack, Text, TextInput, Title } from "@mantine/core";
import axios from "axios";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { AIScope } from "./types";

interface Props {
  scope: AIScope;
  initialPrompt?: string;
}

interface DashboardSpec {
  title: string;
  chart_type: "bar" | "line" | "pie";
  x_axis: string;
  y_axis: string;
  data: Array<Record<string, number | string>>;
}

/**
 * Prompt → chart spec → recharts. The backend returns a stable JSON shape;
 * the UI never executes raw SQL.
 */
export function AIDashboard({ scope, initialPrompt = "" }: Props) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [spec, setSpec] = useState<DashboardSpec | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post<DashboardSpec>("/api/ai/dashboard", { scope, prompt });
      setSpec(res.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to generate dashboard");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Paper p="md" withBorder>
      <Stack gap="sm">
        <Group gap="xs" align="end">
          <TextInput
            flex={1}
            placeholder="Describe the chart you want…"
            value={prompt}
            onChange={(e) => setPrompt(e.currentTarget.value)}
          />
          <Button onClick={run} loading={loading} color="dark">
            Generate
          </Button>
        </Group>
        {error ? <Text size="sm" c="red">{error}</Text> : null}
        {loading ? <Loader size="sm" /> : null}
        {spec ? (
          <Stack gap="xs">
            <Title order={5}>{spec.title}</Title>
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <BarChart data={spec.data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={spec.x_axis} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey={spec.y_axis} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}
