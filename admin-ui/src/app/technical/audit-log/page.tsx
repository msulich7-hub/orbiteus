"use client";
/**
 * Technical → Log Activity
 *
 * Read-only viewer over the mandatory audit trail (`ir_audit_log`,
 * ADR-0014). Streams the latest mutations on the tenant via the same
 * SSE backplane that drives ResourceList, so a busy system shows new
 * rows in real time without manual refresh.
 *
 * Backend contract: `GET /api/base/audit-log`
 *   query: model, record_id, actor, operation, user_id, limit, offset
 *   returns: { items: AuditRow[], total, limit, offset }
 *
 * One row covers one CRUD or auth event:
 *   id, create_date, tenant_id, actor (user|ai|system),
 *   user_id, request_id, model, record_id,
 *   operation (create|update|delete|tool_call|login|login_failed),
 *   diff (Record<field, [old, new]> | null),
 *   metadata (Record<string, unknown> | null)
 */
import { Fragment, useCallback, useEffect, useState } from "react";
import {
  Alert, Badge, Button, Code, Collapse, Group, Loader, Pagination, Paper,
  Select, Stack, Table, Text, TextInput, Title, Tooltip,
} from "@mantine/core";
import {
  IconAlertCircle, IconChevronDown, IconChevronRight, IconHistory,
  IconRefresh,
} from "@tabler/icons-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatListDate } from "@/lib/formatters";
import { getCachedUiConfig } from "@/lib/modelConfig";

interface AuditRow {
  id: string;
  create_date: string | null;
  tenant_id: string | null;
  actor: "user" | "ai" | "system" | string;
  user_id: string | null;
  request_id: string | null;
  model: string | null;
  record_id: string | null;
  operation: string;
  diff: Record<string, [unknown, unknown]> | null;
  metadata: Record<string, unknown> | null;
}

interface AuditPage {
  items: AuditRow[];
  total: number;
  limit: number;
  offset: number;
}

const PAGE_SIZE = 50;

const OPERATION_OPTIONS = [
  { value: "",             label: "All operations" },
  { value: "create",       label: "create" },
  { value: "update",       label: "update" },
  { value: "delete",       label: "delete" },
  { value: "tool_call",    label: "tool_call" },
  { value: "login",        label: "login" },
  { value: "login_failed", label: "login_failed" },
];

const ACTOR_OPTIONS = [
  { value: "",       label: "All actors" },
  { value: "user",   label: "user" },
  { value: "ai",     label: "ai" },
  { value: "system", label: "system" },
];

function operationColor(op: string): string {
  switch (op) {
    case "create":       return "green";
    case "update":       return "blue";
    case "delete":       return "red";
    case "tool_call":    return "violet";
    case "login":        return "gray";
    case "login_failed": return "orange";
    default:             return "gray";
  }
}

function actorColor(actor: string): string {
  switch (actor) {
    case "user":   return "blue";
    case "ai":     return "violet";
    case "system": return "gray";
    default:       return "gray";
  }
}

function shortUuid(s: string | null): string {
  return s ? `${s.slice(0, 8)}…` : "—";
}

