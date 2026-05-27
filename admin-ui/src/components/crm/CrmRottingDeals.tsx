"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Badge,
  Group,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
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

interface RottingLead {
  lead_id: string;
  name: string;
  stage_name: string;
  days_in_stage: number;
  rotting_days: number;
  expected_revenue: number;
}

interface RottingResponse {
  count: number;
  leads: RottingLead[];
}

interface Props {
  defaultPipelineId?: string | null;
}

export default function CrmRottingDeals({ defaultPipelineId }: Props) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [pipelineId, setPipelineId] = useState<string | null>(defaultPipelineId ?? null);
  const [leads, setLeads] = useState<RottingLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRotting = useCallback(async (selectedPipelineId?: string | null) => {
    const params = selectedPipelineId ? { pipeline_id: selectedPipelineId } : undefined;
    const { data } = await api.get<RottingResponse>("/crm/leads/rotting", { params });
    setLeads(data.leads ?? []);
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

        await loadRotting(initialPipeline);
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message: string }).message ?? "Failed to load rotting deals");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [defaultPipelineId, loadRotting]);

  async function onPipelineChange(value: string | null) {
    if (!value) return;
    setPipelineId(value);
    setLoading(true);
    setError("");
    try {
      await loadRotting(value);
    } catch (e: unknown) {
      setError((e as { message: string }).message ?? "Failed to load rotting deals");
    } finally {
      setLoading(false);
    }
  }

  if (loading && leads.length === 0) {
    return (
      <Stack gap="md">
        <Skeleton height={36} radius="sm" />
        <Skeleton height={200} radius="sm" />
      </Stack>
    );
  }

  if (error) {
    return <Alert icon={<IconAlertCircle size={16} />} color="red">{error}</Alert>;
  }

  return (
    <Stack gap="md">
      {pipelines.length > 0 && (
        <Select
          label="Pipeline"
          data={pipelines.map((p) => ({ value: p.id, label: p.name }))}
          value={pipelineId}
          onChange={onPipelineChange}
          style={{ maxWidth: 280 }}
          size="sm"
          allowDeselect={false}
        />
      )}

      {leads.length === 0 ? (
        <EmptyState
          title="No rotting deals"
          description="All deals are within their stage time limits."
        />
      ) : (
        <>
          <Text size="sm" c="dimmed">
            {leads.length} deal{leads.length === 1 ? "" : "s"} exceeding stage rotting threshold
          </Text>

          <ScrollArea visibleFrom="sm">
            <Table highlightOnHover striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Deal</Table.Th>
                  <Table.Th>Stage</Table.Th>
                  <Table.Th>Days in stage</Table.Th>
                  <Table.Th>Expected revenue</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {leads.map((lead) => (
                  <Table.Tr key={lead.lead_id}>
                    <Table.Td>
                      <Text
                        component={Link}
                        href={`/crm/lead/${lead.lead_id}`}
                        size="sm"
                        fw={600}
                        c="inherit"
                        style={{ textDecoration: "none" }}
                      >
                        {lead.name || "—"}
                      </Text>
                    </Table.Td>
                    <Table.Td>{lead.stage_name}</Table.Td>
                    <Table.Td>
                      <Group gap={6}>
                        <Text size="sm">{lead.days_in_stage}d</Text>
                        <Badge size="xs" color="orange" variant="light">
                          limit {lead.rotting_days}d
                        </Badge>
                      </Group>
                    </Table.Td>
                    <Table.Td>{formatMoney(lead.expected_revenue)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md" hiddenFrom="sm">
            {leads.map((lead) => (
              <Paper key={lead.lead_id} p="md" withBorder>
                <Stack gap="xs">
                  <Text
                    component={Link}
                    href={`/crm/lead/${lead.lead_id}`}
                    size="sm"
                    fw={600}
                    c="inherit"
                    style={{ textDecoration: "none" }}
                  >
                    {lead.name || "—"}
                  </Text>
                  <Group gap="xs">
                    <Badge size="sm" variant="light" color="blue">
                      {lead.stage_name}
                    </Badge>
                    <Badge size="sm" variant="light" color="orange">
                      {lead.days_in_stage}d / {lead.rotting_days}d
                    </Badge>
                  </Group>
                  <Text size="sm" c="dimmed">
                    {formatMoney(lead.expected_revenue)}
                  </Text>
                </Stack>
              </Paper>
            ))}
          </SimpleGrid>
        </>
      )}
    </Stack>
  );
}
