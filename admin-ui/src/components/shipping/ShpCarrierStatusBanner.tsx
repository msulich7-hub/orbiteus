"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Group, Loader, Text } from "@mantine/core";
import { IconTruck } from "@tabler/icons-react";
import { api } from "@/lib/api";
import type { ShpCarrierStatusResponse } from "./shpTypes";

/**
 * Read-only banner from `GET /api/shipping/carriers/status`.
 * Gates AUTO dispatch when the recommended carrier is not configured.
 */
export default function ShpCarrierStatusBanner({
  recommendedCarrier,
}: {
  recommendedCarrier?: string | null;
}) {
  const [data, setData] = useState<ShpCarrierStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: body } = await api.get<ShpCarrierStatusResponse>("/shipping/carriers/status", {
        skipGlobalErrorToast: true,
      });
      setData(body ?? null);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <Alert variant="light" color="gray" icon={<Loader size={16} />}>
        <Text size="sm">Ładowanie statusu kurierów…</Text>
      </Alert>
    );
  }

  const configured = data?.configured_carriers ?? [];
  const rec = (recommendedCarrier ?? "").toUpperCase();
  const recOk = !rec || configured.map((c) => c.toUpperCase()).includes(rec);

  if (configured.length === 0) {
    return (
      <Alert variant="light" color="yellow" icon={<IconTruck size={18} />} title="Kurierzy">
        Brak skonfigurowanych przewoźników w środowisku. Sprawdź zmienne z pliku
        `.env.shipping.example` na backendzie.
      </Alert>
    );
  }

  if (!recOk) {
    return (
      <Alert variant="light" color="orange" icon={<IconTruck size={18} />} title="Kurierzy">
        Rekomendowany przewoźnik <strong>{recommendedCarrier}</strong> nie jest skonfigurowany.
        Skonfigurowane: {configured.join(", ")}.
      </Alert>
    );
  }

  return (
    <Alert variant="light" color="blue" icon={<IconTruck size={18} />}>
      <Group gap="xs" wrap="wrap">
        <Text size="sm" fw={500}>
          Kurierzy:
        </Text>
        <Text size="sm">{configured.join(" · ")}</Text>
      </Group>
    </Alert>
  );
}
