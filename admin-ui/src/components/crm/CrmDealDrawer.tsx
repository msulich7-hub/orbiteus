"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Badge,
  Button,
  Drawer,
  Group,
  Select,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconExternalLink, IconPlus } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";
import LeadStageHistory from "@/components/crm/LeadStageHistory";
import CrmDealTimeline from "@/components/crm/CrmDealTimeline";
import CrmEmailLogModal from "@/components/crm/CrmEmailLogModal";

export interface DealDrawerPreview {
  id: string;
  name: string;
  expected_revenue?: number;
  organization_name?: string | null;
  person_name?: string | null;
  stage_name?: string | null;
}

interface LeadDetail {
  id: string;
  name: string;
  expected_revenue: number;
  probability?: number;
  organization_id?: string | null;
  person_id?: string | null;
  organization_id__name?: string | null;
  person_id__name?: string | null;
  stage_id?: string | null;
  stage_id__name?: string | null;
}

interface EmailLogItem {
  id: string;
  subject: string;
  direction: string;
  sent_at: string | null;
}

interface Props {
  opened: boolean;
  onClose: () => void;
  leadId: string | null;
  preview?: DealDrawerPreview | null;
}

const ACTIVITY_TYPES = [
  { value: "task", label: "Task" },
  { value: "call", label: "Call" },
  { value: "meeting", label: "Meeting" },
  { value: "email", label: "Email" },
];

