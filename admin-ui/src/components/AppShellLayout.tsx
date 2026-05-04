"use client";
import { useEffect, useState } from "react";
import { AppShell, Group, Text, NavLink, ScrollArea, Burger, Menu, ActionIcon, Loader, UnstyledButton } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  IconDashboard, IconSettings, IconShieldLock, IconFilter, IconAdjustments,
  IconClockPlay, IconList, IconLogout, IconUser, IconBriefcase, IconUsers,
  IconBuilding, IconTable, IconSearch, IconSparkles, IconHistory,
  IconWebhook,
} from "@tabler/icons-react";
import { useBranding } from "@/lib/branding";
import { api, type ModuleConfig } from "@/lib/api";
import { humanizeRegistrySlugForUi } from "@/lib/formatters";
import { getCachedUiConfig } from "@/lib/modelConfig";
import CommandPalette from "@/components/CommandPalette";
import PageBreadcrumbs from "@/components/PageBreadcrumbs";

const MODULE_ICONS: Record<string, React.ComponentType<{ size?: number | string; stroke?: number | string }>> = {
  crm:  IconUsers,
  hr:   IconBriefcase,
  base: IconBuilding,
};
const DEFAULT_ICON: React.ComponentType<{ size?: number | string; stroke?: number | string }> = IconTable;

// Modules hidden from main nav (internal/system)
const HIDDEN_MODULES = new Set(["auth", "base"]);

const TECHNICAL_NAV = [
  { label: "Models",          href: "/base/ir-model",            icon: IconSettings },
  { label: "Access",          href: "/base/ir-model-access",     icon: IconShieldLock },
  { label: "Rules",           href: "/base/ir-rule",             icon: IconFilter },
  { label: "Parameters",      href: "/base/ir-config-param",     icon: IconAdjustments },
  { label: "Sequences",       href: "/base/ir-sequence",         icon: IconList },
  { label: "Cron Jobs",       href: "/base/ir-cron",             icon: IconClockPlay },
  { label: "Log Activity",    href: "/technical/audit-log",      icon: IconHistory },
  { label: "Webhooks",        href: "/technical/webhooks",       icon: IconWebhook },
  { label: "AI Integration",  href: "/technical/ai-integration", icon: IconSparkles },
];

function modelHref(moduleName: string, modelName: string): string {
  const segment = modelName.startsWith(`${moduleName}.`)
    ? modelName.slice(moduleName.length + 1)
    : modelName;
  return `/${moduleName}/${segment}`;
}

