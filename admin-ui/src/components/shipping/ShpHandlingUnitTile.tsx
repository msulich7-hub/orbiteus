"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Badge, Group, Paper, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconGripVertical, IconPackage } from "@tabler/icons-react";
import type { ShpHandlingUnit } from "./shpTypes";

export default function ShpHandlingUnitTile({
  unit,
  isDragging,
}: {
  unit: ShpHandlingUnit;
  isDragging?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging: dndDragging } =
    useDraggable({ id: unit.id });

  const style = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging || dndDragging ? 0.45 : 1,
    cursor: "grab",
    touchAction: "none" as const,
    minWidth: 72,
    minHeight: 72,
  };

  const isPallet = unit.type === "pallet" || (unit.pack_type ?? "").startsWith("PAL");

  return (
    <Paper
      ref={setNodeRef}
      style={style}
      p="xs"
      radius="sm"
      withBorder
      data-testid={`shp-hu-tile-${unit.id}`}
      aria-grabbed={dndDragging}
      aria-roledescription="przeciągnij jednostkę"
      {...attributes}
      {...listeners}
    >
      <Group gap={6} wrap="nowrap" align="flex-start">
        <ThemeIcon variant="subtle" color="gray" size="sm" style={{ pointerEvents: "none" }}>
          <IconGripVertical size={14} />
        </ThemeIcon>
        <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
          <Group gap={4}>
            <IconPackage size={14} />
            <Text size="sm" fw={600} lineClamp={1}>
              {unit.pack_type ?? unit.type ?? "HU"}
            </Text>
          </Group>
          <Text size="xs" c="dimmed">
            {(unit.weight_kg ?? 0).toFixed(1)} kg
            {(unit.qty ?? 1) > 1 ? ` · ×${unit.qty}` : ""}
          </Text>
          {isPallet && (
            <Badge size="xs" variant="light" color="orange">
              Paleta
            </Badge>
          )}
        </Stack>
      </Group>
    </Paper>
  );
}

/** Drag overlay clone — no draggable hooks. */
export function ShpHandlingUnitTileOverlay({ unit }: { unit: ShpHandlingUnit }) {
  return (
    <Paper
      p="xs"
      radius="sm"
      withBorder
      style={{ cursor: "grabbing", boxShadow: "var(--mantine-shadow-md)", minWidth: 120 }}
    >
      <Text size="sm" fw={600}>
        {unit.pack_type ?? unit.type ?? "HU"}
      </Text>
      <Text size="xs" c="dimmed">
        {(unit.weight_kg ?? 0).toFixed(1)} kg
      </Text>
    </Paper>
  );
}
