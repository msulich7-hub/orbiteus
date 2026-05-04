"use client";
/**
 * Public welcome / marketing page (DoD §9.9).
 *
 * Lives at `/welcome` so the sign-in form on `/login` stays single-purpose.
 * The page is whitelisted in `proxy.ts` (`PUBLIC_PATHS`) — visitors can
 * land here without a session cookie.
 *
 * Vendor-neutral (per `AGENTS.md`): names only Orbiteus and the public
 * stack. No outbound links to third-party ERP demos, no competitor
 * trademarks. The headline + subheadline mirror the README.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Code,
  Container,
  Flex,
  Group,
  List,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconApi,
  IconArrowRight,
  IconBook,
  IconBrandGithub,
  IconCircleCheck,
  IconDatabase,
  IconShieldLock,
  IconSparkles,
  IconUsers,
} from "@tabler/icons-react";
import { useBranding } from "@/lib/branding";

const fluidPx = { base: "md", sm: "xl", lg: "3rem", xl: "4rem" } as const;

const ROLE_CARDS: {
  title: string;
  blurb: string;
  features: string[];
  icon: typeof IconShieldLock;
}[] = [
  {
    title: "Super administrator",
    blurb:
      "Bootstrap account with full technical access — RBAC, system parameters, and module configuration.",
    features: [
      "Manage users, roles, and record rules",
      "Technical models, cron jobs, sequences",
      "Branding and instance-wide settings",
    ],
    icon: IconShieldLock,
  },
  {
    title: "Operations workspace",
    blurb:
      "Day-to-day work — list / form / kanban / calendar / graph views over the registered modules in the same tenant.",
    features: [
      "Auto-generated CRUD per model",
      "List + Kanban + Calendar + Graph perspectives",
      "Fuzzy search and Command Palette (⌘K)",
    ],
    icon: IconUsers,
  },
  {
    title: "Headless engine",
    blurb:
      "Treat Orbiteus as a headless engine — OpenAPI-first, module registry, no vendor UI lock-in.",
    features: [
      "Auto-generated REST + OpenAPI per model",
      "Extend with registry.register(\"your_module\")",
      "PostgreSQL + Alembic migrations at startup",
    ],
    icon: IconApi,
  },
];

type HealthJson = { status?: string; service?: string };

export default function WelcomePage() {
  const branding = useBranding();
  const [health, setHealth] = useState<HealthJson | null>(null);
  const [healthErr, setHealthErr] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/api/base/health");
        if (!r.ok) throw new Error("bad");
        const j = (await r.json()) as HealthJson;
        if (!cancelled) setHealth(j);
      } catch {
        if (!cancelled) setHealthErr(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box bg="gray.0" mih="100vh" w="100%" pb="xl">
      <Container fluid px={fluidPx} pt="md" pb="xl" w="100%" mx={0}>
        <Stack gap="xl" w="100%" align="flex-start">
          <Box
            component="header"
            w="100%"
            pb="md"
            style={{
              borderBottom: "1px solid var(--mantine-color-default-border)",
            }}
          >
            <Flex direction="column" align="flex-start" gap="xs" w="100%" wrap="nowrap">
              <Group gap="sm" justify="flex-start" align="center" wrap="nowrap" w="100%">
                {branding.hydrated && branding.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={branding.logo_url}
                    alt={branding.name}
                    style={{ height: 44, width: "auto", display: "block" }}
                  />
                ) : (
                  <Title order={2} c="dark.9" style={{ lineHeight: 1.2 }}>
                    {branding.name}
                  </Title>
                )}
              </Group>
              <Text
                size="sm"
                c="dimmed"
                ta="left"
                maw={{ base: "100%", md: "42rem", lg: "50rem" }}
                lh={1.55}
              >
                Development engine for AI agents that build custom ERP / CRM apps.
                Open-source, MIT, FastAPI + Next.js, PostgreSQL + pgvector.
              </Text>
            </Flex>
          </Box>

          <Stack gap="md" align="flex-start" w="100%">
            <Title
              order={1}
              ta="left"
              fz={{ base: 26, sm: 34 }}
              fw={700}
              w="100%"
            >
              Welcome to your Orbiteus installation
            </Title>
            <Text
              c="dimmed"
              ta="left"
              lh={1.65}
              w="100%"
              maw={{ base: "100%", md: "48rem", lg: "56rem" }}
              size="md"
            >
              This is the public entry of your demo instance — the same Next.js +
              FastAPI codebase as in the repository, with live PostgreSQL,
              auto-generated CRUD, registry-driven modules, Command Palette
              (⌘K) and OpenAPI per model. A modular onboarding layout for
              Orbiteus.
            </Text>
            <Group>
              <Button
                component={Link}
                href="/login"
                rightSection={<IconArrowRight size={18} />}
                color="dark"
                size="md"
              >
                Sign in
              </Button>
              <Button
                component="a"
                href="https://github.com/orbiteus/orbiteus"
                target="_blank"
                rel="noreferrer"
                variant="default"
                leftSection={<IconBrandGithub size={18} />}
              >
                README on GitHub
              </Button>
            </Group>
          </Stack>

          <Box w="100%">
            <Title order={3} mb="md">
              What ships out of the box
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md" w="100%">
              {ROLE_CARDS.map((card) => {
                const RoleIcon = card.icon;
                return (
                  <Card
                    key={card.title}
                    withBorder
                    padding="lg"
                    radius="md"
                    h="100%"
                  >
                    <Stack gap="sm" h="100%">
                      <ThemeIcon
                        variant="outline"
                        color="dark"
                        size="lg"
                        radius="md"
                      >
                        <RoleIcon size={22} stroke={1.5} />
                      </ThemeIcon>
                      <Title order={4}>{card.title}</Title>
                      <Text size="sm" c="dimmed">
                        {card.blurb}
                      </Text>
                      <List
                        spacing={4}
                        size="sm"
                        icon={
                          <ThemeIcon variant="white" color="dark" size={16}>
                            <IconCircleCheck size={14} />
                          </ThemeIcon>
                        }
                      >
                        {card.features.map((f) => (
                          <List.Item key={f}>{f}</List.Item>
                        ))}
                      </List>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          </Box>

          <Box w="100%">
            <Group gap="sm" align="center" mb="xs">
              <ThemeIcon variant="light" color="dark" radius="xl" size="md">
                <IconDatabase size={16} />
              </ThemeIcon>
              <Title order={4}>Reference stack</Title>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <Stack gap={2}>
                <Text size="xs" tt="uppercase" fw={700} c="dimmed">
                  Backend
                </Text>
                <Code block>FastAPI · SQLAlchemy · PostgreSQL · pgvector · Redis · Celery</Code>
              </Stack>
              <Stack gap={2}>
                <Text size="xs" tt="uppercase" fw={700} c="dimmed">
                  Frontend
                </Text>
                <Code block>Next.js (App Router) · Mantine · TanStack Query</Code>
              </Stack>
            </SimpleGrid>
          </Box>

          <Box w="100%">
            <Group gap="sm" mb="xs">
              <ThemeIcon variant="light" color="dark" radius="xl" size="md">
                <IconSparkles size={16} />
              </ThemeIcon>
              <Title order={4}>Live status</Title>
            </Group>
            <Group gap="xs">
              <Badge
                color={healthErr ? "red" : "green"}
                variant="light"
                size="lg"
              >
                {healthErr
                  ? "Backend unreachable"
                  : health?.status
                    ? `Backend: ${health.status}`
                    : "Pinging backend…"}
              </Badge>
              <Anchor href="/api/base/health" target="_blank" rel="noreferrer" size="sm">
                /api/base/health
              </Anchor>
              <Anchor href="/api/docs" target="_blank" rel="noreferrer" size="sm">
                <IconBook size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                OpenAPI docs
              </Anchor>
            </Group>
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}
