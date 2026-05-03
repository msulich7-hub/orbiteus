# ADR-0002: Mantine 8 as the only design system

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** frontend, design system

## Context

Senior teams want a complete, themeable component set with strong defaults,
TypeScript types, dark/light mode, and an active community. Multiple design
systems in one codebase is a maintenance nightmare.

## Decision

Mantine 8 is the **only** design system used by `admin-ui`, `portal-ui`, and
the shared `packages/ui` workspace. No shadcn/ui, MUI, Chakra, Ant Design, or
raw Tailwind is allowed without a superseding ADR.

## Consequences

- Senior devs can reuse Mantine knowledge across both apps.
- Theming and branding go through one provider.
- AI assistants see consistent component shapes; less hallucination.
- Custom widgets must integrate with Mantine theming tokens.

## Alternatives considered

- **shadcn/ui** — high quality but copy-paste model creates drift; rejected.
- **MUI** — heavier, less idiomatic with Next.js App Router; rejected.
- **Chakra UI** — fewer components than Mantine for our needs; rejected.
- **Tailwind raw** — no component library; would force us to re-invent forms,
  modals, tables; rejected.

## References

- `docs/10-design-system.md`
