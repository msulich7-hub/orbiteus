"use client";

import { useCallback, useState } from "react";
import { Button, Group, Paper, Stack, Text } from "@mantine/core";
import { IconBolt, IconLayoutKanban } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import type {
  ShpComposePreview,
  ShpDispatchPlanBody,
  ShpDispatchPlanResponse,
} from "./shpTypes";

interface Props {
  ifsShipmentId: string;
  preview: ShpComposePreview;
  onDispatched?: () => void;
  onOpenKiosk?: () => void;
}

/**
 * One-tap AUTO dispatch when `suggested_mode === "auto"`.
 * Prefers `POST .../dispatch-plan`; falls back to legacy `POST .../dispatch`.
 */
export default function ShpAutoConfirmStrip({
  ifsShipmentId,
  preview,
  onDispatched,
  onOpenKiosk,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const carrier =
    preview.suggested_carrier ??
    preview.suggested_plan?.waybills?.[0]?.carrier_code ??
    "MOCK";
  const waybillCount = preview.suggested_plan?.waybills?.length ?? 1;

  const dispatch = useCallback(async () => {
    if (!preview.order_id) {
      notifications.show({
        title: "Brak zamówienia",
        message: "Wybierz zamówienie ERP przed wysyłką.",
        color: "orange",
      });
      onOpenKiosk?.();
      return;
    }

    setSubmitting(true);
    try {
      const planBody: ShpDispatchPlanBody = {
        order_id: preview.order_id,
        waybills:
          preview.suggested_plan?.waybills?.map((w, i) => ({
            ...w,
            index: w.index ?? i,
            carrier_code: w.carrier_code ?? carrier,
          })) ?? [
            {
              index: 0,
              carrier_code: carrier,
              hu_ids: preview.handling_units?.map((h) => h.id) ?? [],
              is_pallet: preview.handling_units?.some((h) => h.type === "pallet"),
            },
          ],
        print_labels: true,
      };

      try {
        await api.post<ShpDispatchPlanResponse>(
          `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch-plan`,
          planBody,
          { skipGlobalErrorToast: true },
        );
      } catch {
        await api.post(
          `/shipping/ifs/queue/${encodeURIComponent(ifsShipmentId)}/dispatch`,
          {
            order_id: preview.order_id,
            force_carrier: carrier,
          },
          { skipGlobalErrorToast: true },
        );
      }

      notifications.show({
        title: "W kolejce",
        message: "Wysyłka przekazana do przetwarzania (202).",
        color: "green",
      });
      onDispatched?.();
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Nie udało się wysłać.";
      notifications.show({
        title: "Wysyłka nieudana",
        message: String(detail),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  }, [carrier, ifsShipmentId, onDispatched, onOpenKiosk, preview]);

  return (
    <Paper p="md" withBorder data-testid="shp-auto-confirm-strip">
      <Group justify="space-between" align="center" wrap="wrap">
        <Stack gap={4}>
          <Text size="sm" fw={600}>
            Tryb automatyczny · {waybillCount} list{waybillCount > 1 ? "y" : "a"} · {carrier}
          </Text>
          <Text size="xs" c="dimmed">
            IFS {ifsShipmentId}
            {preview.order_no ? ` · ${preview.order_no}` : ""}
          </Text>
        </Stack>
        <Group gap="sm">
          {onOpenKiosk && (
            <Button
              variant="subtle"
              color="gray"
              leftSection={<IconLayoutKanban size={16} />}
              onClick={onOpenKiosk}
            >
              Otwórz kiosk
            </Button>
          )}
          <Button
            size="lg"
            h={56}
            leftSection={<IconBolt size={20} />}
            loading={submitting}
            onClick={() => void dispatch()}
            data-testid="shp-auto-dispatch-cta"
          >
            Wyślij {waybillCount} list{waybillCount > 1 ? "y" : "ę"} przewozow{waybillCount > 1 ? "e" : "ą"} · {carrier}
          </Button>
        </Group>
      </Group>
    </Paper>
  );
}