function modelLabel(modelName: string): string {
  const last = modelName.split(".").pop() ?? modelName;
  return humanizeRegistrySlugForUi(last);
}

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const [opened, { toggle }] = useDisclosure();
  const path = usePathname();
  const branding = useBranding();

  const [modules, setModules] = useState<ModuleConfig[]>([]);
  const [navLoading, setNavLoading] = useState(true);

  // Auth gate is enforced server-side by `admin-ui/src/proxy.ts` (Next 16
  // Edge proxy) reading the httpOnly `orbiteus_token` cookie before any HTML
  // is generated. Here we only load module metadata for authenticated
  // routes.
  //
  // ui-config is fetched ONCE per session via `getCachedUiConfig` so the
  // module list survives client navigations and we don't spam the backend
  // with `/api/base/ui-config` on every route change. The previous
  // `[path]` dependency caused ~10 calls/second when interacting with the
  // app and intermittently emptied the sidebar mid-render.
  useEffect(() => {
    if (path === "/login" || path === "/welcome") {
      setNavLoading(false);
      return;
    }
    let cancelled = false;
    getCachedUiConfig()
      .then((cfg) => { if (!cancelled) setModules(cfg.modules); })
      .catch(() => { /* keep last-known modules */ })
      .finally(() => { if (!cancelled) setNavLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (path === "/login" || path === "/welcome") return <>{children}</>;

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* even if the server rejects, fall through and force redirect */
    }
    // Hard navigation so middleware sees the cleared cookie immediately.
    window.location.assign("/login");
  }

  // Show only non-system modules that have at least one model with views defined
  const dynamicSections = modules
    .filter((mod) => !HIDDEN_MODULES.has(mod.name))
    .map((mod) => ({ ...mod, models: mod.models.filter((m) => m.fields.length > 0) }))
    .filter((mod) => mod.models.length > 0);

  return (
    <AppShell
      header={{ height: 52 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
      styles={{
        navbar: {
          background: "var(--mantine-color-body)",
          borderRight: "1px solid var(--mantine-color-default-border)",
        },
        main: { background: "var(--mantine-color-body)" },
      }}
    >
      <AppShell.Header
        style={{
          background: "var(--mantine-color-body)",
          borderBottom: "1px solid var(--mantine-color-default-border)",
        }}
      >
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            {/* Same hydration-safe gate as the login page: only flip to
                the logo once the client effect has populated branding. */}
            {branding.hydrated && branding.logo_url
              ? <img src={branding.logo_url} alt={branding.name} style={{ height: 28 }} />
              : <Text fw={700} size="lg">{branding.name}</Text>
            }
          </Group>
          <Group gap="sm">
            {/* Cmd+K hint — clicking also opens palette */}
            <UnstyledButton
              onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }))}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "4px 10px",
                borderRadius: "var(--mantine-radius-sm)",
                background: "var(--mantine-color-default)",
                border: "1px solid var(--mantine-color-default-border)",
                cursor: "pointer",
              }}
            >
              <IconSearch size={13} stroke={1.5} color="var(--mantine-color-gray-6)" />
              <Text size="xs" c="dimmed">Search actions</Text>
              <Text size="xs" c="dimmed" style={{ fontFamily: "monospace", marginLeft: 4 }}>⌘K</Text>
            </UnstyledButton>

            <Menu position="bottom-end" withArrow>
              <Menu.Target>
                <ActionIcon variant="subtle" color="gray" size="lg">
                  <IconUser size={18} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconLogout size={14} />} color="red" onClick={logout}>
                  Log out
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <ScrollArea style={{ flex: 1 }}>
          <NavLink
            component={Link} href="/" label="Dashboard"
            leftSection={<IconDashboard size={16} stroke={1.5} />}
            active={path === "/"}
            variant="filled"
            styles={{ root: { borderRadius: "var(--mantine-radius-sm)" } }}
          />

          {navLoading ? (
            <Loader size="xs" color="gray" mt="sm" ml="sm" />
          ) : (
            dynamicSections.map((mod) => {
              const ModIcon = MODULE_ICONS[mod.name] ?? DEFAULT_ICON;
              return (
                <div key={mod.name}>
                  <Text size="xs" fw={700} tt="uppercase" c="dimmed" px="sm" pt="md" pb={4}
                    style={{ letterSpacing: "0.05em" }}>
                    {mod.label}
                  </Text>
                  {mod.models.map((model) => {
                    const href = modelHref(mod.name, model.name);
                    return (
                      <NavLink
                        key={model.name}
                        component={Link} href={href}
                        label={modelLabel(model.name)}
                        leftSection={<ModIcon size={16} stroke={1.5} />}
                        active={path.startsWith(href)}
                        variant="filled"
                        styles={{ root: { borderRadius: "var(--mantine-radius-sm)" } }}
                      />
                    );
                  })}
                </div>
              );
            })
          )}

          <Text size="xs" fw={700} tt="uppercase" c="dimmed" px="sm" pt="md" pb={4}
            style={{ letterSpacing: "0.05em" }}>
            Technical
          </Text>
          {TECHNICAL_NAV.map((item) => (
            <NavLink
              key={item.href}
              component={Link} href={item.href} label={item.label}
              leftSection={<item.icon size={16} stroke={1.5} />}
              active={path === item.href}
              variant="filled"
              styles={{ root: { borderRadius: "var(--mantine-radius-sm)" } }}
            />
          ))}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <PageBreadcrumbs />
        {children}
      </AppShell.Main>

      {/* Global Command Palette — Cmd+K */}
      {path !== "/login" && <CommandPalette />}
    </AppShell>
  );
}
