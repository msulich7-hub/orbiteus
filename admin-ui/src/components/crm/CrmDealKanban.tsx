"use client";

import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
  closestCorners,
} from "@dnd-kit/core";import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Group,
  Text,
  Button,
  Stack,
  Paper,
  Badge,
  Skeleton,
  Alert,
  ScrollArea,
  ThemeIcon,
  Select,
  SimpleGrid,
  Chip,
  Modal,
  TextInput,
} from "@mantine/core";
import { IconPlus, IconAlertCircle, IconGripVertical, IconFlame } from "@tabler/icons-react";
import Link from "next/link";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";
import EmptyState from "@/components/EmptyState";
import CrmDealDrawer, { type DealDrawerPreview } from "@/components/crm/CrmDealDrawer";
import CrmCsvButtons from "@/components/crm/CrmCsvButtons";
import RequiredFieldsModal, {
  fieldLabel,
  parseMissingFieldsError,
} from "@/components/crm/RequiredFieldsModal";

interface Pipeline {
  id: string;
  name: string;
  is_default?: boolean;
}

interface KanbanLead {
  id: string;
  name: string;
  expected_revenue: number;
  is_rotting: boolean;
  days_in_stage: number | null;
  organization_name?: string | null;
  person_name?: string | null;
  score?: number;
}

interface KanbanColumnData {
  stage_id: string;
  stage_name: string;
  sequence: number;
  is_won?: boolean;
  is_lost?: boolean;
  count: number;
  expected_revenue: number;
  leads: KanbanLead[];
}

interface KanbanResponse {
  pipeline_id: string | null;
  columns: KanbanColumnData[];
  total_leads: number;
  total_expected_revenue: number;
}

interface PendingLostMove {
  leadId: string;
  lead: KanbanLead;
  sourceStage: string;
  targetStage: string;
  stageName: string;
}

interface PendingRequiredFieldsMove {
  leadId: string;
  lead: KanbanLead;
  sourceStage: string;
  targetStage: string;
  missingFields: string[];
  fromStageName?: string;
}

interface Props {
  createHref?: string;
}

function stageColor(col: KanbanColumnData): string {
  if (col.is_won) return "green";
  if (col.is_lost) return "red";
  return "blue";
}

function DealCard({
  lead,
  stageName,
  isDragging,
  rottingOnly,
  onOpen,
  suppressClickRef,
}: {
  lead: KanbanLead;
  stageName?: string;
  isDragging?: boolean;
  rottingOnly?: boolean;
  onOpen?: (lead: KanbanLead, stageName?: string) => void;
  suppressClickRef?: MutableRefObject<boolean>;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: lead.id,
  });
  const dimmed = rottingOnly && !lead.is_rotting;
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : dimmed ? 0.35 : 1,
    cursor: "grab",
    touchAction: "none" as const,
  };

  const subtitle = [lead.organization_name, lead.person_name].filter(Boolean).join(" · ");

  return (
    <Paper
      ref={setNodeRef}
      style={style}
      p="sm"
      radius="sm"
      withBorder
      data-testid={`crm-kanban-card-${lead.id}`}
      {...attributes}
      {...listeners}
      onClick={() => {
        if (suppressClickRef?.current) return;
        onOpen?.(lead, stageName);
      }}
      styles={{
        root: {
          background: "var(--mantine-color-default)",
          borderColor: lead.is_rotting
            ? "var(--mantine-color-orange-5)"
            : "var(--mantine-color-default-border)",
          boxShadow:
            rottingOnly && lead.is_rotting
              ? "0 0 0 1px var(--mantine-color-orange-5)"
              : undefined,
        },
      }}
    >
      <Group gap="xs" wrap="nowrap" align="flex-start">
        <ThemeIcon
          variant="subtle"
          color="gray"
          size="sm"
          style={{ cursor: "grab", flexShrink: 0, marginTop: 2, pointerEvents: "none" }}
        >
          <IconGripVertical size={14} />
        </ThemeIcon>
        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
          <Text size="sm" fw={600} lineClamp={2}>
            {lead.name || "—"}
          </Text>
          {subtitle && (
            <Text size="xs" c="dimmed" lineClamp={1}>
              {subtitle}
            </Text>
          )}
          <Text size="xs" c="dimmed">
            {formatMoney(lead.expected_revenue)}
          </Text>
          <Group gap={6}>
            {lead.is_rotting && (
              <Badge size="xs" color="orange" variant="light">
                Rotting
              </Badge>
            )}
            {(lead.score ?? 0) > 0 && (
              <Badge
                size="xs"
                variant="filled"
                color={
                  lead.score! >= 80
                    ? "yellow"
                    : lead.score! >= 60
                      ? "green"
                      : lead.score! >= 30
                        ? "blue"
                        : "gray"
                }
              >
                ⚡ {lead.score}
              </Badge>
            )}
            {lead.days_in_stage != null && (
              <Text size="xs" c="dimmed">
                {lead.days_in_stage}d in stage
              </Text>
            )}
          </Group>
        </Stack>
      </Group>
    </Paper>
  );
}

