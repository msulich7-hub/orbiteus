"use client";

import {
  Alert,
  Badge,
  Button,
  Container,
  FileButton,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconCheck, IconPaperclip, IconSend } from "@tabler/icons-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useRealtimeShareResource } from "@/lib/realtime";

interface ResourceView {
  resource_model: string;
  resource_id: string;
  permissions: string[];
  /** Surfaced by `/api/portal/exchange` so the realtime hook can build the topic. */
  tenant_id: string;
  /** "readonly" by default — DoD §12.5. */
  view_mode: "readonly" | "editable";
  /** Mutation endpoints the share-token unlocks (DoD §12.4). */
  available_mutations: string[];
  payload: Record<string, unknown>;
}

export default function ShareLinkPage({ params }: { params: { token: string } }) {
  const [view, setView] = useState<ResourceView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  // "live" badge — flashes on every realtime event so the visitor knows the
  // page reflects the latest state without a manual reload.
  const [liveAt, setLiveAt] = useState<number | null>(null);

  const reload = useCallback(() => setRefreshTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/portal/exchange?token=${encodeURIComponent(params.token)}`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail ?? "Invalid or expired share link");
        }
        return (await r.json()) as ResourceView;
      })
      .then((data) => {
        if (!cancelled) setView(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [params.token, refreshTick]);

  // Subscribe to realtime updates for this resource. When the backend
  // emits `record.updated`, refetch `/api/portal/exchange` so the page
  // reflects the new payload without forcing the visitor to reload.
  useRealtimeShareResource(
    {
      shareToken: params.token,
      tenantId: view?.tenant_id,
      model: view?.resource_model,
      recordId: view?.resource_id,
    },
    () => {
      setLiveAt(Date.now());
      reload();
    },
  );

  // -- Mutations --------------------------------------------------------
  const canComment = view?.available_mutations.includes("portal.comment") ?? false;
  const canAttach = view?.available_mutations.includes("portal.attachment") ?? false;

  return (
    <Container size="md" py="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>Shared resource</Title>
          {liveAt ? (
            <Badge color="green" variant="light">
              live · last update {new Date(liveAt).toLocaleTimeString()}
            </Badge>
          ) : null}
        </Group>
        {error ? <Alert color="red" title="Cannot open the share link">{error}</Alert> : null}
        {!error && !view ? <Loader /> : null}
        {view ? (
          <>
            <Paper withBorder p="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600}>
                  {view.resource_model} / {view.resource_id}
                </Text>
                <Badge variant="light" color="gray">
                  {view.view_mode}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed" mt="xs">
                Permissions: {view.permissions.join(", ")}
              </Text>
              <pre style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
                {JSON.stringify(view.payload, null, 2)}
              </pre>
            </Paper>
            {canComment ? (
              <CommentSurface token={params.token} onSubmitted={reload} />
            ) : null}
            {canAttach ? (
              <AttachmentSurface token={params.token} onSubmitted={reload} />
            ) : null}
          </>
        ) : null}
      </Stack>
    </Container>
  );
}


// ---------------------------------------------------------------------------
// Comment surface — POST /api/portal/comment
// ---------------------------------------------------------------------------

function CommentSurface({
  token, onSubmitted,
}: {
  token: string;
  onSubmitted: () => void;
}) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  async function handleSubmit() {
    if (!body.trim()) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const r = await fetch("/api/portal/comment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, body }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        const detail = typeof j.detail === "string" ? j.detail : "Could not post comment.";
        throw new Error(detail);
      }
      setBody("");
      setFeedback({ kind: "ok", msg: "Comment recorded." });
      onSubmitted();
    } catch (err) {
      setFeedback({
        kind: "err",
        msg: err instanceof Error ? err.message : "Could not post comment.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Title order={4}>Add a comment</Title>
        <Textarea
          placeholder="Write a quick update and press Send to attach it to the record."
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
          autosize
          minRows={3}
          maxRows={8}
        />
        <Group justify="space-between" align="center">
          {feedback ? (
            <Text size="sm" c={feedback.kind === "ok" ? "green" : "red"}>
              {feedback.msg}
            </Text>
          ) : <span />}
          <Button
            leftSection={<IconSend size={16} />}
            loading={submitting}
            onClick={handleSubmit}
            disabled={!body.trim()}
          >
            Send
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}


// ---------------------------------------------------------------------------
// Attachment surface — POST /api/portal/attachment (multipart)
// ---------------------------------------------------------------------------

function AttachmentSurface({
  token, onSubmitted,
}: {
  token: string;
  onSubmitted: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const resetRef = useRef<() => void>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  async function handleSubmit() {
    if (!file) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const fd = new FormData();
      fd.append("token", token);
      fd.append("file", file);
      const r = await fetch("/api/portal/attachment", {
        method: "POST",
        body: fd,
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        const detail = typeof j.detail === "string" ? j.detail : "Could not upload attachment.";
        throw new Error(detail);
      }
      setFile(null);
      resetRef.current?.();
      setFeedback({ kind: "ok", msg: "Attachment uploaded." });
      onSubmitted();
    } catch (err) {
      setFeedback({
        kind: "err",
        msg: err instanceof Error ? err.message : "Could not upload attachment.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Paper withBorder p="md">
      <Stack gap="sm">
        <Title order={4}>Add an attachment</Title>
        <Group>
          <FileButton onChange={setFile} resetRef={resetRef}>
            {(props) => (
              <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
                {file ? "Change file" : "Pick a file"}
              </Button>
            )}
          </FileButton>
          {file ? <Text size="sm">{file.name} ({Math.round(file.size / 1024)} KB)</Text> : null}
        </Group>
        <Group justify="space-between" align="center">
          {feedback ? (
            <Text size="sm" c={feedback.kind === "ok" ? "green" : "red"}>
              {feedback.kind === "ok" ? <IconCheck size={14} style={{ verticalAlign: -2 }} /> : null}
              {" "}{feedback.msg}
            </Text>
          ) : <span />}
          <Button onClick={handleSubmit} loading={submitting} disabled={!file}>
            Upload
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}
