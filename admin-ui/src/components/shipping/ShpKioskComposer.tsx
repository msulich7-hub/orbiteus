"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  TouchSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Stepper,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconPlus } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import Many2OneField from "@/components/widgets/Many2OneField";
import ShpCarrierStatusBanner from "./ShpCarrierStatusBanner";
import ShpHandlingUnitTile, { ShpHandlingUnitTileOverlay } from "./ShpHandlingUnitTile";
import ShpWaybillColumn from "./ShpWaybillColumn";
import { useShpComposePreview } from "./useShpComposePreview";
import type {
  ShpAssignUnitBody,
  ShpComposePlanBody,
  ShpDispatchPlanBody,
  ShpHandlingUnit,
  ShpWaybillPlan,
} from "./shpTypes";
import { SHP_QUEUE_STATE_COLORS, SHP_QUEUE_STATE_LABELS } from "./shpTypes";

const POOL_ID = "hu-pool";
const MAX_WAYBILLS = 5;

function buildInitialPlan(
  units: ShpHandlingUnit[],
  suggested?: ShpWaybillPlan[] | null,
): { pool: string[]; waybills: ShpWaybillPlan[] } {
  if (suggested && suggested.length > 0) {
    const assigned = new Set(suggested.flatMap((w) => w.hu_ids ?? []));
    const pool = units.filter((u) => !assigned.has(u.id)).map((u) => u.id);
    return { pool, waybills: suggested.map((w, i) => ({ ...w, index: i })) };
  }
  if (units.length === 1) {
    return {
      pool: [],
      waybills: [
        {
          index: 0,
          carrier_code: "DPD",
          hu_ids: [units[0].id],
          is_pallet: units[0].type === "pallet",
        },
      ],
    };
  }
  return {
    pool: units.map((u) => u.id),
    waybills: [{ index: 0, carrier_code: "DPD", hu_ids: [] }],
  };
}

interface Props {
  ifsShipmentId: string;
  autoSubmit?: boolean;
  onClose?: () => void;
  onDispatched?: () => void;
}

