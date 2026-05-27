"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Badge,
  Button,
  Group,
  Paper,
  Skeleton,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/lib/api";
import { formatListDate } from "@/lib/formatters";
import EmptyState from "@/components/EmptyState";

interface TodayActivity {
  id: string;
  subject: string;
  activity_type: string;
  due_date: string | null;
  res_model: string;
  res_id: string | null;
}

interface TodayResponse {
  count: number;
  activities: TodayActivity[];
}

function activityTypeColor(type: string): string {
  switch (type.toLowerCase()) {
    case "call":
      return "blue";
    case "meeting":
      return "violet";
    case "email":
      return "cyan";
    case "task":
      return "gray";
    default:
      return "gray";
  }
}

function relatedHref(activity: TodayActivity): string | null {
  if (!activity.res_model || !activity.res_id) return null;
  const parts = activity.res_model.split(".");
  if (parts.length !== 2) return null;
  return `/${parts[0]}/${parts[1]}/${activity.res_id}`;
}

export default function CrmTodayActivities() {
  const [activities, setActivities] = useState<TodayActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completingId, setCompletingId] = useState<string | null>(null);

  const loadActivities = useCallback(async () => {
    const { data } = await api.get<TodayResponse>("/crm/activities/today");
    setActivities(data.activities ?? []);
    return data;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      setError("");
      try {
        await loadActivities();
      } catch (e: unknown) {
        if (!cancelled) {
          setError((e as { message?: string }).message ?? "Failed to load activities");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [loadActivities]);

  async function markDone(activityId: string) {
    setCompletingId(activityId);
    try {
      await api.post(
        `/crm/activity/${activityId}/done`,
        {},
        { skipGlobalErrorToast: true },
      );
      setActivities((prev) => prev.filter((a) => a.id !== activityId));
      notifications.show({
        title: "Done",
        message: "Activity marked complete.",
        color: "green",
      });
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      notifications.show({
        title: "Could not complete",
        message: err.response?.data?.detail ?? err.message ?? "Request failed",
        color: "red",
      });
    } finally {
      setCompletingId(null);
    }
  }

  if (loading) {
    return (
      <Stack gap="sm">
        <Skeleton height={40} radius="sm" />
        <Skeleton height={120} radius="sm" />
        <Skeleton height={120} radius="sm" />
      </Stack>
    );
  }

  if (error) {
    return <Alert icon={<IconAlertCircle size={16} />} color="red">{error}</Alert>;
  }

  if (activities.length === 0) {
    return (
      <EmptyState
        title="Nothing due today"
        description="You're all caught up — no open activities due today or overdue."
      />
    );
  }

  return (
    <Paper withBorder radius="sm" style={{ overflow: "hidden" }} data-testid="crm-today-activities">
      <Table striped highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Subject</Table.Th>
            <Table.Th>Type</Table.Th>
            <Table.Th>Due</Table.Th>
            <Table.Th>Related</Table.Th>
            <Table.Th w={100} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {activities.map((activity) => {
            const href = relatedHref(activity);
            return (
              <Table.Tr key={activity.id}>
                <Table.Td>
                  <Text size="sm" fw={500} lineClamp={2}>
                    {activity.subject || "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge size="sm" variant="light" color={activityTypeColor(activity.activity_type)}>
                    {activity.activity_type || "—"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">
                    {formatListDate(activity.due_date)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {href ? (
                    <Text
                      component={Link}
                      href={href}
                      size="sm"
                      c="inherit"
                      style={{ textDecoration: "none" }}
                    >
                      {activity.res_model}
                    </Text>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {activity.res_model || "—"}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="light"
                    color="green"
                    leftSection={<IconCheck size={14} />}
                    loading={completingId === activity.id}
                    onClick={() => markDone(activity.id)}
                  >
                    Done
                  </Button>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Paper>
  );
}
