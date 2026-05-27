"use client";

import { useEffect, useState } from "react";
import { Badge, Group, Loader, Stack, Text, Timeline } from "@mantine/core";
import { IconArrowRight, IconPhone, IconMail, IconCalendar, IconChecklist } from "@tabler/icons-react";
import { api } from "@/lib/api";

interface TimelineItem {
  type: "stage_change" | "activity";
  timestamp: string | null;
  id: string;
  subject?: string;
  activity_type?: string;
  done?: boolean;
  from_stage_id?: string | null;
  to_stage_id?: string;
}

interface Props {
  leadId: string;
}

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  call: <IconPhone size={12} />,
  meeting: <IconCalendar size={12} />,
  email: <IconMail size={12} />,
  task: <IconChecklist size={12} />,
};

export default function CrmDealTimeline({ leadId }: Props) {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get<{ timeline: TimelineItem[] }>(`/crm/lead/${leadId}/timeline`)
      .then(({ data }) => {
        if (!cancelled) setItems(data.timeline ?? []);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [leadId]);

  if (loading) {
    return <Loader size="sm" color="gray" />;
  }

  if (items.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        No timeline events yet.
      </Text>
    );
  }

  return (
    <Stack gap="xs">
      <Text size="sm" fw={600}>
        Timeline
      </Text>
      <Timeline active={-1} bulletSize={22} lineWidth={2}>
        {items.map((item) => {
          if (item.type === "stage_change") {
            return (
              <Timeline.Item
                key={`sh-${item.id}`}
                bullet={<IconArrowRight size={12} />}
                title="Stage changed"
              >
                <Text size="xs" c="dimmed">
                  {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                </Text>
              </Timeline.Item>
            );
          }

          const icon = ACTIVITY_ICONS[item.activity_type ?? "task"] ?? ACTIVITY_ICONS.task;
          return (
            <Timeline.Item
              key={`act-${item.id}`}
              bullet={icon}
              title={item.subject ?? "Activity"}
            >
              <Group gap={6}>
                <Badge size="xs" variant="light">
                  {item.activity_type ?? "task"}
                </Badge>
                {item.done && (
                  <Badge size="xs" color="green" variant="light">
                    done
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed">
                {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
              </Text>
            </Timeline.Item>
          );
        })}
      </Timeline>
    </Stack>
  );
}
