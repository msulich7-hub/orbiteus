# 10 — Design System

## One DS, two front-ends

- **Mantine 9** is the only design system. ADR-0002 floats with major
  Mantine versions; the *decision* (Mantine as the sole DS) is what's
  locked, not the version number.
- Cross-cutting widgets and AI surfaces live in **`admin-ui/src/orbiteus-ui/`**
  (`widgets/` + `ai/`). `portal-ui` is a separate Next app; copy components
  from there when the portal needs the same UX (no shared npm package).
- No second DS. Adding one requires an ADR (and a strong reason — ADR `0002`
  documents the existing decision).

## Workspace layout

```
package.json                 (workspaces: ["admin-ui", "portal-ui"])
admin-ui/                    (Next.js 16 + React 19)
  src/orbiteus-ui/           (Badge, Monetary, Statusbar, Many2OneSelect, TagsField,
                              PromptInput, AIChatPanel, AIDashboard, useAIContext)
portal-ui/                   (Next.js 16 + React 19)
```

Imports in admin-ui:

```ts
import { PromptInput, AIDashboard } from "@/orbiteus-ui";
```

## Tokens and theme

- Mantine theme is defined in `admin-ui/src/app/layout.tsx` (and can be
  extracted to a small `theme.ts` next to it when it grows).
- Root layout wraps `<MantineProvider theme={theme}>`.
- `primaryColor`, font stack, default radius, default gradient — live there.

## Branding

- `useBranding()` in `admin-ui/src/lib/branding.tsx` reads `/api/base/branding` per tenant.
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
- **Build in `admin-ui/src/orbiteus-ui/`** when you need engine semantics (badge color
  rules, monetary format with locale, statusbar transitions, RBAC-aware
  many2one resolver, AI prompt widgets).
- **Never build in `admin-ui/src/components/`** if `portal-ui` could ever need
  the same component — put it under `orbiteus-ui/` first (then copy to portal
  when that app adopts it).
