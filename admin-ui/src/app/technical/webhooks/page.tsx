"use client";
/**
 * Technical → Webhooks
 *
 * Manage outbound webhook subscribers (`ir_webhooks`, ADR-0010 outbox).
 * Each subscriber declares:
 *   - which events to listen for (record.created / updated / deleted)
 *   - optional model scope (one of the registered tenant models, or "any")
 *   - for record.updated: optional whitelist of fields whose change fires
 *     the delivery (empty list ⇒ any field change fires)
 *   - optional inbound-auth header sent with every delivery (HMAC signing
 *     in `X-Orbiteus-Signature` is unconditional)
 *
 * Backend contract (no auto-CRUD — see `modules/base/controller/router.py`):
 *   GET    /api/base/webhooks
 *   POST   /api/base/webhooks
 *   PUT    /api/base/webhooks/{id}
 *   DELETE /api/base/webhooks/{id}
 *   POST   /api/base/webhooks/{id}/test  → synthetic delivery
 *
 * Secret + auth_header_value are write-only on the wire — `GET` only
 * exposes `has_secret` / `has_auth_header_value` flags.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert, Badge, Box, Button, Checkbox, Code, CopyButton, Group, Loader,
  Modal, MultiSelect, PasswordInput, Paper, Select, Stack, Switch, Table,
  Text, TextInput, Title, Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle, IconCopy, IconCheck, IconPencil, IconPlayerPlay, IconPlus,
  IconRefresh, IconTrash, IconWebhook,
} from "@tabler/icons-react";
import { api } from "@/lib/api";
import { getCachedUiConfig } from "@/lib/modelConfig";
import { formatListDate } from "@/lib/formatters";

interface WebhookRow {
  id: string;
  name: string;
  url: string;
  event_mask: string[];
  model_filter: string | null;
  field_filter: string[];
  auth_header_name: string | null;
  has_auth_header_value: boolean;
  has_secret: boolean;
  is_active: boolean;
  last_delivery_at: string | null;
  last_delivery_status: string | null;
  create_date: string | null;
  /** Only populated by POST /api/base/webhooks (one-time secret reveal). */
  secret?: string;
}

interface ModelMeta {
  name: string;          // e.g. "crm.person"
  label: string;
  fields: { name: string; label: string }[];
}

interface FormState {
  id: string | null;
  name: string;
  url: string;
  event_created: boolean;
  event_updated: boolean;
  event_deleted: boolean;
  model_filter: string;       // "" → any
  field_filter: string[];
  auth_header_name: string;
  auth_header_value: string;  // only set when operator wants to (re)set it
  is_active: boolean;
  rotate_secret: boolean;
}

const EMPTY_FORM: FormState = {
  id: null,
  name: "",
  url: "",
  event_created: true,
  event_updated: true,
  event_deleted: true,
  model_filter: "",
  field_filter: [],
  auth_header_name: "",
  auth_header_value: "",
  is_active: true,
  rotate_secret: false,
};

const ANY_MODEL = "__any__";  // sentinel value for the "all models" option

function eventBadges(mask: string[]): React.ReactNode {
  const map: { [k: string]: { label: string; color: string } } = {
    "record.created": { label: "create", color: "green" },
    "record.updated": { label: "update", color: "blue" },
    "record.deleted": { label: "delete", color: "red" },
  };
  return (
    <Group gap={4}>
      {mask.length === 0 ? (
        <Badge size="xs" variant="light" color="gray">all events</Badge>
      ) : mask.map((e) => (
        <Badge key={e} size="xs" variant="light" color={map[e]?.color ?? "gray"}>
          {map[e]?.label ?? e}
        </Badge>
      ))}
    </Group>
  );
}

