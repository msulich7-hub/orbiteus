# 08 — Admin UI

## Stack

- Next.js 14 App Router
- React 18
- Mantine 8 (only design system; no shadcn / MUI / Chakra / Ant)
- `@orbiteus/ui` (workspace package: shared widgets, hooks, AI inputs)
- axios, dayjs, recharts, @dnd-kit, @tabler/icons-react

## Routes

| Path | Public? | Purpose |
|---|---|---|
| `/welcome` | yes | Landing page with hub of resources |
| `/login` | yes | Sign-in form (email/password + optional 2FA) |
| `/` | no | Authenticated dashboard |
| `/[module]/[model]` | no | Auto-rendered list / kanban |
| `/[module]/[model]/new` | no | Auto-rendered create form |
| `/[module]/[model]/[id]` | no | Auto-rendered edit form |

`/welcome` and `/login` are separate routes. **Never merge them.**

## Dynamic rendering

The admin UI is a renderer. Adding a new module **must not** require new TSX.

1. Frontend fetches `GET /api/base/ui-config` once on app boot.
2. The catch-all routes `[module]/[model]/*` look up the model in ui-config.
3. The list / form / kanban / calendar arch (`<list>`, `<form>`, `<kanban>`,
   `<calendar>` XML) controls layout.
4. If no XML arch is registered, fields are auto-generated from Pydantic
   schema metadata.

If you find yourself creating `admin-ui/src/app/<module>/...`, **stop** and
either:
- Add an XML view in the module's `view/`, or
- Register a new widget for the missing rendering case.

## Widget registry

Forms and lists render through widgets keyed by `widget` attribute or field type:

| Widget | Field type / attribute |
|---|---|
| `text` | `str` |
| `email` | name === "email" |
| `tel` | name in {"phone", "mobile"} |
| `number` | `int` / `float` |
| `textarea` | `widget="textarea"` |
| `boolean` | `bool` |
| `date` | `datetime` |
| `select` | `widget="select"` (static or `optionsResource`) |
| `many2one` | FK ending with `_id` |
| `badge` | `widget="badge"` (status fields) |
| `monetary` | `widget="monetary"` |
| `statusbar` | `widget="statusbar"` (form header) |
| `tags` | `list[str]` (JSON array) |
| `readonly` | any widget with `readonly=true` |

To add a new widget: register it in `packages/ui/src/widgets/` and the
`<ResourceForm>` / `<ResourceList>` components pick it up automatically.

## View types

| View | Required arch attribute | Status |
|---|---|---|
| list | (none) | implemented |
| form | (none) | implemented |
| kanban | `default_group_by` | implemented |
| calendar | `date_start` (and optional `date_end`) | planned (CRM-MVP) |
| graph | `measure`, `group_by` | planned |
| pivot | — | deferred |
| activities | — | deferred |

## Command Palette (⌘K)

- Modal opened by ⌘K (Mac) / Ctrl+K (Win/Linux).
- Searches Actions through `GET /api/ai/actions?q=...`.
- RapidFuzz scoring (~1 ms), no LLM in the happy path.
- Multilingual keyword matching (EN + PL extensible).

⌘K is **deterministic** action search. It is *not* a chat. The chat lives in
`<AIChatPanel>` — see `15-ai-layer.md`.

## AI integration in admin UI

| Component | Purpose |
|---|---|
| `<PromptInput>` | Embeddable text box on any module page; sends query with module's `accessible_models` context |
| `<AIChatPanel>` | Sidebar / drawer chat with tools available to the user |
| `<AIDashboard>` | Prompt → `aggregate` queries → recharts spec |
| `useAIContext(model, id)` | Hook that scopes context to current view |

All four come from `packages/ui` and are mandatory entry points — modules do
not call provider SDKs directly.

## Branding

- `useBranding()` returns `{ name, logo_url, favicon_url }` from `ir_config_param`.
- Logo, name, and favicon are tenant-controlled.
- The product name is **never** hardcoded in tracked content (see `AGENTS.md`).

## Forbidden patterns

- Per-module page files in `admin-ui/src/app/<module>/...`.
- Direct calls to provider APIs from the front-end.
- A second design system.
- New UI primitives outside `packages/ui` widget registry.
- Inline styles that bypass Mantine theme tokens.
