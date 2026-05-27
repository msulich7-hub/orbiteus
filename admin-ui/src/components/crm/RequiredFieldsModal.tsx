"use client";

import { Button, Group, Modal, Stack, Text } from "@mantine/core";

const FIELD_LABELS: Record<string, string> = {
  expected_close_date: "Expected close date",
  expected_revenue: "Expected revenue",
  lost_reason: "Lost reason",
  description: "Description",
};

export function fieldLabel(name: string): string {
  return FIELD_LABELS[name] ?? name.replace(/_/g, " ");
}

export interface RequiredFieldsModalProps {
  opened: boolean;
  dealName: string;
  fromStageName?: string;
  missingFields: string[];
  loading?: boolean;
  onClose: () => void;
  onEditDeal?: () => void;
}

export default function RequiredFieldsModal({
  opened,
  dealName,
  fromStageName,
  missingFields,
  loading = false,
  onClose,
  onEditDeal,
}: RequiredFieldsModalProps) {
  const labels = missingFields.map(fieldLabel);

  return (
    <Modal
      opened={opened}
      onClose={() => {
        if (!loading) onClose();
      }}
      title="Complete required fields"
      size="sm"
      styles={{
        content: { background: "var(--mantine-color-body)" },
        header: { background: "var(--mantine-color-body)" },
      }}
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Moving{" "}
          <Text span fw={600}>
            {dealName}
          </Text>
          {fromStageName ? (
            <>
              {" "}
              out of{" "}
              <Text span fw={600}>
                {fromStageName}
              </Text>
            </>
          ) : null}{" "}
          requires:
        </Text>
        <Stack gap={4}>
          {labels.map((label) => (
            <Text key={label} size="sm">
              • {label}
            </Text>
          ))}
        </Stack>
        <Group justify="flex-end">
          <Button variant="subtle" color="gray" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          {onEditDeal ? (
            <Button onClick={onEditDeal} disabled={loading}>
              Edit deal
            </Button>
          ) : null}
        </Group>
      </Stack>
    </Modal>
  );
}

export interface MissingFieldsDetail {
  code: "missing_required_fields";
  message: string;
  missing_fields: string[];
  from_stage_name?: string;
}

export function parseMissingFieldsError(err: unknown): MissingFieldsDetail | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail;
  if (!detail || typeof detail !== "object") return null;
  const d = detail as Record<string, unknown>;
  if (d.code !== "missing_required_fields" || !Array.isArray(d.missing_fields)) {
    return null;
  }
  return {
    code: "missing_required_fields",
    message: String(d.message ?? "Missing required fields"),
    missing_fields: d.missing_fields.map(String),
    from_stage_name: d.from_stage_name ? String(d.from_stage_name) : undefined,
  };
}