export default function WebhooksPage() {
  const [items, setItems] = useState<WebhookRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [models, setModels] = useState<ModelMeta[]>([]);

  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);

  // Initial loads
  const refreshList = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<{ items: WebhookRow[] }>("/base/webhooks", {
        skipGlobalErrorToast: true,
      });
      setItems(data.items ?? []);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail ?? "Failed to load webhooks.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refreshList(); }, [refreshList]);

  useEffect(() => {
    let cancelled = false;
    getCachedUiConfig()
      .then((cfg) => {
        if (cancelled) return;
        const flat: ModelMeta[] = [];
        for (const m of cfg.modules) {
          for (const model of m.models) {
            flat.push({
              name: model.name,
              label: model.label || model.name,
              fields: model.fields.map((f) => ({ name: f.name, label: f.label })),
            });
          }
        }
        flat.sort((a, b) => a.name.localeCompare(b.name));
        setModels(flat);
      })
      .catch(() => { /* ignore — form will degrade to text inputs */ });
    return () => { cancelled = true; };
  }, []);

  // Field options for the *currently selected* model in the form. When
  // model_filter is empty (any model), we union every model's fields so
  // the user can still scope updates by a common field name like "name".
  const fieldOptions = useMemo(() => {
    if (form.model_filter) {
      const m = models.find((x) => x.name === form.model_filter);
      return (m?.fields ?? []).map((f) => ({ value: f.name, label: `${f.name} — ${f.label}` }));
    }
    const seen = new Set<string>();
    const out: { value: string; label: string }[] = [];
    for (const m of models) {
      for (const f of m.fields) {
        if (seen.has(f.name)) continue;
        seen.add(f.name);
        out.push({ value: f.name, label: f.name });
      }
    }
    out.sort((a, b) => a.value.localeCompare(b.value));
    return out;
  }, [form.model_filter, models]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setRevealedSecret(null);
    setFormOpen(true);
  }

  function openEdit(row: WebhookRow) {
    setForm({
      id: row.id,
      name: row.name,
      url: row.url,
      event_created: row.event_mask.includes("record.created"),
      event_updated: row.event_mask.includes("record.updated"),
      event_deleted: row.event_mask.includes("record.deleted"),
      model_filter: row.model_filter ?? "",
      field_filter: row.field_filter ?? [],
      auth_header_name: row.auth_header_name ?? "",
      auth_header_value: "",
      is_active: row.is_active,
      rotate_secret: false,
    });
    setRevealedSecret(null);
    setFormOpen(true);
  }

  function buildEventMask(f: FormState): string[] {
    const out: string[] = [];
    if (f.event_created) out.push("record.created");
    if (f.event_updated) out.push("record.updated");
    if (f.event_deleted) out.push("record.deleted");
    return out;
  }

  async function submit() {
    setSubmitting(true);
    try {
      const event_mask = buildEventMask(form);
      const body: Record<string, unknown> = {
        name: form.name.trim(),
        url: form.url.trim(),
        event_mask,
        model_filter: form.model_filter || null,
        // Only include field_filter when "update" is in the mask, so
        // that toggling update off cleanly clears the gate.
        field_filter: form.event_updated ? form.field_filter : [],
        auth_header_name: form.auth_header_name.trim() || null,
        is_active: form.is_active,
      };
      if (form.auth_header_value.trim()) {
        body.auth_header_value = form.auth_header_value.trim();
      }

      let row: WebhookRow;
      if (form.id) {
        if (form.rotate_secret) body.secret = "";  // ignored on update; UI hint only
        const { data } = await api.put<WebhookRow>(
          `/base/webhooks/${form.id}`, body, { skipGlobalErrorToast: true });
        row = data;
        notifications.show({
          title: "Saved",
          message: "Webhook updated.",
          color: "green",
          icon: <IconCheck size={16} />,
        });
      } else {
        const { data } = await api.post<WebhookRow>(
          "/base/webhooks", body, { skipGlobalErrorToast: true });
        row = data;
        if (data.secret) setRevealedSecret(data.secret);
        notifications.show({
          title: "Webhook registered",
          message: "Copy the signing secret — it won't be shown again.",
          color: "green",
          icon: <IconCheck size={16} />,
        });
      }
      // If the API returned a secret on create, keep the form open so
      // the operator can copy it; otherwise close.
      if (!revealedSecret && !row.secret) setFormOpen(false);
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string | unknown } } };
      const detail = e.response?.data?.detail;
      const msg = typeof detail === "string"
        ? detail
        : "Failed to save webhook.";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(row: WebhookRow) {
    if (!confirm(`Delete webhook "${row.name}"? Audit history is retained.`)) return;
    try {
      await api.delete(`/base/webhooks/${row.id}`, { skipGlobalErrorToast: true });
      notifications.show({ title: "Deleted", message: row.name, color: "orange" });
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      notifications.show({
        title: "Delete failed",
        message: e.response?.data?.detail ?? "Could not delete.",
        color: "red",
      });
    }
  }

  async function onTest(row: WebhookRow) {
    try {
      const { data } = await api.post<WebhookRow>(
        `/base/webhooks/${row.id}/test`, {}, { skipGlobalErrorToast: true });
      notifications.show({
        title: "Test delivered",
        message: `Receiver replied with ${data.last_delivery_status ?? "—"}.`,
        color: "green",
        icon: <IconCheck size={16} />,
      });
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: { message?: string } | string } } };
      const detail = e.response?.data?.detail;
      const msg = typeof detail === "object" && detail && "message" in detail
        ? String((detail as { message: string }).message)
        : typeof detail === "string"
          ? detail
          : "Test delivery failed.";
      notifications.show({ title: "Test failed", message: msg, color: "red" });
      await refreshList();
    }
  }

  async function onToggleActive(row: WebhookRow, next: boolean) {
    try {
      await api.put(`/base/webhooks/${row.id}`, { is_active: next }, { skipGlobalErrorToast: true });
      await refreshList();
    } catch {
      notifications.show({ title: "Error", message: "Failed to toggle.", color: "red" });
    }
  }

  // --- render ----------------------------------------------------------

  return (
    <Stack gap="md">
      <Paper>
        <Group justify="space-between" align="center">
          <Group gap="sm" align="center">
            <IconWebhook size={22} stroke={1.5} />
            <Stack gap={0}>
              <Title order={3}>Webhooks</Title>
              <Text size="sm" c="dimmed">
                Outbound subscribers for tenant CRUD events. Every delivery is
                signed with HMAC-SHA256 (header `X-Orbiteus-Signature`); an
                optional inbound auth header can be configured for receivers
                that gate webhooks behind a custom token.
              </Text>
            </Stack>
          </Group>
          <Group gap="xs">
            <Button
              variant="default" size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={() => void refreshList()}
              loading={loading}
            >
              Refresh
            </Button>
            <Button
              size="sm"
              leftSection={<IconPlus size={16} />}
              onClick={openCreate}
            >
              New webhook
            </Button>
          </Group>
        </Group>
      </Paper>

      {error && (
        <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
          {error}
        </Alert>
      )}

      <Paper p={0}>
        <Table withColumnBorders highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: 70 }}>Active</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Target URL</Table.Th>
              <Table.Th>Model</Table.Th>
              <Table.Th>Events</Table.Th>
              <Table.Th>Watched fields</Table.Th>
              <Table.Th>Last delivery</Table.Th>
              <Table.Th style={{ width: 200 }}> </Table.Th>
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
                    No webhooks registered yet.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              items.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>
                    <Switch
                      size="xs"
                      checked={row.is_active}
                      onChange={(e) => void onToggleActive(row, e.currentTarget.checked)}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={500}>{row.name}</Text>
                    {row.auth_header_name && (
                      <Text size="xs" c="dimmed">
                        auth: {row.auth_header_name}
                        {row.has_auth_header_value ? "" : " (empty)"}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Code style={{ fontSize: 11, wordBreak: "break-all" }}>{row.url}</Code>
                  </Table.Td>
                  <Table.Td>
                    {row.model_filter
                      ? <Code style={{ fontSize: 11 }}>{row.model_filter}</Code>
                      : <Badge size="xs" variant="light" color="gray">any</Badge>}
                  </Table.Td>
                  <Table.Td>{eventBadges(row.event_mask)}</Table.Td>
                  <Table.Td>
                    {row.field_filter.length === 0 ? (
                      <Text size="xs" c="dimmed">any field</Text>
                    ) : (
                      <Group gap={4}>
                        {row.field_filter.map((f) => (
                          <Badge key={f} size="xs" variant="light" color="gray">{f}</Badge>
                        ))}
                      </Group>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {row.last_delivery_at ? (
                      <Stack gap={2}>
                        <Text size="xs">{formatListDate(row.last_delivery_at)}</Text>
                        <Badge
                          size="xs" variant="light"
                          color={row.last_delivery_status?.startsWith("2") ? "green" : "red"}
                        >
                          {row.last_delivery_status}
                        </Badge>
                      </Stack>
                    ) : <Text size="xs" c="dimmed">—</Text>}
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} justify="flex-end">
                      <Tooltip label="Send test delivery">
                        <Button
                          variant="subtle" color="gray" size="xs"
                          leftSection={<IconPlayerPlay size={14} />}
                          onClick={() => void onTest(row)}
                        >
                          Test
                        </Button>
                      </Tooltip>
                      <Tooltip label="Edit">
                        <Button
                          variant="subtle" color="gray" size="xs"
                          leftSection={<IconPencil size={14} />}
                          onClick={() => openEdit(row)}
                        >
                          Edit
                        </Button>
                      </Tooltip>
                      <Tooltip label="Delete">
                        <Button
                          variant="subtle" color="red" size="xs"
                          leftSection={<IconTrash size={14} />}
                          onClick={() => void onDelete(row)}
                        >
                          Delete
                        </Button>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={formOpen}
        onClose={() => { setFormOpen(false); setRevealedSecret(null); }}
        title={form.id ? "Edit webhook" : "New webhook"}
        size="lg"
        centered
      >
        <Stack gap="md">
          {revealedSecret && (
            <Alert variant="light" color="yellow" icon={<IconAlertCircle size={16} />}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>
                  Save this signing secret now — it won&apos;t be shown again.
                </Text>
                <Group gap="xs">
                  <Code style={{ flex: 1, fontSize: 11, wordBreak: "break-all" }}>
                    {revealedSecret}
                  </Code>
                  <CopyButton value={revealedSecret}>
                    {({ copied, copy }) => (
                      <Button
                        size="xs" variant="default"
                        leftSection={<IconCopy size={14} />}
                        color={copied ? "green" : "gray"}
                        onClick={copy}
                      >
                        {copied ? "Copied" : "Copy"}
                      </Button>
                    )}
                  </CopyButton>
                </Group>
                <Text size="xs" c="dimmed">
                  Add this as the HMAC key on your receiver. Every delivery will
                  carry the SHA-256 HMAC of the body in
                  <Code style={{ fontSize: 11 }}>X-Orbiteus-Signature</Code>.
                </Text>
              </Stack>
            </Alert>
          )}

          <TextInput
            label="Name"
            description="Free-form label shown in the table."
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
            required
          />

          <TextInput
            label="Target URL"
            description="HTTPS endpoint that will receive the JSON body."
            placeholder="https://example.com/orbiteus/hook"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.currentTarget.value })}
            required
          />

          <Box>
            <Text size="sm" fw={500} mb={4}>Events</Text>
            <Group gap="md">
              <Checkbox
                label="record.created"
                checked={form.event_created}
                onChange={(e) => setForm({ ...form, event_created: e.currentTarget.checked })}
              />
              <Checkbox
                label="record.updated"
                checked={form.event_updated}
                onChange={(e) => setForm({ ...form, event_updated: e.currentTarget.checked })}
              />
              <Checkbox
                label="record.deleted"
                checked={form.event_deleted}
                onChange={(e) => setForm({ ...form, event_deleted: e.currentTarget.checked })}
              />
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              Empty selection = no events delivered. The dispatcher silently
              skips a webhook whose mask doesn&apos;t include the fired event.
            </Text>
          </Box>

          <Select
            label="Model"
            description="Limit to a single registered model, or fan out for everything in the tenant."
            placeholder="Select a model"
            data={[
              { value: ANY_MODEL, label: "Any model in this tenant" },
              ...models.map((m) => ({ value: m.name, label: `${m.name} — ${m.label}` })),
            ]}
            value={form.model_filter || ANY_MODEL}
            onChange={(v) => setForm({
              ...form,
              model_filter: !v || v === ANY_MODEL ? "" : v,
              // Drop previously-selected fields that no longer exist on
              // the new model — keeps the payload coherent.
              field_filter: [],
            })}
            allowDeselect={false}
            searchable
          />

          {form.event_updated && (
            <MultiSelect
              label="Watched fields (only for record.updated)"
              description={
                form.model_filter
                  ? "Empty = any field change fires. Pick one or more to gate."
                  : "Empty = any field change fires. The list shows the union of all model fields; pick names that exist on the models you care about."
              }
              data={fieldOptions}
              value={form.field_filter}
              onChange={(v) => setForm({ ...form, field_filter: v })}
              searchable
              clearable
            />
          )}

          <Box>
            <Text size="sm" fw={500} mb={4}>Inbound auth header (optional)</Text>
            <Group gap="sm" align="flex-end">
              <TextInput
                label="Header name"
                placeholder="Authorization"
                value={form.auth_header_name}
                onChange={(e) => setForm({ ...form, auth_header_name: e.currentTarget.value })}
                style={{ flex: 1 }}
              />
              <PasswordInput
                label={form.id ? "Header value (leave empty to keep existing)" : "Header value"}
                placeholder="Bearer …"
                value={form.auth_header_value}
                onChange={(e) => setForm({ ...form, auth_header_value: e.currentTarget.value })}
                style={{ flex: 2 }}
              />
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              Sent on every delivery in addition to the unconditional
              <Code style={{ fontSize: 11 }}>X-Orbiteus-Signature</Code> HMAC.
              Useful for receivers that gate the endpoint behind
              <Code style={{ fontSize: 11 }}>Authorization: Bearer …</Code>.
            </Text>
          </Box>

          <Switch
            label="Active"
            description="When off, the dispatcher skips this subscriber but the row is preserved."
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.currentTarget.checked })}
          />

          <Group justify="flex-end">
            <Button
              variant="subtle"
              onClick={() => { setFormOpen(false); setRevealedSecret(null); }}
            >
              Close
            </Button>
            <Button
              loading={submitting}
              leftSection={<IconCheck size={16} />}
              onClick={() => void submit()}
              disabled={!form.name.trim() || !form.url.trim()}
            >
              {form.id ? "Save changes" : "Register webhook"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