export default function CrmDealDrawer({ opened, onClose, leadId, preview }: Props) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activitySubject, setActivitySubject] = useState("");
  const [activityType, setActivityType] = useState("task");
  const [loggingActivity, setLoggingActivity] = useState(false);
  const [emails, setEmails] = useState<EmailLogItem[]>([]);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailModalOpen, setEmailModalOpen] = useState(false);

  const loadEmails = useCallback(async (id: string) => {
    setEmailsLoading(true);
    try {
      const { data } = await api.get<{ emails?: EmailLogItem[] }>(`/crm/lead/${id}/emails`);
      setEmails((data.emails ?? []).slice(0, 5));
    } catch {
      setEmails([]);
    } finally {
      setEmailsLoading(false);
    }
  }, []);

  const loadLead = useCallback(async (id: string) => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<LeadDetail>(`/crm/lead/${id}`, {
        params: { expand: "organization_id,person_id,stage_id" },
      });
      setLead(data);
    } catch (e: unknown) {
      setLead(null);
      setError((e as { message?: string }).message ?? "Failed to load deal");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!opened || !leadId) {
      setLead(null);
      setError("");
      setActivitySubject("");
      setActivityType("task");
      setEmails([]);
      setEmailModalOpen(false);
      return;
    }
    loadLead(leadId);
    loadEmails(leadId);
  }, [opened, leadId, loadLead, loadEmails]);

  async function handleLogActivity() {
    if (!leadId || !activitySubject.trim()) return;
    setLoggingActivity(true);
    try {
      await api.post("/crm/activity", {
        subject: activitySubject.trim(),
        activity_type: activityType,
        res_model: "crm.lead",
        res_id: leadId,
      });
      notifications.show({
        title: "Activity logged",
        message: "Follow-up added to this deal.",
        color: "green",
      });
      setActivitySubject("");
      await loadLead(leadId);
    } catch (e: unknown) {
      notifications.show({
        title: "Could not log activity",
        message: (e as { message?: string }).message ?? "Request failed",
        color: "red",
      });
    } finally {
      setLoggingActivity(false);
    }
  }

  const displayName = lead?.name ?? preview?.name ?? "Deal";
  const displayRevenue = lead?.expected_revenue ?? preview?.expected_revenue ?? 0;
  const orgName =
    lead?.organization_id__name ?? preview?.organization_name ?? null;
  const personName = lead?.person_id__name ?? preview?.person_name ?? null;
  const stageName = lead?.stage_id__name ?? preview?.stage_name ?? null;

  function formatEmailDate(value: string | null) {
    if (!value) return "";
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
  }

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={<Title order={4}>Deal details</Title>}
      position="right"
      size="md"
      data-testid="crm-deal-drawer"
      overlayProps={{ backgroundOpacity: 0.35, blur: 2 }}
      styles={{
        content: { background: "var(--mantine-color-body)" },
        header: {
          background: "var(--mantine-color-body)",
          borderBottom: "1px solid var(--mantine-color-default-border)",
        },
      }}
    >
      <Stack gap="md">
        {loading && !lead && !preview ? (
          <Stack gap="sm">
            <Skeleton height={28} radius="sm" />
            <Skeleton height={18} radius="sm" />
            <Skeleton height={120} radius="sm" />
          </Stack>
        ) : (
          <>
            {error && (
              <Alert icon={<IconAlertCircle size={16} />} color="red">
                {error}
              </Alert>
            )}

            <Stack gap={6}>
              <Text fw={700} size="lg" lineClamp={2}>
                {displayName}
              </Text>
              <Group gap="xs">
                {stageName && (
                  <Badge variant="light" color="blue">
                    {stageName}
                  </Badge>
                )}
                <Text size="sm" fw={600}>
                  {formatMoney(displayRevenue)}
                </Text>
              </Group>
              {(orgName || personName) && (
                <Stack gap={2}>
                  {orgName && (
                    <Text size="sm" c="dimmed">
                      Organization: {orgName}
                    </Text>
                  )}
                  {personName && (
                    <Text size="sm" c="dimmed">
                      Contact: {personName}
                    </Text>
                  )}
                </Stack>
              )}
            </Stack>

            <Group justify="flex-end">
              {leadId && (
                <Button
                  component={Link}
                  href={`/crm/lead/${leadId}`}
                  variant="light"
                  size="xs"
                  rightSection={<IconExternalLink size={14} />}
                >
                  Open full record
                </Button>
              )}
            </Group>

            {leadId && <LeadStageHistory leadId={leadId} />}

            {leadId && <CrmDealTimeline leadId={leadId} />}

            {leadId && (
              <Stack gap="xs">
                <Group justify="space-between" align="center">
                  <Text size="sm" fw={600}>
                    Emails
                  </Text>
                  <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconPlus size={14} />}
                    onClick={() => setEmailModalOpen(true)}
                  >
                    Log email
                  </Button>
                </Group>
                {emailsLoading ? (
                  <Skeleton height={48} radius="sm" />
                ) : emails.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    No emails logged yet.
                  </Text>
                ) : (
                  <Stack gap={6}>
                    {emails.map((email) => (
                      <Group key={email.id} justify="space-between" wrap="nowrap" gap="xs">
                        <Text size="sm" lineClamp={1} style={{ flex: 1 }}>
                          {email.subject || "(no subject)"}
                        </Text>
                        <Group gap={6} wrap="nowrap">
                          <Badge
                            size="xs"
                            variant="light"
                            color={email.direction === "inbound" ? "teal" : "blue"}
                          >
                            {email.direction}
                          </Badge>
                          <Text size="xs" c="dimmed">
                            {formatEmailDate(email.sent_at)}
                          </Text>
                        </Group>
                      </Group>
                    ))}
                  </Stack>
                )}
              </Stack>
            )}

            <Stack gap="xs">
              <Text size="sm" fw={600}>
                Log activity
              </Text>
              <TextInput
                placeholder="Follow-up subject…"
                value={activitySubject}
                onChange={(e) => setActivitySubject(e.currentTarget.value)}
                size="sm"
              />
              <Group align="flex-end" wrap="nowrap">
                <Select
                  label="Type"
                  data={ACTIVITY_TYPES}
                  value={activityType}
                  onChange={(v) => setActivityType(v ?? "task")}
                  size="sm"
                  style={{ flex: 1 }}
                />
                <Button
                  leftSection={<IconPlus size={16} />}
                  onClick={handleLogActivity}
                  loading={loggingActivity}
                  disabled={!activitySubject.trim()}
                  size="sm"
                >
                  Log
                </Button>
              </Group>
            </Stack>
          </>
        )}
      </Stack>

      {leadId && (
        <CrmEmailLogModal
          opened={emailModalOpen}
          onClose={() => setEmailModalOpen(false)}
          leadId={leadId}
          onLogged={() => loadEmails(leadId)}
        />
      )}
    </Drawer>
  );
}
