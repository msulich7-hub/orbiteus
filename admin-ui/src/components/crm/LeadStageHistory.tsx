"use client";
import { useEffect, useState } from "react";
import {
  Alert,
  Paper,
  Skeleton,
  Stack,
  Text,
  Timeline,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconArrowRight } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { formatListDate } from "@/lib/formatters";
import EmptyState from "@/components/EmptyState";

interface StageHistoryEntry {
  id: string;
  from_stage_id: string | null;
  to_stage_id: string;
  changed_by_id: string | null;
  changed_at: string | null;
}

interface StageHistoryResponse {
  lead_id: string;
  count: number;
  history: StageHistoryEntry[];
}

interface Stage {
  id: string;
  name: string;
}

interface Props {
  leadId: string;
}

function stageLabel(stageId: string | null, stageNames: Record<string, string>): string {
  if (!stageId) return "—";
  return stageNames[stageId] ?? `${stageId.slice(0, 8)}…`;
}

export default function LeadStageHistory({ leadId }: Props) {
  const [history, setHistory] = useState<StageHistoryEntry[]>([]);
  const [stageNames, setStageNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [historyRes, stagesRes] = await Promise.all([
          api.get<StageHistoryResponse>(`/crm/lead/${leadId}/stage-history`),
          api.get("/crm/stage", { params: { limit: 200 } }),
        ]);
        if (cancelled) return;

        const stages: Stage[] = stagesRes.data.items ?? stagesRes.data ?? [];
        const names: Record<string, string> = {};
        stages.forEach((s) => {
          names[s.id] = s.name;
        });
        setStageNames(names);

        const entries = [...(historyRes.data.history ?? [])].sort((a, b) => {
          const ta = a.changed_at ? Date.parse(a.changed_at) : 0;
          const tb = b.changed_at ? Date.parse(b.changed_at) : 0;
          return tb - ta;
        });
        setHistory(entries);
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message: string }).message ?? "Failed to load stage history");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [leadId]);

  return (
    <Paper p="md" withBorder data-testid="crm-stage-history">
      <Stack gap="md">
        <Title order={5}>Stage history</Title>

        {loading && (
          <Stack gap="sm">
            <Skeleton height={48} radius="sm" />
            <Skeleton height={48} radius="sm" />
          </Stack>
        )}

        {!loading && error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red">
            {error}
          </Alert>
        )}

        {!loading && !error && history.length === 0 && (
          <EmptyState
            title="No stage changes"
            description="This deal has not moved between stages yet."
          />
        )}

        {!loading && !error && history.length > 0 && (
          <Timeline active={0} bulletSize={24} lineWidth={2}>
            {history.map((entry) => (
              <Timeline.Item
                key={entry.id}
                title={
                  <Text size="sm" fw={600}>
                    {stageLabel(entry.from_stage_id, stageNames)}
                    {" "}
                    <IconArrowRight
                      size={14}
                      style={{ verticalAlign: "middle", margin: "0 4px" }}
                    />
                    {" "}
                    {stageLabel(entry.to_stage_id, stageNames)}
                  </Text>
                }
              >
                <Text size="xs" c="dimmed">
                  {formatListDate(entry.changed_at)}
                </Text>
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Stack>
    </Paper>
  );
}