/** Drag preview — no sortable hooks (avoids duplicate id in overlay). */
function DealCardOverlay({ lead }: { lead: KanbanLead }) {
  const subtitle = [lead.organization_name, lead.person_name].filter(Boolean).join(" · ");
  return (
    <Paper
      p="sm"
      radius="sm"
      withBorder
      style={{ cursor: "grabbing", boxShadow: "var(--mantine-shadow-md)", width: 260 }}
      styles={{
        root: {
          background: "var(--mantine-color-default)",
          borderColor: lead.is_rotting
            ? "var(--mantine-color-orange-5)"
            : "var(--mantine-color-default-border)",
        },
      }}
    >
      <Group gap="xs" wrap="nowrap" align="flex-start">
        <ThemeIcon variant="subtle" color="gray" size="sm" style={{ flexShrink: 0, marginTop: 2 }}>
          <IconGripVertical size={14} />
        </ThemeIcon>
        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
          <Text size="sm" fw={600} lineClamp={2}>
            {lead.name || "—"}
          </Text>
          {subtitle && (
            <Text size="xs" c="dimmed" lineClamp={1}>
              {subtitle}
            </Text>
          )}
          <Text size="xs" c="dimmed">
            {formatMoney(lead.expected_revenue)}
          </Text>
        </Stack>
      </Group>
    </Paper>
  );
}

function KanbanColumn({
  column,
  leads,
  activeId,
  rottingOnly,
  onOpenDeal,
  suppressClickRef,
}: {
  column: KanbanColumnData;
  leads: KanbanLead[];
  activeId: string | null;
  rottingOnly?: boolean;
  onOpenDeal?: (lead: KanbanLead, stageName: string) => void;
  suppressClickRef?: MutableRefObject<boolean>;
}) {
  const color = stageColor(column);
  const { setNodeRef, isOver } = useDroppable({ id: column.stage_id });

  return (
    <Stack
      gap="xs"
      style={{ minWidth: 260, maxWidth: 300, flex: "0 0 280px" }}
      data-testid={`crm-kanban-column-${column.stage_id}`}
    >
      <Paper p="xs">
        <Stack gap={4}>
          <Group justify="space-between" wrap="nowrap">
            <Group gap={8} wrap="nowrap" style={{ minWidth: 0 }}>
              <ThemeIcon variant="light" color={color} size={20}>
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 999,
                    background: "currentColor",
                  }}
                />
              </ThemeIcon>
              <Text size="sm" fw={700} lineClamp={1}>
                {column.stage_name}
              </Text>
            </Group>
            <Badge size="sm" variant="light" color="gray">
              {column.count}
            </Badge>
          </Group>
          <Text size="xs" c="dimmed" pl={28}>
            {formatMoney(column.expected_revenue)}
          </Text>
        </Stack>
      </Paper>
      <Paper
        ref={setNodeRef}
        p="xs"
        data-testid={`crm-kanban-drop-${column.stage_id}`}
        style={{
          minHeight: 120,
          background: isOver
            ? "var(--mantine-color-blue-light)"
            : "var(--mantine-color-default-hover)",
          outline: isOver ? "2px dashed var(--mantine-color-blue-5)" : undefined,
          transition: "background 120ms ease, outline 120ms ease",
        }}
      >
        <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          <Stack gap="xs">
            {leads.map((lead) => (
              <DealCard
                key={lead.id}
                lead={lead}
                stageName={column.stage_name}
                isDragging={lead.id === activeId}
                rottingOnly={rottingOnly}
                suppressClickRef={suppressClickRef}
                onOpen={(l, stage) => onOpenDeal?.(l, stage ?? column.stage_name)}
              />
            ))}            {leads.length === 0 && (
              <Text size="xs" c="dimmed" ta="center" py="md">
                Drop a card here
              </Text>
            )}
          </Stack>
        </SortableContext>
      </Paper>
    </Stack>
  );
}

