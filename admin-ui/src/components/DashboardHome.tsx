"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconBriefcase,
  IconCash,
  IconFlame,
  IconInbox,
  IconLayoutKanban,
  IconCalendarEvent,
  IconTrendingUp,
  IconTrophy,
  IconUsers,
} from "@tabler/icons-react";
import { AIDashboard, PromptInput } from "@/orbiteus-ui";

import { api } from "@/lib/api";
import { formatMoney } from "@/lib/formatters";

interface CrmStats {
  total_persons: number;
  total_leads: number;
  won_leads: number;
  pipeline_value: number;
  won_revenue: number;
  open_prospects?: number;
  rotting_leads?: number;
}

export default function DashboardHome() {
  const [stats, setStats] = useState<CrmStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<CrmStats>("/crm/stats")
      .then(({ data }) => setStats(data))
      .catch(() => setError("Could not load CRM statistics."));
  }, []);

  if (error) {
    return (
      <Stack gap="md">
        <Title order={3}>Dashboard</Title>
        <Alert color="yellow" title="CRM stats unavailable">{error}</Alert>
        <Text c="dimmed" size="sm">Ensure you are logged in and the CRM module is loaded.</Text>
      </Stack>
    );
  }

  if (!stats) {
    return (
      <Stack gap="md" align="center" py="xl">
        <Loader color="gray" />
        <Text c="dimmed" size="sm">Loading dashboard…</Text>
      </Stack>
    );
  }

  const quickActions = [
    {
      label: "Pipeline Kanban",
      description: "Drag deals across stages",
      icon: IconLayoutKanban,
      color: "blue",
      href: "/crm/lead?view=kanban",
      badge: stats.total_leads > 0 ? String(stats.total_leads) : undefined,
    },
    {
      label: "Rotting deals",
      description: "Deals stuck too long in stage",
      icon: IconFlame,
      color: "orange",
      href: "/crm/lead?filter=rotting",
      badge: stats.rotting_leads != null ? String(stats.rotting_leads) : undefined,
    },
    {
      label: "Today's activities",
      description: "Tasks and calls due today",
      icon: IconCalendarEvent,
      color: "violet",
      href: "/crm/activity?filter=today",
    },
    {
      label: "Prospect inbox",
      description: "Unconverted pre-pipeline leads",
      icon: IconInbox,
      color: "cyan",
      href: "/crm/prospect?filter=inbox",
      badge: stats.open_prospects != null ? String(stats.open_prospects) : undefined,
    },
  ] as const;

  const cards = [
    {
      label: "Persons",
      value: String(stats.total_persons),
      icon: IconUsers,
      color: "blue",
      href: "/crm/person",
    },
    {
      label: "Open leads",
      value: String(stats.total_leads),
      icon: IconBriefcase,
      color: "cyan",
      href: "/crm/lead?view=kanban",
    },
    {
      label: "Won leads",
      value: String(stats.won_leads),
      icon: IconTrophy,
      color: "green",
      href: "/crm/lead",
    },
    {
      label: "Pipeline value",
      value: formatMoney(stats.pipeline_value),
      icon: IconTrendingUp,
      color: "grape",
      href: "/crm/lead?view=kanban",
    },
    {
      label: "Won revenue",
      value: formatMoney(stats.won_revenue),
      icon: IconCash,
      color: "teal",
      href: "/crm/lead",
    },
  ] as const;

  return (
    <Stack gap="lg">
      <div>
        <Title order={3}>Dashboard</Title>
        <Text c="dimmed" size="sm" mt={4}>
          Overview of your CRM — data from{" "}
          <Text span ff="monospace" size="xs">GET /api/crm/stats</Text>
        </Text>
      </div>

      <Stack gap="xs">
        <Text size="sm" fw={600}>Quick actions</Text>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          {quickActions.map((action) => (
            <Paper
              key={action.label}
              component={Link}
              href={action.href}
              p="md"
              radius="md"
              withBorder
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Stack gap={4} style={{ minWidth: 0 }}>
                  <Text size="sm" fw={700}>
                    {action.label}
                  </Text>
                  <Text size="xs" c="dimmed" lineClamp={2}>
                    {action.description}
                  </Text>
                  {action.badge != null && (
                    <Text size="lg" fw={700} mt={4}>
                      {action.badge}
                    </Text>
                  )}
                </Stack>
                <ThemeIcon size={40} radius="md" variant="light" color={action.color}>
                  <action.icon size={22} stroke={1.5} />
                </ThemeIcon>
              </Group>
            </Paper>
          ))}
        </SimpleGrid>
      </Stack>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
        {cards.map((c) => (
          <Paper
            key={c.label}
            component={Link}
            href={c.href}
            p="md"
            radius="md"
            withBorder
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <div>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.05em" }}>
                  {c.label}
                </Text>
                <Text size="xl" fw={700} mt={4}>
                  {c.value}
                </Text>
              </div>
              <ThemeIcon size={44} radius="md" variant="light" color={c.color}>
                <c.icon size={24} stroke={1.5} />
              </ThemeIcon>
            </Group>
          </Paper>
        ))}
      </SimpleGrid>

      <Paper p="md" withBorder radius="md">
        <Text size="sm" fw={600} mb="xs">AI assistant</Text>
        <PromptInput scope="module:crm" placeholder="Ask about your CRM…" />
      </Paper>

      <AIDashboard scope="module:crm" initialPrompt="Pipeline value by stage this quarter" />

      <Paper p="md" withBorder radius="md">
        <Text size="sm" fw={600} mb="xs">Quick links</Text>
        <Group gap="sm">
          <Button component={Link} href="/crm/team" variant="default" size="xs">Sales teams</Button>
          <Button component={Link} href="/crm/stage" variant="default" size="xs">Stages</Button>
          <Button component={Link} href="/base/company" variant="default" size="xs">Companies</Button>
          <Button component={Link} href="/base/user" variant="default" size="xs">Users</Button>
        </Group>
      </Paper>
    </Stack>
  );
}
