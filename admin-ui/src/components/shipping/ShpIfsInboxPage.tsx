"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Center,
  Flex,
  Group,
  Loader,
  NavLink,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconInbox,
  IconLayoutKanban,
  IconList,
  IconRefresh,
} from "@tabler/icons-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useRealtimeList } from "@/lib/realtime";
import EmptyState from "@/components/EmptyState";
import ShpAutoConfirmStrip from "./ShpAutoConfirmStrip";
import ShpCarrierStatusBanner from "./ShpCarrierStatusBanner";
import ShpKioskComposer from "./ShpKioskComposer";
import { useShpComposePreview } from "./useShpComposePreview";
import type { ShpIfsQueueRow, ShpInboxFilter } from "./shpTypes";
import { SHP_QUEUE_STATE_COLORS, SHP_QUEUE_STATE_LABELS } from "./shpTypes";

const FILTERS: { id: ShpInboxFilter; label: string; icon: typeof IconList }[] = [
  { id: "queued", label: "W kolejce", icon: IconInbox },
  { id: "processing", label: "W trakcie", icon: IconList },
  { id: "failed", label: "Błędy", icon: IconAlertTriangle },
  { id: "all", label: "Wszystkie", icon: IconList },
];

function resolveFilter(searchParams: URLSearchParams): ShpInboxFilter {
  if (searchParams.get("filter") === "errors") return "failed";
  const state = searchParams.get("state");
  if (state === "processing" || state === "failed" || state === "all") return state;
  return "queued";
}

/**
 * IFS inbox (SHP-S01) + kiosk overlay via `?kiosk=` / `?auto=1`.
 * API: `GET /api/shipping/ifs/queue` — compose endpoints may 404 until SHP-004.
 */