export default function AuditLogPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [page, setPage] = useState(1);
  const [model, setModel] = useState("");
  const [actor, setActor] = useState("");
  const [operation, setOperation] = useState("");

  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      };
      if (model.trim()) params.model = model.trim();
      if (actor) params.actor = actor;
      if (operation) params.operation = operation;

      const { data } = await api.get<AuditPage>("/base/audit-log", {
        params,
        skipGlobalErrorToast: true,
      });
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail ?? "Failed to load audit log.");
    } finally {
      setLoading(false);
    }
  }, [page, model, actor, operation]);

  useEffect(() => { void refresh(); }, [refresh]);

  // Realtime: the audit log captures CRUD / auth events on *every* model,
  // so we have to listen to the union of `tenant:<tid>:model:<m>:list`
  // topics rather than a single one. Backend's
  // `/api/realtime/subscribe` accepts `?topic=` repeated, so we just
  // pass every registered model from ui-config in one shot.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!user?.tenant_id) return;

    let es: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    let attempts = 0;

    async function connect() {
      if (cancelled) return;
      const cfg = await getCachedUiConfig().catch(() => null);
      if (cancelled || !cfg || !user?.tenant_id) return;

      const topics = cfg.modules.flatMap((m) =>
        m.models.map((mod) => `tenant:${user.tenant_id}:model:${mod.name}:list`),
      );
      if (topics.length === 0) return;

      const url = `/api/realtime/subscribe?${topics
        .map((t) => `topic=${encodeURIComponent(t)}`)
        .join("&")}`;

      es = new EventSource(url);
      es.addEventListener("open", () => { attempts = 0; });
      es.addEventListener("message", () => {
        // Coalesce bursts — at most one refresh per ~600ms.
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => { void refresh(); }, 600);
      });
      es.addEventListener("error", () => {
        es?.close();
        es = null;
        if (cancelled) return;
        attempts += 1;
        const delay = Math.min(3000 * Math.pow(1.5, attempts - 1), 30_000);
        setTimeout(() => { void connect(); }, delay);
      });
    }

    void connect();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      es?.close();
    };
  }, [user?.tenant_id, refresh]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function renderDiff(row: AuditRow) {
    if (!row.diff || Object.keys(row.diff).length === 0) {
      return (
        <Text size="xs" c="dimmed">
          {row.operation === "create"
            ? "Initial values stored — no per-field diff captured."
            : "No field-level diff."}
        </Text>
      );
    }
    return (
      <Stack gap={4}>
        {Object.entries(row.diff).map(([field, pair]) => {
          const [oldVal, newVal] = Array.isArray(pair) ? pair : [null, pair];
          return (
            <Group key={field} gap="xs" wrap="nowrap" align="flex-start">
              <Badge variant="light" color="gray" size="xs">{field}</Badge>
              <Code style={{ fontSize: 11 }} c="red">
                {oldVal === null ? "∅" : JSON.stringify(oldVal)}
              </Code>
              <Text size="xs" c="dimmed">→</Text>
              <Code style={{ fontSize: 11 }} c="green">
                {newVal === null ? "∅" : JSON.stringify(newVal)}
              </Code>
            </Group>
          );
        })}
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Paper>
        <Group gap="sm" align="center" justify="space-between">
          <Group gap="sm" align="center">
            <IconHistory size={22} stroke={1.5} />
            <Stack gap={0}>
              <Title order={3}>Log Activity</Title>
              <Text size="sm" c="dimmed">
                Mandatory audit trail (`ir_audit_log`, ADR-0014). Every CRUD /
                auth event in the tenant lands here; the page auto-refreshes on
                the same SSE backplane that drives the list views.
              </Text>
            </Stack>
          </Group>
          <Group gap="xs">
            <Badge variant="light" color="blue" size="lg">{total}</Badge>
            <Text size="sm" c="dimmed">events</Text>
            <Tooltip label="Refresh now">
              <Button
                variant="default" size="xs"
                leftSection={<IconRefresh size={14} />}
                onClick={() => void refresh()}
                loading={loading}
              >
                Refresh
              </Button>
            </Tooltip>
          </Group>
        </Group>
      </Paper>

      <Paper>
        <Group gap="sm" align="flex-end">
          <TextInput
            label="Model"
            placeholder="e.g. crm.person"
            value={model}
            onChange={(e) => { setModel(e.currentTarget.value); setPage(1); }}
            style={{ flex: 1, minWidth: 180 }}
          />
          <Select
            label="Actor"
            data={ACTOR_OPTIONS}
            value={actor}
            onChange={(v) => { setActor(v ?? ""); setPage(1); }}
            allowDeselect={false}
            style={{ width: 160 }}
          />
          <Select
            label="Operation"
            data={OPERATION_OPTIONS}
            value={operation}
            onChange={(v) => { setOperation(v ?? ""); setPage(1); }}
            allowDeselect={false}
            style={{ width: 180 }}
          />
        </Group>
      </Paper>

      {error && (
        <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
          {error}
        </Alert>
      )}

      <Paper p={0}>
        <Table withColumnBorders highlightOnHover style={{ tableLayout: "fixed" }}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 28 }}> </Table.Th>
              <Table.Th style={{ width: 170 }}>Timestamp</Table.Th>
              <Table.Th style={{ width: 90 }}>Actor</Table.Th>
              <Table.Th style={{ width: 130 }}>Operation</Table.Th>
              <Table.Th>Model</Table.Th>
              <Table.Th style={{ width: 110 }}>Record</Table.Th>
              <Table.Th style={{ width: 110 }}>User</Table.Th>
              <Table.Th style={{ width: 130 }}>Request</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {loading && items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Group justify="center" py="lg"><Loader size="sm" color="gray" /></Group>
                </Table.Td>
              </Table.Tr>
            ) : items.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Text size="sm" c="dimmed" ta="center" py="lg">
                    No audit entries match the current filter.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              items.map((row) => {
                const isOpen = expanded.has(row.id);
                return (
                  <Fragment key={row.id}>
                    <Table.Tr
                      onClick={() => toggleExpanded(row.id)}
                      style={{ cursor: "pointer" }}
                    >
                      <Table.Td>
                        {isOpen ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{formatListDate(row.create_date) || "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" variant="light" color={actorColor(row.actor)}>
                          {row.actor}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" variant="light" color={operationColor(row.operation)}>
                          {row.operation}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Code style={{ fontSize: 11 }}>{row.model ?? "—"}</Code>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label={row.record_id ?? "—"} disabled={!row.record_id}>
                          <Code style={{ fontSize: 11 }}>{shortUuid(row.record_id)}</Code>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label={row.user_id ?? "—"} disabled={!row.user_id}>
                          <Code style={{ fontSize: 11 }}>{shortUuid(row.user_id)}</Code>
                        </Tooltip>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label={row.request_id ?? "—"} disabled={!row.request_id}>
                          <Code style={{ fontSize: 11 }}>
                            {row.request_id ? row.request_id.slice(0, 14) + "…" : "—"}
                          </Code>
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td colSpan={8} p={0} style={{ border: 0 }}>
                        <Collapse in={isOpen}>
                          <Paper m="xs" p="sm" radius="sm" withBorder
                            bg="var(--mantine-color-default)">
                            <Stack gap="xs">
                              <Group gap="xs">
                                <Badge size="xs" variant="light" color="gray">id</Badge>
                                <Code style={{ fontSize: 11 }}>{row.id}</Code>
                              </Group>
                              <Group gap="xs" align="flex-start">
                                <Badge size="xs" variant="light" color="gray">diff</Badge>
                                <div style={{ flex: 1 }}>{renderDiff(row)}</div>
                              </Group>
                              {row.metadata && Object.keys(row.metadata).length > 0 && (
                                <Group gap="xs" align="flex-start">
                                  <Badge size="xs" variant="light" color="gray">metadata</Badge>
                                  <Code block style={{ flex: 1, fontSize: 11 }}>
                                    {JSON.stringify(row.metadata, null, 2)}
                                  </Code>
                                </Group>
                              )}
                            </Stack>
                          </Paper>
                        </Collapse>
                      </Table.Td>
                    </Table.Tr>
                  </Fragment>
                );
              })
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      {totalPages > 1 && (
        <Group justify="center">
          <Pagination
            total={totalPages}
            value={page}
            onChange={setPage}
            siblings={1}
            boundaries={1}
          />
        </Group>
      )}
    </Stack>
  );
}
