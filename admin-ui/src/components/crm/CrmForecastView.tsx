"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";
import EmptyState from "@/components/EmptyState";

interface Pipeline {
  id: string;
  name: string;
  is_default?: boolean;
}

interface ForecastStageBreakdown {
  stage_id: string;
  stage_name: string;
  weighted_revenue: number;
  deal_count: number;
}

interface ForecastMonth {
  month: string;
  label: string;
  weighted_revenue: number;
  raw_revenue: number;
  deal_count: number;
  by_stage: ForecastStageBreakdown[];
}

interface ForecastResponse {
  pipeline_id: string | null;
  currency: string;
  months: ForecastMonth[];
  total_weighted: number;
  total_raw: number;
}

interface Props {
  defaultPipelineId?: string | null;
}

export default function CrmForecastView({ defaultPipelineId }: Props) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [pipelineId, setPipelineId] = useState<string | null>(defaultPipelineId ?? null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadForecast = useCallback(async (selectedPipelineId?: string | null) => {
    const params: Record<string, string | number> = { months_ahead: 6 };
    if (selectedPipelineId) params.pipeline_id = selectedPipelineId;
    const { data } = await api.get<ForecastResponse>("/crm/leads/forecast", { params });
    setForecast(data);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      setError("");
      try {
        const pipeRes = await api.get("/crm/pipeline", { params: { limit: 50 } });
        const pipeItems: Pipeline[] = pipeRes.data.items ?? pipeRes.data ?? [];
        if (!cancelled) setPipelines(pipeItems);

        const initialPipeline =
          defaultPipelineId
          ?? pipeItems.find((p) => p.is_default)?.id
          ?? pipeItems[0]?.id
          ?? null;
        if (!cancelled && initialPipeline) setPipelineId(initialPipeline);

        await loadForecast(initialPipeline);
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message: string }).message ?? "Failed to load forecast");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void init();
    return () => { cancelled = true; };
  }, [defaultPipelineId, loadForecast]);

  const handlePipelineChange = async (value: string | null) => {
    setPipelineId(value);
    setLoading(true);
    setError("");
    try {
      await loadForecast(value);
    } catch (e: unknown) {
      setError((e as { message: string }).message ?? "Failed to load forecast");
    } finally {
      setLoading(false);
    }
  };

  const stageColumns = useMemo(() => {
    const stages = new Map<string, string>();
    for (const month of forecast?.months ?? []) {
      for (const stage of month.by_stage) {
        stages.set(stage.stage_id, stage.stage_name);
      }
    }
    return Array.from(stages.entries()).map(([id, name]) => ({ id, name }));
  }, [forecast]);

  const stageColumnTotals = useMemo(() => {
    const totals = new Map<string, number>();
    for (const month of forecast?.months ?? []) {
      for (const stage of month.by_stage) {
        totals.set(
          stage.stage_id,
          (totals.get(stage.stage_id) ?? 0) + stage.weighted_revenue,
        );
      }
    }
    return totals;
  }, [forecast]);

  const currency = forecast?.currency ?? "PLN";
  const hasDeals = (forecast?.months ?? []).some((m) => m.deal_count > 0);
  const months = forecast?.months ?? [];

  if (loading && !forecast) {
    return (
      <Stack gap="md">
        <Skeleton height={80} radius="md" />
        <Skeleton height={240} radius="md" />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} color="red" title="Forecast unavailable">
        {error}
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        {pipelines.length > 1 ? (
          <Select
            label="Pipeline"
            data={pipelines.map((p) => ({ value: p.id, label: p.name }))}
            value={pipelineId}
            onChange={handlePipelineChange}
            w={280}
          />
        ) : (
          <div />
        )}
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <Paper withBorder p="lg" radius="md">
          <Text size="sm" c="dimmed" tt="uppercase" fw={600}>
            Total weighted
          </Text>
          <Title order={2} mt={4}>
            {formatMoney(forecast?.total_weighted ?? 0, currency)}
          </Title>
          <Text size="sm" c="dimmed" mt="xs">
            Raw pipeline: {formatMoney(forecast?.total_raw ?? 0, currency)}
          </Text>
        </Paper>
        <Paper withBorder p="lg" radius="md">
          <Text size="sm" c="dimmed">
            Horizon
          </Text>
          <Text fw={600} mt={4}>
            Next 6 months
          </Text>
          <Text size="sm" c="dimmed" mt="xs">
            Open deals by expected close date
          </Text>
        </Paper>
      </SimpleGrid>

      {!hasDeals && (
        <EmptyState
          title="No forecast data"
          description="Add open deals with expected close dates in the selected pipeline."
        />
      )}

      <Paper withBorder radius="md" p="md">
        <Table
          data-testid="crm-forecast-table"
          striped
          highlightOnHover
          withTableBorder
          withColumnBorders
        >
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Month</Table.Th>
              {stageColumns.map((stage) => (
                <Table.Th key={stage.id} ta="right">
                  {stage.name}
                </Table.Th>
              ))}
              <Table.Th ta="right">Weighted</Table.Th>
              <Table.Th ta="right">Raw</Table.Th>
              <Table.Th ta="right">Deals</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {months.map((month) => (
              <Table.Tr key={month.month}>
                <Table.Td>{month.label}</Table.Td>
                {stageColumns.map((stage) => {
                  const cell = month.by_stage.find((s) => s.stage_id === stage.id);
                  return (
                    <Table.Td key={stage.id} ta="right">
                      {cell ? formatMoney(cell.weighted_revenue, currency) : "—"}
                    </Table.Td>
                  );
                })}
                <Table.Td ta="right" fw={600}>
                  {formatMoney(month.weighted_revenue, currency)}
                </Table.Td>
                <Table.Td ta="right" c="dimmed">
                  {formatMoney(month.raw_revenue, currency)}
                </Table.Td>
                <Table.Td ta="right">{month.deal_count}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
          {stageColumns.length > 0 && (
            <Table.Tfoot>
              <Table.Tr>
                <Table.Th>Stage totals</Table.Th>
                {stageColumns.map((stage) => (
                  <Table.Th key={stage.id} ta="right">
                    {formatMoney(stageColumnTotals.get(stage.id) ?? 0, currency)}
                  </Table.Th>
                ))}
                <Table.Th ta="right">
                  {formatMoney(forecast?.total_weighted ?? 0, currency)}
                </Table.Th>
                <Table.Th ta="right">
                  {formatMoney(forecast?.total_raw ?? 0, currency)}
                </Table.Th>
                <Table.Th ta="right" />
              </Table.Tr>
            </Table.Tfoot>
          )}
        </Table>
      </Paper>
    </Stack>
  );
}