export default function ShpIfsInboxPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const kioskId = searchParams.get("kiosk");
  const autoParam = searchParams.get("auto") === "1";
  const filter = resolveFilter(searchParams);

  const [rows, setRows] = useState<ShpIfsQueueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedIfsId = kioskId ?? selectedId;

  const { preview, loading: previewLoading, refetch: refetchPreview } = useShpComposePreview(
    selectedIfsId && !kioskId ? selectedIfsId : null,
  );

  const setParams = useCallback(
    (mutate: (p: URLSearchParams) => void) => {
      const p = new URLSearchParams(searchParams.toString());
      mutate(p);
      const qs = p.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const loadRows = useCallback(async () => {
    setLoading(true);
    try {
      const state = filter === "all" ? undefined : filter;
      const { data } = await api.get<ShpIfsQueueRow[]>("/shipping/ifs/queue", {
        params: { state, limit: 100 },
        skipGlobalErrorToast: true,
      });
      setRows(Array.isArray(data) ? data : []);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  useRealtimeList("shipping/ifs_queue", () => {
    void loadRows();
    if (selectedIfsId) void refetchPreview();
  });

  const openKiosk = (ifsShipmentId: string, auto?: boolean) => {
    setParams((p) => {
      p.set("kiosk", ifsShipmentId);
      if (auto) p.set("auto", "1");
      else p.delete("auto");
    });
  };

  const closeKiosk = () => {
    setParams((p) => {
      p.delete("kiosk");
      p.delete("auto");
    });
  };

  const setFilter = (f: ShpInboxFilter) => {
    setParams((p) => {
      p.delete("kiosk");
      p.delete("auto");
      if (f === "failed") {
        p.set("filter", "errors");
        p.set("state", "failed");
      } else if (f === "all") {
        p.delete("filter");
        p.set("state", "all");
      } else {
        p.delete("filter");
        p.set("state", f);
      }
    });
  };

  const showAutoStrip = useMemo(() => {
    if (kioskId || !selectedIfsId || previewLoading) return false;
    return preview?.suggested_mode === "auto" && (preview.blocking_errors?.length ?? 0) === 0;
  }, [kioskId, preview, previewLoading, selectedIfsId]);

  return (
    <Stack gap="md" data-testid="shp-ifs-inbox-page">
      <Paper>
        <Group justify="space-between" align="center">
          <Stack gap={2}>
            <Title order={3}>Skrzynka IFS</Title>
            <Text size="sm" c="dimmed">
              Kolejka webhooków IFS — wysyłka AUTO lub kiosk wielolistowy.
            </Text>
          </Stack>
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={() => void loadRows()}
          >
            Odśwież
          </Button>
        </Group>
      </Paper>

      <ShpCarrierStatusBanner recommendedCarrier={preview?.suggested_carrier} />

      <Flex gap="md" align="flex-start" wrap="nowrap">
        <Paper p="sm" withBorder style={{ minWidth: 200, maxWidth: 240 }}>
          <Text size="sm" fw={600} mb="xs">
            Filtry
          </Text>
          {FILTERS.map((f) => (
            <NavLink
              key={f.id}
              label={f.label}
              leftSection={<f.icon size={16} />}
              active={filter === f.id}
              onClick={() => setFilter(f.id)}
              variant="filled"
              mb={4}
            />
          ))}
        </Paper>

        <Stack gap="md" style={{ flex: 1, minWidth: 0 }}>
          {kioskId ? (
            <ShpKioskComposer
              ifsShipmentId={kioskId}
              autoSubmit={autoParam}
              onClose={closeKiosk}
              onDispatched={() => {
                void loadRows();
                closeKiosk();
              }}
            />
          ) : (
            <>
              {loading ? (
                <Center py="xl">
                  <Loader size="sm" />
                </Center>
              ) : rows.length === 0 ? (
                <EmptyState
                  title="Brak przesyłek w kolejce"
                  description="Nowe wpisy pojawią się po webhooku IFS."
                  icon={<IconInbox size={28} />}
                />
              ) : (
                <ScrollArea>
                  <Table striped highlightOnHover withTableBorder>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>IFS Shipment</Table.Th>
                        <Table.Th>Zamówienie</Table.Th>
                        <Table.Th>Waga</Table.Th>
                        <Table.Th>HU</Table.Th>
                        <Table.Th>Agent</Table.Th>
                        <Table.Th>Stan</Table.Th>
                        <Table.Th />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {rows.map((row) => {
                        const selected = selectedId === row.ifs_shipment_id;
                        const color = SHP_QUEUE_STATE_COLORS[row.state] ?? "gray";
                        const label = SHP_QUEUE_STATE_LABELS[row.state] ?? row.state;
                        return (
                          <Table.Tr
                            key={row.id}
                            style={{
                              cursor: "pointer",
                              background: selected
                                ? "var(--mantine-color-blue-light)"
                                : undefined,
                            }}
                            onClick={() => setSelectedId(row.ifs_shipment_id)}
                            data-testid={`shp-ifs-row-${row.ifs_shipment_id}`}
                          >
                            <Table.Td>
                              <Text fw={600} size="sm">
                                {row.ifs_shipment_id}
                              </Text>
                              {row.ifs_sid && (
                                <Text size="xs" c="dimmed">
                                  {row.ifs_sid}
                                </Text>
                              )}
                            </Table.Td>
                            <Table.Td>{row.order_no ?? "—"}</Table.Td>
                            <Table.Td>
                              {row.total_weight_kg != null
                                ? `${row.total_weight_kg.toFixed(1)} kg`
                                : "—"}
                            </Table.Td>
                            <Table.Td>{row.line_count ?? 0}</Table.Td>
                            <Table.Td>{row.forward_agent_id ?? "—"}</Table.Td>
                            <Table.Td>
                              <Badge color={color} variant="light">
                                {label}
                              </Badge>
                            </Table.Td>
                            <Table.Td>
                              <Button
                                size="xs"
                                variant="light"
                                leftSection={<IconLayoutKanban size={14} />}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openKiosk(row.ifs_shipment_id);
                                }}
                              >
                                Kiosk
                              </Button>
                            </Table.Td>
                          </Table.Tr>
                        );
                      })}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              )}

              {showAutoStrip && preview && selectedIfsId && (
                <ShpAutoConfirmStrip
                  ifsShipmentId={selectedIfsId}
                  preview={preview}
                  onOpenKiosk={() => openKiosk(selectedIfsId)}
                  onDispatched={() => {
                    setSelectedId(null);
                    void loadRows();
                  }}
                />
              )}

              {selectedIfsId && !showAutoStrip && preview && !previewLoading && (
                <Group>
                  <Button
                    leftSection={<IconLayoutKanban size={16} />}
                    onClick={() => openKiosk(selectedIfsId)}
                  >
                    Otwórz kiosk
                  </Button>
                </Group>
              )}
            </>
          )}
        </Stack>
      </Flex>
    </Stack>
  );
}
