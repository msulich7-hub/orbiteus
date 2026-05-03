"use client";
/**
 * Technical → AI Integration
 *
 * BYOK admin surface:
 *  - List configured providers (`GET /api/ai/credentials`).
 *  - Add / overwrite a credential (`POST /api/ai/credentials`). The
 *    backend pings the provider with the supplied secret before storing
 *    it; a bad key returns 400 and we never persist it.
 *  - Delete a credential (`DELETE /api/ai/credentials/{provider}`).
 *  - Run a one-shot test prompt (`POST /api/ai/chat`) against the
 *    selected provider so an operator can verify the key is live and
 *    the budget is intact without leaving the page.
 *
 * Secrets are stored encrypted at rest (Fernet, ADR-0004) and never
 * leave the backend after upsert — the API key input is write-only;
 * `GET /api/ai/credentials` returns metadata only.
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert, Badge, Button, Code, Group, Loader, NumberInput, Paper,
  PasswordInput, Select, Stack, Table, Text, Textarea, TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle, IconCheck, IconPlugConnected, IconSend, IconSparkles,
  IconTrash,
} from "@tabler/icons-react";
import { api } from "@/lib/api";

interface CredentialRow {
  id: string;
  provider: "anthropic" | "openai" | "ollama";
  model_default: string | null;
  is_active: boolean;
  monthly_token_budget: number | null;
  usage_tokens: number;
}

interface ChatResponse {
  text: string;
  tool_calls?: unknown[];
  usage_tokens: number;
  finish_reason?: string;
}

const PROVIDERS: { value: CredentialRow["provider"]; label: string; defaultModel: string }[] = [
  { value: "anthropic", label: "Anthropic (Claude)", defaultModel: "claude-3-5-sonnet-latest" },
  { value: "openai",    label: "OpenAI (GPT)",       defaultModel: "gpt-4o-mini" },
  { value: "ollama",    label: "Ollama (local)",     defaultModel: "llama3.1" },
];

function providerLabel(p: string): string {
  return PROVIDERS.find((x) => x.value === p)?.label ?? p;
}

function defaultModelFor(p: CredentialRow["provider"]): string {
  return PROVIDERS.find((x) => x.value === p)?.defaultModel ?? "";
}

function formatTokens(n: number): string {
  if (!n) return "0";
  return new Intl.NumberFormat("en-US").format(n);
}

export default function AiIntegrationPage() {
  // ---- Configured providers ----
  const [credentials, setCredentials] = useState<CredentialRow[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  const refreshList = useCallback(async () => {
    setLoadingList(true);
    try {
      const { data } = await api.get<{ items: CredentialRow[] }>("/ai/credentials", {
        skipGlobalErrorToast: true,
      });
      setCredentials(data.items ?? []);
    } catch {
      setCredentials([]);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => { void refreshList(); }, [refreshList]);

  // ---- Add / overwrite form ----
  const [provider, setProvider] = useState<CredentialRow["provider"]>("anthropic");
  const [secret, setSecret] = useState("");
  const [modelDefault, setModelDefault] = useState(defaultModelFor("anthropic"));
  const [budget, setBudget] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  function onProviderChange(v: string | null) {
    if (!v) return;
    const next = v as CredentialRow["provider"];
    setProvider(next);
    setModelDefault(defaultModelFor(next));
  }

  async function onSave() {
    setSubmitError("");
    if (!secret.trim()) {
      setSubmitError("API key is required.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/ai/credentials", {
        provider,
        secret: secret.trim(),
        model_default: modelDefault.trim() || null,
        monthly_token_budget: typeof budget === "number" ? budget : null,
      }, { skipGlobalErrorToast: true });
      notifications.show({
        title: "Saved",
        message: `Stored ${providerLabel(provider)} credential.`,
        color: "green",
        icon: <IconCheck size={16} />,
      });
      setSecret("");
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      const raw = e.response?.data?.detail ?? "Failed to save credential.";
      setSubmitError(humaniseAiError(raw));
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(p: string) {
    if (!confirm(`Delete the ${providerLabel(p)} credential? Saved AI usage counters are retained.`)) {
      return;
    }
    try {
      await api.delete(`/ai/credentials/${p}`, { skipGlobalErrorToast: true });
      notifications.show({
        title: "Deleted",
        message: `${providerLabel(p)} credential removed.`,
        color: "orange",
      });
      await refreshList();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      notifications.show({
        title: "Delete failed",
        message: e.response?.data?.detail ?? "Could not delete credential.",
        color: "red",
      });
    }
  }

  // ---- Test query ----
  const [testProvider, setTestProvider] = useState<CredentialRow["provider"]>("anthropic");
  const [testPrompt, setTestPrompt] = useState(
    "Reply with exactly one word: hello"
  );
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState<ChatResponse | null>(null);
  const [testError, setTestError] = useState("");

  async function onTest() {
    setTestError("");
    setTestResult(null);
    setTestRunning(true);
    try {
      const { data } = await api.post<ChatResponse>("/ai/chat", {
        provider: testProvider,
        messages: [{ role: "user", content: testPrompt }],
      }, { skipGlobalErrorToast: true });
      setTestResult(data);
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: unknown } } };
      const detail = e.response?.data?.detail;
      let msg = "Test query failed.";
      if (typeof detail === "string") {
        msg = detail;
      } else if (detail && typeof detail === "object" && "message" in detail) {
        msg = String((detail as { message: string }).message);
      }
      msg = humaniseAiError(msg);
      if (e.response?.status === 412) {
        msg = `${msg} Configure the ${providerLabel(testProvider)} credential first.`;
      } else if (e.response?.status === 429) {
        msg = `${msg} Monthly token budget exceeded.`;
      }
      setTestError(msg);
    } finally {
      setTestRunning(false);
    }
  }

  /**
   * Re-word a few backend error strings into something an operator can
   * act on without reading FastAPI internals.
   */
  function humaniseAiError(raw: string): string {
    if (/tenant context required/i.test(raw)) {
      return (
        "Your account is not bound to a tenant, so AI credentials cannot " +
        "be stored or used. Re-create the user under Technical → Access, " +
        "or run the bootstrap with BOOTSTRAP_ADMIN_TENANT set, then sign " +
        "in again."
      );
    }
    if (/provider rejected/i.test(raw)) {
      return (
        "The provider rejected the supplied API key — double-check the " +
        "value and that the key is enabled for the selected model."
      );
    }
    return raw;
  }

  // ---- Render ----
  const hasCredential = (p: string) => credentials.some((c) => c.provider === p);

  return (
    <Stack gap="md">
      <Paper>
        <Group gap="sm" align="center">
          <IconSparkles size={22} stroke={1.5} />
          <Stack gap={0}>
            <Title order={3}>AI Integration</Title>
            <Text size="sm" c="dimmed">
              Bring-your-own-key per tenant. Keys are encrypted at rest
              (Fernet, ADR-0004) and never returned by the API after save.
            </Text>
          </Stack>
        </Group>
      </Paper>

      {/* List of configured providers */}
      <Paper>
        <Stack gap="sm">
          <Group justify="space-between" align="center">
            <Title order={5}>Configured providers</Title>
            <Button variant="subtle" size="xs" onClick={() => void refreshList()}>
              Refresh
            </Button>
          </Group>

          {loadingList ? (
            <Group justify="center" py="md"><Loader size="sm" color="gray" /></Group>
          ) : credentials.length === 0 ? (
            <Alert variant="light" color="gray" icon={<IconPlugConnected size={16} />}>
              No AI provider configured for this tenant. Add a credential below to enable
              the dashboard prompt input, the Cmd+K AI suggestions, and the test query
              tool.
            </Alert>
          ) : (
            <Table withTableBorder withColumnBorders striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Provider</Table.Th>
                  <Table.Th>Default model</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Monthly budget</Table.Th>
                  <Table.Th>Usage (tokens)</Table.Th>
                  <Table.Th style={{ width: 60 }}> </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {credentials.map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td>
                      <Group gap="xs">
                        <Text fw={500}>{providerLabel(c.provider)}</Text>
                        <Badge color="gray" variant="light" size="xs">{c.provider}</Badge>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Code>{c.model_default ?? defaultModelFor(c.provider)}</Code>
                    </Table.Td>
                    <Table.Td>
                      {c.is_active
                        ? <Badge color="green" variant="light">active</Badge>
                        : <Badge color="gray" variant="light">disabled</Badge>}
                    </Table.Td>
                    <Table.Td>
                      {c.monthly_token_budget == null
                        ? <Text c="dimmed" size="sm">unlimited</Text>
                        : formatTokens(c.monthly_token_budget)}
                    </Table.Td>
                    <Table.Td>{formatTokens(c.usage_tokens)}</Table.Td>
                    <Table.Td>
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={() => void onDelete(c.provider)}
                      >
                        Delete
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Stack>
      </Paper>

      {/* Add / overwrite */}
      <Paper>
        <Stack gap="sm">
          <Title order={5}>Add or update a credential</Title>
          <Text size="sm" c="dimmed">
            The backend pings the provider with the supplied API key before
            storing it; a rejected key is never persisted. Saving a key for a
            provider that already exists overwrites the previous secret.
          </Text>

          {submitError && (
            <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
              {submitError}
            </Alert>
          )}

          <Select
            label="Provider"
            data={PROVIDERS.map((p) => ({
              value: p.value,
              label: hasCredential(p.value) ? `${p.label} — already configured` : p.label,
            }))}
            value={provider}
            onChange={onProviderChange}
            allowDeselect={false}
          />

          <PasswordInput
            label="API key"
            description={
              provider === "ollama"
                ? "For local Ollama use any non-empty placeholder; the secret is not used at request time."
                : "The key is sent over HTTPS, never echoed back, and stored encrypted at rest."
            }
            placeholder={provider === "anthropic" ? "sk-ant-…" : provider === "openai" ? "sk-…" : "ollama-local"}
            value={secret}
            onChange={(e) => setSecret(e.currentTarget.value)}
            required
          />

          <TextInput
            label="Default model"
            description="Used when /api/ai/chat is called without an explicit `model` field."
            value={modelDefault}
            onChange={(e) => setModelDefault(e.currentTarget.value)}
            placeholder={defaultModelFor(provider)}
          />

          <NumberInput
            label="Monthly token budget"
            description="Soft cap per tenant; calls return 429 once this is reached. Leave empty for unlimited."
            value={budget}
            onChange={(v) => setBudget(typeof v === "number" ? v : "")}
            min={0}
            step={10000}
            thousandSeparator=" "
            allowNegative={false}
            allowDecimal={false}
          />

          <Group justify="flex-end">
            <Button
              loading={submitting}
              leftSection={<IconCheck size={16} />}
              onClick={() => void onSave()}
            >
              {hasCredential(provider) ? "Overwrite credential" : "Save credential"}
            </Button>
          </Group>
        </Stack>
      </Paper>

      {/* Test query */}
      <Paper>
        <Stack gap="sm">
          <Title order={5}>Test query</Title>
          <Text size="sm" c="dimmed">
            Sends a single user message through <Code>POST /api/ai/chat</Code>{" "}
            against the selected provider. Useful to verify a freshly added
            key, the active budget, and round-trip latency without leaving
            the admin shell.
          </Text>

          <Select
            label="Provider"
            data={PROVIDERS.map((p) => ({ value: p.value, label: p.label }))}
            value={testProvider}
            onChange={(v) => v && setTestProvider(v as CredentialRow["provider"])}
            allowDeselect={false}
          />

          <Textarea
            label="Prompt"
            description="Single-turn user message. Backend wraps it as { role: 'user', content: … }."
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.currentTarget.value)}
            autosize
            minRows={2}
            maxRows={6}
          />

          <Group justify="flex-end">
            <Button
              loading={testRunning}
              leftSection={<IconSend size={16} />}
              onClick={() => void onTest()}
              disabled={!testPrompt.trim()}
            >
              Send test query
            </Button>
          </Group>

          {testError && (
            <Alert variant="light" color="red" icon={<IconAlertCircle size={16} />}>
              {testError}
            </Alert>
          )}

          {testResult && (
            <Paper withBorder p="sm" radius="sm" bg="var(--mantine-color-default)">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Group gap="xs">
                    <Badge color="green" variant="light">response</Badge>
                    {testResult.finish_reason && (
                      <Badge color="gray" variant="light" size="xs">
                        {testResult.finish_reason}
                      </Badge>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    {formatTokens(testResult.usage_tokens)} tokens used
                  </Text>
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {testResult.text || "(empty response)"}
                </Text>
              </Stack>
            </Paper>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
