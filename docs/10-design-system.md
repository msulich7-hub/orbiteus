# 10 — Design System

## One DS, two front-ends

- **Mantine 9** is the only design system. ADR-0002 floats with major
  Mantine versions; the *decision* (Mantine as the sole DS) is what's
  locked, not the version number.
- Shared widgets and AI components live in `packages/ui`, an npm workspace
  consumed by both `admin-ui` and `portal-ui`.
- No second DS. Adding one requires an ADR (and a strong reason — ADR `0002`
  documents the existing decision).

## Workspace layout

```
package.json                 (workspaces: ["admin-ui", "portal-ui", "packages/*"])
admin-ui/                    (Next.js 16 + React 19)
portal-ui/                   (Next.js 16 + React 19)
packages/
  ui/                        (@orbiteus/ui)
    src/
      widgets/               (text, email, badge, monetary, statusbar, many2one, tags)
      ai/                    (PromptInput, AIChatPanel, AIDashboard, useAIContext)
      branding/              (BrandingProvider, useBranding)
      hooks/                 (useResource, useStream, usePresence)
      index.ts
```

Both apps import:

```ts
import { PromptInput, AIDashboard } from "@orbiteus/ui";
```

## Tokens and theme

- Mantine theme defined once in `packages/ui/src/theme.ts`.
- Both apps wrap their root with the same `<MantineProvider theme={theme}>`.
- `primaryColor`, font stack, default radius, default gradient — all live there.

## Branding

- `useBranding()` reads `/api/base/branding` per tenant.
- Returns `{ name, logo_url, favicon_url }`.
- Components prefer `<Branding>` markers over hardcoded names.
- Product name is **never** hardcoded in tracked content (see `AGENTS.md`).

## Dark / light mode

- Both apps use Mantine's `ColorSchemeScript` for hydration-safe SSR.
- Default: light. User toggle persists in `localStorage`.

## Accessibility

- Color contrast: WCAG AA minimum on text and primary buttons.
- All interactive widgets must have keyboard equivalents.
- Mantine inputs already meet ARIA basics; custom widgets must too.

## What you ship vs reuse

- **Reuse from Mantine** whenever it covers the case (TextInput, Select,
  Modal, Drawer, Tabs, Button, Badge, ActionIcon, Notifications, Calendar).
- **Build in `packages/ui`** when you need engine semantics (badge color
  rules, monetary format with locale, statusbar transitions, RBAC-aware
  many2one resolver, AI prompt widgets).
- **Never build in `admin-ui/src/components/`** if `portal-ui` could ever need
  the same component.
