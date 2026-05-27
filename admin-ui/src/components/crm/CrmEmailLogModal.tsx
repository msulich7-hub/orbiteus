"use client";

import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";

export interface CrmEmailLogModalProps {
  opened: boolean;
  onClose: () => void;
  leadId: string;
  onLogged: () => void;
}

export default function CrmEmailLogModal({
  opened,
  onClose,
  leadId,
  onLogged,
}: CrmEmailLogModalProps) {
  const [direction, setDirection] = useState<string>("outbound");
  const [fromAddress, setFromAddress] = useState("");
  const [toAddress, setToAddress] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);

  function resetForm() {
    setDirection("outbound");
    setFromAddress("");
    setToAddress("");
    setSubject("");
    setBody("");
  }

  async function handleSubmit() {
    if (!fromAddress.trim() || !toAddress.trim()) return;
    setSaving(true);
    try {
      await api.post(`/crm/lead/${leadId}/email`, {
        direction,
        from_address: fromAddress.trim(),
        to_address: toAddress.trim(),
        subject: subject.trim(),
        body: body.trim(),
      });
      notifications.show({
        title: "Email logged",
        message: "The email was saved on this deal.",
        color: "green",
      });
      resetForm();
      onLogged();
      onClose();
    } catch (e: unknown) {
      notifications.show({
        title: "Could not log email",
        message: (e as { message?: string }).message ?? "Request failed",
        color: "red",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (!saving) onClose();
      }}
      title="Log email"
      size="md"
      styles={{
        content: { background: "var(--mantine-color-body)" },
        header: { background: "var(--mantine-color-body)" },
      }}
    >
      <Stack gap="sm">
        <SegmentedControl
          value={direction}
          onChange={setDirection}
          data={[
            { label: "Inbound", value: "inbound" },
            { label: "Outbound", value: "outbound" },
          ]}
          fullWidth
        />
        <TextInput
          label="From"
          value={fromAddress}
          onChange={(e) => setFromAddress(e.currentTarget.value)}
          placeholder="you@company.com"
        />
        <TextInput
          label="To"
          value={toAddress}
          onChange={(e) => setToAddress(e.currentTarget.value)}
          placeholder="client@company.com"
        />
        <TextInput
          label="Subject"
          value={subject}
          onChange={(e) => setSubject(e.currentTarget.value)}
          placeholder="Email subject"
        />
        <Textarea
          label="Body"
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
          placeholder="Message body"
          minRows={4}
          autosize
        />
        <Group justify="flex-end" mt="xs">
          <Button variant="subtle" color="gray" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            loading={saving}
            disabled={!fromAddress.trim() || !toAddress.trim()}
          >
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
