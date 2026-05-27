"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import {
  ActionIcon,
  Badge,
  Group,
  Paper,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconTrash } from "@tabler/icons-react";
import ShpHandlingUnitTile from "./ShpHandlingUnitTile";
import type { ShpHandlingUnit, ShpWaybillPlan } from "./shpTypes";

const CARRIER_OPTIONS = ["DPD", "DSV", "GEODIS", "INPOST", "MOCK"].map((c) => ({
  value: c,
  label: c,
}));

export default function ShpWaybillColumn({
  index,
  waybill,
  units,
  carriers,
  onCarrierChange,
  onRemove,
  canRemove,
}: {
  index: number;
  waybill: ShpWaybillPlan;
  units: ShpHandlingUnit[];
  carriers?: string[];
  onCarrierChange?: (carrier: string) => void;
  onRemove?: () => void;
  canRemove?: boolean;
}) {
  const dropId = `waybill-${index}`;
  const { setNodeRef, isOver } = useDroppable({ id: dropId });
  const carrier = waybill.carrier_code ?? "DPD";
  const carrierData =
    carriers && carriers.length > 0
      ? carriers.map((c) => ({ value: c, label: c }))
      : CARRIER_OPTIONS;

  return (
    <Stack
      gap="xs"
      style={{ minWidth: 200, flex: "1 1 200px", maxWidth: 280 }}
      data-testid={`shp-waybill-column-${index}`}
      aria-label={`List przewozowy ${index + 1}, przewoźnik ${carrier}`}
    >
      <Paper p="xs" withBorder>
        <Group justify="space-between" wrap="nowrap">
          <Stack gap={2}>
            <Title order={6}>List {index + 1}</Title>
            <Select
              size="xs"
              data={carrierData}
              value={carrier}
              onChange={(v) => v && onCarrierChange?.(v)}
              comboboxProps={{ withinPortal: true }}
              aria-label="Przewoźnik"
            />
          </Stack>
          <Group gap={4}>
            <Badge size="sm" variant="light">
              {units.length} HU
            </Badge>
            {canRemove && onRemove && (
              <ActionIcon
                variant="subtle"
                color="red"
                size="sm"
                onClick={onRemove}
                aria-label="Usuń list"
              >
                <IconTrash size={14} />
              </ActionIcon>
            )}
          </Group>
        </Group>
      </Paper>
      <Paper
        ref={setNodeRef}
        p="xs"
        data-testid={`shp-waybill-drop-${index}`}
        style={{
          minHeight: 120,
          background: isOver
            ? "var(--mantine-color-blue-light)"
            : "var(--mantine-color-default-hover)",
          outline: isOver ? "2px dashed var(--mantine-color-blue-5)" : undefined,
          transition: "background 120ms ease, outline 120ms ease",
        }}
      >
        <SortableContext items={units.map((u) => u.id)} strategy={verticalListSortingStrategy}>
          <Stack gap="xs">
            {units.map((u) => (
              <ShpHandlingUnitTile key={u.id} unit={u} />
            ))}
            {units.length === 0 && (
              <Text size="xs" c="dimmed" ta="center" py="md">
                Upuść jednostkę tutaj
              </Text>
            )}
          </Stack>
        </SortableContext>
      </Paper>
    </Stack>
  );
}