export default function CrmDealKanban({ createHref = "/crm/lead/new" }: Props) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [columns, setColumns] = useState<KanbanColumnData[]>([]);
  const [columnsByStage, setColumnsByStage] = useState<Record<string, KanbanLead[]>>({});
  const [metrics, setMetrics] = useState({ total_leads: 0, total_expected_revenue: 0 });
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeLead, setActiveLead] = useState<KanbanLead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rottingOnly, setRottingOnly] = useState(false);
  const [drawerLead, setDrawerLead] = useState<DealDrawerPreview | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pendingLostMove, setPendingLostMove] = useState<PendingLostMove | null>(null);
  const [pendingRequiredFields, setPendingRequiredFields] =
    useState<PendingRequiredFieldsMove | null>(null);
  const [lostReason, setLostReason] = useState("");
  const [moving, setMoving] = useState(false);
  const suppressCardClickRef = useRef(false);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const applyKanbanData = useCallback((data: KanbanResponse) => {
    const cols = [...data.columns].sort((a, b) => a.sequence - b.sequence);
    setColumns(cols);
    setMetrics({
      total_leads: data.total_leads,
      total_expected_revenue: data.total_expected_revenue,
    });
    const byStage: Record<string, KanbanLead[]> = {};
    cols.forEach((col) => {
      byStage[col.stage_id] = col.leads;
    });
    setColumnsByStage(byStage);
    if (data.pipeline_id) {
      setPipelineId(data.pipeline_id);
    }
  }, []);

  const loadKanban = useCallback(
    async (selectedPipelineId?: string | null) => {
      const params = selectedPipelineId ? { pipeline_id: selectedPipelineId } : undefined;
      const { data } = await api.get<KanbanResponse>("/crm/leads/kanban", { params });
      applyKanbanData(data);
      return data;
    },
    [applyKanbanData],
  );

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      setError("");
      try {
        const pipeRes = await api.get("/crm/pipeline", { params: { limit: 50 } });
        const pipeItems: Pipeline[] = pipeRes.data.items ?? pipeRes.data ?? [];
        if (!cancelled) setPipelines(pipeItems);

        const kanbanData = await loadKanban();
        if (!cancelled && !kanbanData.pipeline_id && pipeItems.length > 0) {
          const fallback = pipeItems.find((p) => p.is_default)?.id ?? pipeItems[0]?.id ?? null;
          if (fallback) {
            await loadKanban(fallback);
          }
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message: string }).message ?? "Failed to load kanban");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [loadKanban]);

  async function onPipelineChange(value: string | null) {
    if (!value) return;
    setPipelineId(value);
    setLoading(true);
    setError("");
    try {
      await loadKanban(value);
    } catch (e: unknown) {
      setError((e as { message: string }).message ?? "Failed to load kanban");
    } finally {
      setLoading(false);
    }
  }

  function findStageForLead(leadId: string): string | null {
    for (const [stageId, leads] of Object.entries(columnsByStage)) {
      if (leads.some((l) => l.id === leadId)) return stageId;
    }
    return null;
  }

  function getColumn(stageId: string): KanbanColumnData | undefined {
    return columns.find((c) => c.stage_id === stageId);
  }

  function openDealDrawer(lead: KanbanLead, stageName?: string) {
    setDrawerLead({
      id: lead.id,
      name: lead.name,
      expected_revenue: lead.expected_revenue,
      organization_name: lead.organization_name,
      person_name: lead.person_name,
      stage_name: stageName ?? null,
    });
    setDrawerOpen(true);
  }

  function applyOptimisticMove(
    leadId: string,
    lead: KanbanLead,
    sourceStage: string,
    targetStage: string,
  ) {
    setColumnsByStage((prev) => ({
      ...prev,
      [sourceStage]: prev[sourceStage].filter((l) => l.id !== leadId),
      [targetStage]: [...prev[targetStage], lead],
    }));
    setColumns((prev) =>
      prev.map((col) => {
        if (col.stage_id === sourceStage) {
          const nextLeads = col.leads.filter((l) => l.id !== leadId);
          const revenue = nextLeads.reduce((sum, l) => sum + l.expected_revenue, 0);
          return { ...col, leads: nextLeads, count: nextLeads.length, expected_revenue: revenue };
        }
        if (col.stage_id === targetStage) {
          const nextLeads = [...col.leads, lead];
          const revenue = nextLeads.reduce((sum, l) => sum + l.expected_revenue, 0);
          return { ...col, leads: nextLeads, count: nextLeads.length, expected_revenue: revenue };
        }
        return col;
      }),
    );
  }

  function resolveTargetStage(overId: string): string | null {
    if (columns.some((c) => c.stage_id === overId)) return overId;
    return findStageForLead(overId);
  }

  async function executeMove(
    leadId: string,
    lead: KanbanLead,
    sourceStage: string,
    targetStage: string,
    reason = "",
  ) {
    setMoving(true);
    try {
      await api.post(
        `/crm/lead/${leadId}/move`,
        reason ? { lost_reason: reason } : {},
        {
          params: { stage_id: targetStage },
          skipGlobalErrorToast: true,
        },
      );
      applyOptimisticMove(leadId, lead, sourceStage, targetStage);
      notifications.show({ title: "Updated", message: "Deal moved.", color: "green" });
    } catch (e: unknown) {      const missing = parseMissingFieldsError(e);
      if (missing) {
        const labels = missing.missing_fields.map(fieldLabel).join(", ");
        notifications.show({
          title: "Required fields missing",
          message: labels,
          color: "orange",
        });
        const fromCol = getColumn(sourceStage);
        setPendingRequiredFields({
          leadId,
          lead,
          sourceStage,
          targetStage,
          missingFields: missing.missing_fields,
          fromStageName: missing.from_stage_name ?? fromCol?.stage_name,
        });
      } else {
        notifications.show({ title: "Move failed", message: "Could not move deal.", color: "red" });
      }
      try {
        await loadKanban(pipelineId);
      } catch {
        /* ignore reload error */
      }
    } finally {
      setMoving(false);
    }
  }
  function onDragStart(event: DragStartEvent) {
    const id = String(event.active.id);
    setActiveId(id);
    const stageId = findStageForLead(id);
    if (stageId) {
      setActiveLead(columnsByStage[stageId].find((l) => l.id === id) ?? null);
    }
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    setActiveLead(null);
    suppressCardClickRef.current = true;
    window.setTimeout(() => {
      suppressCardClickRef.current = false;
    }, 200);

    if (!over) return;

    const leadId = String(active.id);
    const overId = String(over.id);

    const sourceStage = findStageForLead(leadId);
    const targetStage = resolveTargetStage(overId);
    if (!sourceStage || !targetStage || sourceStage === targetStage) return;

    const lead = columnsByStage[sourceStage].find((l) => l.id === leadId);
    if (!lead) return;

    const targetColumn = getColumn(targetStage);
    if (targetColumn?.is_lost) {
      setPendingLostMove({
        leadId,
        lead,
        sourceStage,
        targetStage,
        stageName: targetColumn.stage_name,
      });
      setLostReason("");
      return;
    }

    await executeMove(leadId, lead, sourceStage, targetStage);
  }

  async function confirmLostMove() {
    if (!pendingLostMove) return;
    setMoving(true);
    const { leadId, lead, sourceStage, targetStage } = pendingLostMove;
    await executeMove(leadId, lead, sourceStage, targetStage, lostReason.trim());
    setMoving(false);
    setPendingLostMove(null);
    setLostReason("");
  }

  if (loading && columns.length === 0) {
    return (
      <Stack gap="md">
        <Skeleton height={36} radius="sm" />
        <Group align="flex-start" gap="md">
          {Array.from({ length: 4 }).map((_, i) => (
            <Stack key={i} gap="xs" style={{ minWidth: 240 }}>
              <Skeleton height={48} radius="sm" />
              <Skeleton height={80} radius="sm" />
              <Skeleton height={80} radius="sm" />
            </Stack>
          ))}
        </Group>
      </Stack>
    );
  }

  if (error) {
    return <Alert icon={<IconAlertCircle size={16} />} color="red">{error}</Alert>;
  }

  if (columns.length === 0) {
    return (
      <Stack gap="md">
        <Group justify="space-between">
          {pipelines.length > 1 ? (
            <Select
              label="Pipeline"
              data={pipelines.map((p) => ({ value: p.id, label: p.name }))}
              value={pipelineId}
              onChange={onPipelineChange}
              style={{ minWidth: 220 }}
              size="sm"
              data-testid="crm-kanban-pipeline-select"
            />
          ) : (
            <div />
          )}
          <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
            New deal
          </Button>
        </Group>
        <EmptyState
          title="No pipeline stages"
          description="Configure stages for this pipeline to use the board."
          ctaLabel="New deal"
          ctaHref={createHref}
        />
      </Stack>
    );
  }

  return (
    <>
      <Stack gap="md">
        <Group justify="space-between" align="flex-end">
          <Group gap="md" align="flex-end">
            {pipelines.length > 0 && (
              <Select
                label="Pipeline"
                data={pipelines.map((p) => ({ value: p.id, label: p.name }))}
                value={pipelineId}
                onChange={onPipelineChange}
                style={{ minWidth: 220 }}
                size="sm"
                allowDeselect={false}
                data-testid="crm-kanban-pipeline-select"
              />
            )}
            <SimpleGrid cols={{ base: 2, sm: 2 }} spacing="md" data-testid="crm-kanban-metrics">
              <Paper p="xs" withBorder>
                <Text size="xs" c="dimmed">
                  Total deals
                </Text>
                <Text size="lg" fw={700}>
                  {metrics.total_leads}
                </Text>
              </Paper>
              <Paper p="xs" withBorder>
                <Text size="xs" c="dimmed">
                  Pipeline value
                </Text>
                <Text size="lg" fw={700}>
                  {formatMoney(metrics.total_expected_revenue)}
                </Text>
              </Paper>
            </SimpleGrid>
            <Chip
              checked={rottingOnly}
              onChange={setRottingOnly}
              color="orange"
              variant={rottingOnly ? "filled" : "outline"}
              icon={<IconFlame size={14} />}
              data-testid="crm-kanban-rotting-filter"
            >
              Rotting only
            </Chip>
          </Group>
          <Group gap="xs">
            <CrmCsvButtons resource="lead" />
            <Button component={Link} href={createHref} leftSection={<IconPlus size={16} />} size="sm">
              New deal
            </Button>
          </Group>
        </Group>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
        >
          <ScrollArea
            type="auto"
            scrollbarSize={8}
            styles={{ viewport: { paddingBottom: 8 } }}
            data-testid="crm-kanban-board"
          >
            <Group gap="md" align="flex-start" wrap="nowrap" pb="md">
              {columns.map((col) => (
                <KanbanColumn
                  key={col.stage_id}
                  column={col}
                  leads={columnsByStage[col.stage_id] ?? []}
                  activeId={activeId}
                  rottingOnly={rottingOnly}
                  suppressClickRef={suppressCardClickRef}
                  onOpenDeal={openDealDrawer}
                />
              ))}
            </Group>
          </ScrollArea>

          <DragOverlay>
            {activeLead && <DealCardOverlay lead={activeLead} />}
          </DragOverlay>
        </DndContext>
      </Stack>

      <CrmDealDrawer
        opened={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setDrawerLead(null);
        }}
        leadId={drawerLead?.id ?? null}
        preview={drawerLead}
      />

      <Modal
        opened={Boolean(pendingLostMove)}
        onClose={() => {
          if (!moving) setPendingLostMove(null);
        }}
        title="Mark deal as lost"
        size="sm"
        styles={{
          content: { background: "var(--mantine-color-body)" },
          header: { background: "var(--mantine-color-body)" },
        }}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Moving{" "}
            <Text span fw={600}>
              {pendingLostMove?.lead.name}
            </Text>{" "}
            to{" "}
            <Text span fw={600}>
              {pendingLostMove?.stageName}
            </Text>
            . Optionally capture why the deal was lost.
          </Text>
          <TextInput
            label="Lost reason"
            placeholder="Price, timing, competitor…"
            value={lostReason}
            onChange={(e) => setLostReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="subtle" color="gray" onClick={() => setPendingLostMove(null)} disabled={moving}>
              Cancel
            </Button>
            <Button color="red" loading={moving} onClick={confirmLostMove}>
              Move to lost
            </Button>
          </Group>
        </Stack>
      </Modal>

      <RequiredFieldsModal
        opened={Boolean(pendingRequiredFields)}
        dealName={pendingRequiredFields?.lead.name ?? ""}
        fromStageName={pendingRequiredFields?.fromStageName}
        missingFields={pendingRequiredFields?.missingFields ?? []}
        onClose={() => setPendingRequiredFields(null)}
        onEditDeal={() => {
          const pending = pendingRequiredFields;
          if (!pending) return;
          setPendingRequiredFields(null);
          openDealDrawer(pending.lead, pending.fromStageName);
        }}
      />
    </>
  );
}
