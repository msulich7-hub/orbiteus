"use client";



import { useCallback, useEffect, useState } from "react";

import Link from "next/link";

import {

  Badge,

  Button,

  Center,

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

import { IconList, IconRefresh } from "@tabler/icons-react";

import { api } from "@/lib/api";

import { MonetaryCell } from "@/components/widgets/MonetaryField";



interface QueueRow {

  id: string;

  name: string;

  sequence?: number;

  is_shared?: boolean;

}



interface QueueLead {

  id: string;

  name: string;

  expected_revenue: number;

  probability: number;

  expected_close_date: string | null;

  is_rotting: boolean;

  days_in_stage: number | null;

}



interface QueueRunResponse {

  queue_id: string;

  queue_name: string;

  count: number;

  leads: QueueLead[];

}



interface Props {

  /** Pre-select queue from ?queue= URL param */

  initialQueueId?: string | null;

  onQueueChange?: (queueId: string | null) => void;

}



export default function CrmQueueSidebar({ initialQueueId, onQueueChange }: Props) {

  const [queues, setQueues] = useState<QueueRow[]>([]);

  const [loadingQueues, setLoadingQueues] = useState(true);

  const [activeId, setActiveId] = useState<string | null>(initialQueueId ?? null);

  const [runLoading, setRunLoading] = useState(false);

  const [result, setResult] = useState<QueueRunResponse | null>(null);



  const loadQueues = useCallback(async () => {

    setLoadingQueues(true);

    try {

      const { data } = await api.get<{ items: QueueRow[] }>("/crm/queue", {

        params: { limit: 100, order_by: "sequence", order_dir: "asc" },

      });

      const items = data.items ?? [];

      setQueues(items);

      if (!activeId && items.length > 0 && initialQueueId) {

        setActiveId(initialQueueId);

      }

    } catch {

      setQueues([]);

    } finally {

      setLoadingQueues(false);

    }

  }, [activeId, initialQueueId]);



  const runQueue = useCallback(async (queueId: string) => {

    setRunLoading(true);

    setActiveId(queueId);

    onQueueChange?.(queueId);

    try {

      const { data } = await api.get<QueueRunResponse>(`/crm/queue/${queueId}/run`);

      setResult(data);

    } catch {

      setResult(null);

    } finally {

      setRunLoading(false);

    }

  }, [onQueueChange]);



  useEffect(() => {

    loadQueues();

  }, [loadQueues]);



  useEffect(() => {

    if (initialQueueId) {

      runQueue(initialQueueId);

    }

  }, [initialQueueId, runQueue]);



  return (

    <Stack gap="md" style={{ minWidth: 220, maxWidth: 280 }}>

      <Paper p="sm" withBorder>

        <Group justify="space-between" mb="xs">

          <Title order={5}>Work queues</Title>

          <Button

            variant="subtle"

            size="xs"

            leftSection={<IconRefresh size={14} />}

            onClick={loadQueues}

          >

            Refresh

          </Button>

        </Group>

        {loadingQueues ? (

          <Center py="md">

            <Loader size="sm" />

          </Center>

        ) : queues.length === 0 ? (

          <Text size="sm" c="dimmed">

            No queues yet. Run CRM bootstrap or create one under Work queues.

          </Text>

        ) : (

          <ScrollArea.Autosize mah={240}>

            {queues.map((q) => {

              const selected = activeId === q.id;

              return (

                <NavLink

                  key={q.id}

                  label={q.name}

                  leftSection={<IconList size={16} />}

                  active={selected}

                  variant="filled"

                  onClick={() => runQueue(q.id)}

                  styles={{

                    root: {

                      borderRadius: "var(--mantine-radius-sm)",

                      marginBottom: 4,

                      ...(selected

                        ? {

                            background: "var(--mantine-color-blue-light)",

                            color: "var(--mantine-color-blue-light-color)",

                            fontWeight: 600,

                          }

                        : {}),

                    },

                  }}

                />

              );

            })}

          </ScrollArea.Autosize>

        )}

      </Paper>



      {(runLoading || result) && (

        <Paper

          p="sm"

          withBorder

          styles={{

            root: {

              borderColor: result

                ? "var(--mantine-color-blue-4)"

                : "var(--mantine-color-default-border)",

            },

          }}

        >

          {runLoading ? (

            <Center py="lg">

              <Loader size="sm" />

            </Center>

          ) : result ? (

            <Stack gap="sm">

              <Group justify="space-between" align="flex-start" wrap="nowrap">

                <Stack gap={2} style={{ minWidth: 0 }}>

                  <Text fw={600} size="sm" lineClamp={2}>

                    {result.queue_name}

                  </Text>

                  <Text size="xs" c="dimmed">

                    Matching deals

                  </Text>

                </Stack>

                <Badge size="lg" variant="filled" color="blue" circle>

                  {result.count}

                </Badge>

              </Group>

              {result.leads.length === 0 ? (

                <Text size="sm" c="dimmed">

                  No matching deals.

                </Text>

              ) : (

                <ScrollArea.Autosize mah={360}>

                  <Table striped highlightOnHover withTableBorder>

                    <Table.Thead>

                      <Table.Tr>

                        <Table.Th>Deal</Table.Th>

                        <Table.Th>Revenue</Table.Th>

                      </Table.Tr>

                    </Table.Thead>

                    <Table.Tbody>

                      {result.leads.map((lead) => (

                        <Table.Tr key={lead.id}>

                          <Table.Td>

                            <Stack gap={2}>

                              <Link href={`/crm/lead/${lead.id}`}>{lead.name}</Link>

                              {lead.is_rotting && (

                                <Badge size="xs" color="orange" variant="light">

                                  Rotting

                                  {lead.days_in_stage != null ? ` ${lead.days_in_stage}d` : ""}

                                </Badge>

                              )}

                            </Stack>

                          </Table.Td>

                          <Table.Td>

                            <MonetaryCell value={lead.expected_revenue} />

                          </Table.Td>

                        </Table.Tr>

                      ))}

                    </Table.Tbody>

                  </Table>

                </ScrollArea.Autosize>

              )}

            </Stack>

          ) : null}

        </Paper>

      )}

    </Stack>

  );

}