export default function ShpKioskComposer({
  ifsShipmentId,
  autoSubmit = false,
  onClose,
  onDispatched,
}: Props) {
  const { preview, dispatchStatus, workspace, loading, error, refetch } = useShpComposePreview(
    ifsShipmentId,
    { pollDispatchStatus: true },
  );

  const [activeStep, setActiveStep] = useState(0);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [poolIds, setPoolIds] = useState<string[]>([]);
  const [waybills, setWaybills] = useState<ShpWaybillPlan[]>([]);
  const [printLabels, setPrintLabels] = useState(true);
  const [activeHu, setActiveHu] = useState<ShpHandlingUnit | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const autoRan = useRef(false);

  const units = preview?.handling_units ?? [];
  const unitById = useMemo(() => {
    const m = new Map<string, ShpHandlingUnit>();
    units.forEach((u) => m.set(u.id, u));
    return m;
  }, [units]);

  useEffect(() => {
    if (!preview) return;
    setOrderId(preview.order_id ?? null);
    const plan = buildInitialPlan(units, preview.suggested_plan?.waybills);
    setPoolIds(plan.pool);
    setWaybills(plan.waybills);
  }, [preview, units]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 6 } }),
  );

  const persistAssign = useCallback(
    async (body: ShpAssignUnitBody) => {
      const dispatchId = preview?.dispatch_id ?? workspace?.dispatch_id;
      if (!dispatchId) return;
      try {
        await api.put(
          `/shipping/dispatch/${dispatchId}/assign-unit`,
          body,
          { skipGlobalErrorToast: true },
        );
      } catch {
        /* SHP-005 optional */
      }
    },
    [preview?.dispatch_id, workspace?.dispatch_id],
  );

  const saveDraft = useCallback(async () => {
    if (!orderId) return;
    const body: ShpComposePlanBody = {
      order_id: orderId,
      waybills,
    };
    try {
      await api.put(
        `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/compose-plan`,
        body,
        { skipGlobalErrorToast: true },
      );
    } catch {
      /* optional draft endpoint */
    }
  }, [ifsShipmentId, orderId, waybills]);

  const onDragStart = (event: DragStartEvent) => {
    const id = String(event.active.id);
    setActiveHu(unitById.get(id) ?? null);
  };

  const onDragEnd = (event: DragEndEvent) => {
    setActiveHu(null);
    const { active, over } = event;
    if (!over) return;

    const huId = String(active.id);
    const overId = String(over.id);

    let targetWaybill: number | null = null;
    if (overId.startsWith("waybill-")) {
      targetWaybill = Number(overId.replace("waybill-", ""));
    } else if (overId === POOL_ID) {
      targetWaybill = -1;
    } else {
      const wb = waybills.findIndex((w) => (w.hu_ids ?? []).includes(overId));
      if (wb >= 0) targetWaybill = wb;
    }

    if (targetWaybill === null) return;

    setWaybills((prev) =>
      prev.map((w) => ({
        ...w,
        hu_ids: (w.hu_ids ?? []).filter((id) => id !== huId),
      })),
    );
    setPoolIds((prev) => prev.filter((id) => id !== huId));

    if (targetWaybill === -1) {
      setPoolIds((prev) => (prev.includes(huId) ? prev : [...prev, huId]));
    } else {
      setWaybills((prev) =>
        prev.map((w, i) =>
          i === targetWaybill
            ? { ...w, hu_ids: [...(w.hu_ids ?? []).filter((id) => id !== huId), huId] }
            : w,
        ),
      );
      void persistAssign({ hu_id: huId, waybill_index: targetWaybill });
    }

    void saveDraft();
  };

  const addWaybill = () => {
    if (waybills.length >= MAX_WAYBILLS) return;
    setWaybills((prev) => [
      ...prev,
      { index: prev.length, carrier_code: preview?.suggested_carrier ?? "DPD", hu_ids: [] },
    ]);
  };

  const removeWaybill = (index: number) => {
    const removed = waybills[index];
    const freed = removed?.hu_ids ?? [];
    setWaybills((prev) => prev.filter((_, i) => i !== index).map((w, i) => ({ ...w, index: i })));
    setPoolIds((prev) => [...prev, ...freed.filter((id) => !prev.includes(id))]);
  };

  const submitDispatch = useCallback(async () => {
    if (!orderId) {
      notifications.show({
        title: "Zamówienie wymagane",
        message: "Przypisz zamówienie ERP przed wysyłką.",
        color: "orange",
      });
      setActiveStep(0);
      return;
    }

    const empty = waybills.some((w) => !(w.hu_ids?.length ?? 0));
    if (empty) {
      notifications.show({
        title: "Puste listy",
        message: "Przeciągnij jednostki do list przewozowych.",
        color: "orange",
      });
      setActiveStep(1);
      return;
    }

    setSubmitting(true);
    try {
      const body: ShpDispatchPlanBody = {
        order_id: orderId,
        waybills,
        print_labels: printLabels,
      };
      try {
        await api.post(
          `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch-plan`,
          body,
          { skipGlobalErrorToast: true },
        );
      } catch {
        await api.post(
          `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch`,
          { order_id: orderId, force_carrier: waybills[0]?.carrier_code },
          { skipGlobalErrorToast: true },
        );
      }
      notifications.show({
        title: "W kolejce",
        message: "Wysyłka przekazana do przetwarzania.",
        color: "green",
      });
      setActiveStep(3);
      onDispatched?.();
      void refetch();
    } catch (e: unknown) {
      notifications.show({
        title: "Błąd wysyłki",
        message: String(
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            "Nie udało się wysłać.",
        ),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  }, [ifsShipmentId, onDispatched, orderId, printLabels, refetch, waybills]);

  useEffect(() => {
    if (!autoSubmit || autoRan.current || loading || !preview) return;
    if (preview.suggested_mode !== "auto" || (preview.blocking_errors?.length ?? 0) > 0) return;
    if (!preview.order_id) return;
    autoRan.current = true;
    void submitDispatch();
  }, [autoSubmit, loading, preview, submitDispatch]);

  if (loading && !preview) {
    return (
      <CenterLoader />
    );
  }

  if (error && !preview) {
    return (
      <Stack gap="md">
        <Alert color="red" title="Podgląd niedostępny">
          {error}
        </Alert>
        <Text size="sm" c="dimmed">
          Użyj formularza rekordu lub poczekaj na endpoint compose-preview (SHP-004).
        </Text>
        {onClose && (
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={onClose}>
            Wróć do skrzynki
          </Button>
        )}
      </Stack>
    );
  }

  const queueState = preview?.state ?? "queued";
  const stateColor = SHP_QUEUE_STATE_COLORS[queueState] ?? "gray";
  const stateLabel = SHP_QUEUE_STATE_LABELS[queueState] ?? queueState;
  const blocking = preview?.blocking_errors ?? [];

  const poolUnits = poolIds.map((id) => unitById.get(id)).filter(Boolean) as ShpHandlingUnit[];

  return (
    <Stack gap="md" data-testid="shp-kiosk-composer">
      <Group justify="space-between">
        <Group gap="sm">
          {onClose && (
            <Button
              variant="subtle"
              color="gray"
              leftSection={<IconArrowLeft size={16} />}
              onClick={onClose}
            >
              Skrzynka IFS
            </Button>
          )}
          <Stack gap={2}>
            <Title order={4}>Kiosk wysyłki · IFS {ifsShipmentId}</Title>
            <Group gap="xs">
              {preview?.ifs_sid && <Badge variant="light">{preview.ifs_sid}</Badge>}
              {preview?.objstate && (
                <Text size="xs" c="dimmed">
                  {preview.objstate}
                </Text>
              )}
              <Badge color={stateColor}>{stateLabel}</Badge>
            </Group>
          </Stack>
        </Group>
        <Button variant="light" size="sm" onClick={() => void refetch()}>
          Odśwież
        </Button>
      </Group>

      <ShpCarrierStatusBanner recommendedCarrier={preview?.suggested_carrier} />

      {blocking.length > 0 && (
        <Alert color="red" title="Nie można wysłać automatycznie">
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {blocking.map((msg) => (
              <li key={msg}>
                <Text size="sm">{msg}</Text>
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {(preview?.warnings ?? []).length > 0 && (
        <Alert color="yellow" title="Uwagi">
          {(preview?.warnings ?? []).join(" · ")}
        </Alert>
      )}

      <Stepper active={activeStep} onStepClick={setActiveStep} aria-current="step">
        <Stepper.Step label="Przegląd" description="Dane IFS" />
        <Stepper.Step label="Układ" description="Listy przewozowe" />
        <Stepper.Step label="Wysyłka" description="Podsumowanie" />
        <Stepper.Step label="Druk" description="Status" />
      </Stepper>

      {activeStep === 0 && (
        <Paper p="md" withBorder>
          <Stack gap="md">
            <Text size="sm">
              <strong>Odbiorca:</strong>{" "}
              {preview?.recipient?.company_name ??
                [preview?.recipient?.first_name, preview?.recipient?.last_name]
                  .filter(Boolean)
                  .join(" ") ??
                "—"}
              {preview?.recipient?.city ? ` · ${preview.recipient.city}` : ""}
            </Text>
            <Text size="sm" c="dimmed">
              Waga łączna: {(preview?.total_weight_kg ?? 0).toFixed(1)} kg · Jednostek:{" "}
              {units.length}
            </Text>
            <Group gap="xs" wrap="wrap">
              {units.map((u) => (
                <ShpHandlingUnitTile key={u.id} unit={u} />
              ))}
            </Group>
            <Many2OneField
              label="Zamówienie ERP"
              relation="orders/order"
              value={orderId}
              onChange={(v) => setOrderId(v)}
              required
            />
            <Button onClick={() => setActiveStep(1)}>Dalej: Układ listów</Button>
          </Stack>
        </Paper>
      )}

      {activeStep === 1 && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
        >
          <ScrollArea type="auto">
            <Group align="flex-start" wrap="nowrap" pb="md">
              <ShpHuPoolColumn units={poolUnits} />
              {waybills.map((wb, i) => {
                const colUnits = (wb.hu_ids ?? [])
                  .map((id) => unitById.get(id))
                  .filter(Boolean) as ShpHandlingUnit[];
                return (
                  <ShpWaybillColumn
                    key={`wb-${i}`}
                    index={i}
                    waybill={wb}
                    units={colUnits}
                    onCarrierChange={(c) =>
                      setWaybills((prev) =>
                        prev.map((w, idx) => (idx === i ? { ...w, carrier_code: c } : w)),
                      )
                    }
                    onRemove={() => removeWaybill(i)}
                    canRemove={waybills.length > 1 && colUnits.length === 0}
                  />
                );
              })}
              {waybills.length < MAX_WAYBILLS && (
                <Button
                  variant="light"
                  leftSection={<IconPlus size={16} />}
                  onClick={addWaybill}
                  mt={40}
                >
                  Dodaj list
                </Button>
              )}
            </Group>
          </ScrollArea>
          <DragOverlay>
            {activeHu && <ShpHandlingUnitTileOverlay unit={activeHu} />}
          </DragOverlay>
          <Group justify="space-between" mt="md">
            <Button variant="default" onClick={() => setActiveStep(0)}>
              Wstecz
            </Button>
            <Button onClick={() => setActiveStep(2)}>Dalej: Wyślij</Button>
          </Group>
        </DndContext>
      )}

      {activeStep === 2 && (
        <Paper p="md" withBorder>
          <Stack gap="md">
            <Text fw={600}>Podsumowanie · {waybills.length} list(y)</Text>
            {waybills.map((wb, i) => (
              <Text key={i} size="sm">
                L{i + 1}: {wb.carrier_code} — {(wb.hu_ids ?? []).length} HU
              </Text>
            ))}
            <Checkbox
              label="Drukuj etykiety po utworzeniu"
              checked={printLabels}
              onChange={(e) => setPrintLabels(e.currentTarget.checked)}
            />
            <Button
              size="lg"
              h={56}
              loading={submitting}
              onClick={() => void submitDispatch()}
            >
              Wyślij do kuriera (202 · kolejka)
            </Button>
            <Group>
              <Button variant="default" onClick={() => setActiveStep(1)}>
                Wstecz
              </Button>
            </Group>
          </Stack>
        </Paper>
      )}

      {activeStep === 3 && (
        <Paper p="md" withBorder>
          <Stack gap="sm" aria-live="polite">
            <Text fw={600}>Postęp wysyłki</Text>
            <Text size="sm" c="dimmed">
              Stan kolejki: {dispatchStatus?.queue_state ?? queueState}
            </Text>
            {(dispatchStatus?.waybills ?? []).length > 0 ? (
              dispatchStatus?.waybills?.map((wb) => (
                <Group key={wb.index} justify="space-between">
                  <Text size="sm">
                    List {(wb.index ?? 0) + 1}: {wb.state}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {wb.tracking_number ?? wb.error_message ?? "—"}
                  </Text>
                </Group>
              ))
            ) : (
              <Text size="sm" c="dimmed">
                Oczekiwanie na status z dispatch-status lub SSE…
              </Text>
            )}
            {onClose && (
              <Button variant="light" onClick={onClose}>
                Zamknij kiosk
              </Button>
            )}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}


function ShpHuPoolColumn({ units }: { units: ShpHandlingUnit[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: POOL_ID });
  return (
    <Stack gap="xs" style={{ minWidth: 180 }}>
      <Text size="sm" fw={600}>
        Pula jednostek
      </Text>
      <Paper
        ref={setNodeRef}
        p="xs"
        data-testid="shp-hu-pool"
        style={{
          minHeight: 120,
          background: isOver
            ? "var(--mantine-color-blue-light)"
            : "var(--mantine-color-default-hover)",
          outline: isOver ? "2px dashed var(--mantine-color-blue-5)" : undefined,
        }}
      >
        <Stack gap="xs">
          {units.map((u) => (
            <ShpHandlingUnitTile key={u.id} unit={u} />
          ))}
          {units.length === 0 && (
            <Text size="xs" c="dimmed" ta="center" py="md">
              Wszystkie przypisane
            </Text>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function CenterLoader() {
  return (
    <Stack align="center" py="xl">
      <Loader />
      <Text size="sm" c="dimmed">
        Wczytywanie podglądu…
      </Text>
    </Stack>
  );
}
