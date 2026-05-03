# ADR-0016: npm workspaces with `packages/ui`

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** frontend, monorepo

## Context

`admin-ui` and `portal-ui` need to share widgets, AI components, and branding
helpers. Publishing a separate npm package (`@orbiteus/ui`) is overkill at
this stage and slows iteration.

## Decision

Use **npm workspaces** with a `packages/ui` workspace. Apps consume it as
`"@orbiteus/ui": "*"` in their `package.json`. No external publishing for now.

Optional Turborepo / Nx caching can be layered later; not required.

## Consequences

- Single `npm install` at the repo root.
- Refactors across packages happen in one PR.
- Faster builds, fewer version drifts.
- Slight risk of dependency hoisting mismatches; mitigated by `nohoist` if
  needed.

## Alternatives considered

- Separate published package — more friction, slower iteration; rejected.
- pnpm workspaces — strictly better in some ways but adds a new tool; npm
  workspaces are universal in 2026; revisit if performance matters.

## References

- `docs/10-design-system.md`
- `docs/16-ai-recipes.md`
