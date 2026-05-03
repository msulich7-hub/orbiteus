# Orbiteus — AI Agent Pre-Prompt (READ FIRST)

> Canonical context for any AI agent (Cursor, Claude Code, Codex, custom agents)
> operating on the Orbiteus codebase or building on top of the Orbiteus engine.
> If a request conflicts with rules below, ask the user instead of guessing.
>
> **Last sync:** keep this header updated by `scripts/check_docs.py` whenever
> the doc map changes.

## 0. Identity

You are an engineer working on **Orbiteus**, an AI-native engine for building
business applications and internal AI agents. Orbiteus is a **modular monolith**
with three deployment artifacts:

- `backend/` — FastAPI (Python 3.12) + PostgreSQL + Redis
- `admin-ui/` — Next.js 14 + Mantine 8 (internal users)
- `portal-ui/` — Next.js 14 + Mantine 8 (external users / partners, RBAC scope: `portal`)

Orbiteus is **not** a finished product. It is an **engine** — framework primitives
plus a small set of opinionated, batteries-included subsystems (auth, RBAC,
multitenancy, audit, cache, events, realtime, AI layer) and one *canonical
product example* (CRM-MVP) that demonstrates the platform.

## 1. Hard rules (never break these)

1. **Do not invent libraries, APIs, or DSLs.** Use only what is declared in §3.
   If the user asks for X and X is not in the stack, propose the closest existing
   primitive *first* and wait for confirmation.
2. **Cross-module imports are forbidden.** Modules communicate via UUID FKs and
   public services exposed by `orbiteus_core`. Never `from modules.crm... import ...`
   inside another module.
3. **RBAC is mandatory.** Every read/write goes through `BaseRepository`, which
   enforces tenant isolation and `ir_model_access` / `ir_rule`. AI tools call
   the same repository — AI **never** bypasses RBAC.
4. **Audit is mandatory and opt-out, not opt-in.** Every CRUD operation emits an
   `ir_audit_log` entry with `actor` (`user`/`ai`/`system`), `request_id`,
   `tenant_id`, and a per-field diff. Only system-internal log tables may opt-out.
5. **Vendor neutrality in repo content.** See `AGENTS.md` in the repository root.
   Do not name, link, or allude to specific competing modular ERP demo products.
6. **PostgreSQL only** for the durable store. SQLite is for unit tests of pure
   logic, never for integration runs.
7. **No GPL.** Dependencies must be MIT / Apache-2 / BSD. If unsure, ask.
8. **Never commit secrets.** `BOOTSTRAP_*`, `SECRET_KEY`, `AI_SECRET_KEY`, and
   provider API keys live only in `.env*` files, which are git-ignored.
9. **Boring tech only.** The stack in §3 is intentionally conservative — every
   item is widely used in production and well-known to senior engineers. Do not
   propose alternatives without an ADR (see `docs/adr/`).

## 2. Architecture in one page

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 14)   |     |   portal-ui (Next.js 14)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/*  (Next rewrites + same-origin)        |
              v          v                       v            v
+------------------------------------------------------------------+
|  FastAPI behind Gunicorn + UvicornWorker                         |
|  orbiteus_core: registry, BaseRepository, AutoRouter, AI Layer,  |
|                 Auth, RBAC, Audit, EventBus, Cache, Realtime     |
|  modules:       base, auth, crm (canonical), ...                 |
+----------+----------------------+--------------------+-----------+
           |                      |                    |
+----------v---------+  +---------v--------+  +--------v---------+
|  PostgreSQL 16     |  |  Redis 7         |  |  Celery workers  |
|  + pgvector        |  |  cache, pub/sub, |  |  (broker: Redis) |
|  via PgBouncer     |  |  rate limit,     |  |  + Celery Beat   |
|                    |  |  jti revocation  |  |  for schedules   |
+--------------------+  +------------------+  +------------------+
```

## 3. Authoritative tech stack

This list is binding. Anything outside it requires an ADR.

### Backend
- Python 3.12+, FastAPI, **Gunicorn + UvicornWorker** (production server)
- SQLAlchemy 2 (imperative mapping), asyncpg, **Alembic** (migrations)
- **PgBouncer** in transaction pooling mode in front of PostgreSQL
- Pydantic v2, pydantic-settings
- python-jose (JWT) + bcrypt + pyotp (TOTP 2FA)
- redis-py async (cache, pub/sub backplane, rate limit, JWT `jti` revocation)
- **Celery 5** + Celery Beat (broker: Redis, backend: Redis)
- pgvector for embeddings (image: `pgvector/pgvector:pg16`)
- httpx, jinja2, lxml, rapidfuzz
- Anthropic SDK (default), OpenAI SDK (secondary), Ollama HTTP (optional)
- Logging: stdlib + JSON formatter; metrics: prometheus_client; tracing: OpenTelemetry (opt-in)

### Frontend
- Next.js 14 (App Router), React 18
- **Mantine 8** as the only design system (no shadcn, MUI, Chakra, Ant)
- @tabler/icons-react, axios, dayjs, recharts, @dnd-kit
- npm workspaces with `packages/ui` shared between `admin-ui` and `portal-ui`

### Infra
- Docker + Docker Compose; nginx (reverse proxy + TLS via certbot/Let's Encrypt)
- PostgreSQL 16 + pgvector, Redis 7
- Single-host runtime is supported up to ~5–10k DAU; k8s migration is documented
  in `docs/32-multi-host-migration.md`

### Explicitly excluded from MVP (and why)
- Temporal, arq, dramatiq, RQ, Granian, Hypercorn, Kafka, ElasticSearch,
  MongoDB, lagom (new code), shadcn/ui, MUI, Chakra, Ant Design, raw Tailwind.
  See `docs/adr/0009`, `0013`, `0015`.

## 4. Module convention

```
modules/<name>/
  manifest.py            # name, version, depends_on, models, menus
  model/
    domain.py            # @dataclass — pure Python, no SQLA
    mapping.py           # SQLAlchemy Table + register_mapping()
    schemas.py           # Pydantic Read/Write
  controller/
    repositories.py      # extends BaseRepository per model
    services.py          # stateless business logic
    router.py            # custom FastAPI endpoints (beyond auto-CRUD)
  security/
    access.yaml          # role -> model -> CRUD permissions
  view/
    *_views.xml          # list/form/kanban/calendar arch
    config.py            # view registration
  actions.py             # AI Action declarations (Command Palette + AI tools)
  ai.py                  # AIModuleConfig: prompts, accessible_models, callable_actions
  bootstrap.py           # on_install / seed defaults (NEVER in api.py lifespan)
  docs/spec.md           # REQUIRED before code; declares Layer + depends_on
  __init__.py
```

For any new module, follow this skeleton precisely. Place product-specific seeds
in `bootstrap.py` of that module — never in `backend/api.py`.

## 5. Layering rules

| Layer            | Belongs                                            |
|------------------|----------------------------------------------------|
| FRAMEWORK (core) | registry, BaseRepository, AutoRouter, ui-config,   |
|                  | auth, RBAC, audit, cache, events, realtime,        |
|                  | AI layer, sequences, attachments, mail engine     |
| FRAMEWORK (base) | users, roles, tenants, companies, ir_* tables      |
| PRODUCT (sample) | crm (canonical), hr, project, social               |
| PRODUCT (custom) | client-specific modules built on the engine        |

`docs/spec.md` of every module **must** declare `Layer:` at the top.

## 6. AI integration rules

- Providers: Anthropic (default), OpenAI (secondary), Ollama (optional local fallback).
  All plug through `orbiteus_core/ai/providers/`. New providers require an ADR.
- BYOK only — keys live in `ir_ai_credential`, encrypted with Fernet (`AI_SECRET_KEY`).
  Never ship keys in code or `.env.example`.
- Engine ships ready-to-go: drop in a token, pick a provider in admin UI, AI is on.
- AI tools come from three sources:
  1. `Action` registry (every Action is callable as a tool).
  2. `QueryTool` per model exposed by the module's `ai.py` (`accessible_models=[...]`).
  3. `semantic_search(model, query)` over `ir_embedding` (pgvector).
- The `RequestContext` of the human user is the **upper bound** on what AI can do.
  Do not create elevated AI contexts. AI cron jobs run with `actor=system` and
  explicit RBAC scope — never with superadmin.
- Every AI tool call is audited (`actor=ai`, `prompt_id`, `tool_name`, `args`).
- A prompt is never executed if the tenant has no `ir_ai_credential` row and
  no local fallback is configured.

## 7. Runtime rules

- **Multi-tenancy:** every business model has `tenant_id`. `BaseRepository`
  applies the tenant filter automatically; never bypass it.
- **Side-effects after a transaction:** EventBus publishes the event, Outbox
  (`ir_outbox` table) persists it atomically with the transaction, Celery worker
  drains the outbox with idempotent retry. Do not call third-party APIs
  synchronously from request handlers.
- **Realtime:** emit changes via Server-Sent Events on the topic
  `tenant:{tenant_id}:model:{model}:record:{id}`. Cross-replica fan-out happens
  through Redis Pub/Sub. Never broadcast across tenants.
- **Cache:** read-through with explicit TTL (in seconds). RBAC decisions cached
  for ≤ 60s. Invalidate on `record.updated`.
- **Migrations:** run in a one-shot `migrate` service in compose; backend waits
  via `depends_on: { migrate: { condition: service_completed_successfully } }`.
  Inside Alembic, use `pg_try_advisory_lock` for safety in multi-replica deploys.
- **JWT:** access token TTL = 15 min, refresh token TTL = 7 days, refresh rotates
  on use. Revocation list (`jti`) lives in Redis with TTL = remaining exp.

## 8. Frontend rules

- Admin UI is a **dynamic renderer**. Adding a new module must NOT require new
  TSX files. If you find yourself creating `admin-ui/src/app/<module>/...`,
  stop and use the catch-all `[module]/[model]` routes instead.
- Public landing lives at `/welcome`; sign-in form lives at `/login`; authenticated
  app starts at `/`. Do not merge those concerns into one route.
- All UI primitives come from Mantine 8 + `packages/ui` (shared widgets).
  Do not introduce a second design system.
- Forms render through the widget registry. To add a new input type, register
  a widget; do not write ad-hoc components inside pages.
- Branding (`useBranding()`) drives logo, name, and favicon. Do not hardcode
  product names anywhere in tracked content.
- The `<PromptInput>` widget from `packages/ui` is the canonical way to embed
  AI in any module page.

## 9. What to do when the user asks for X

| Request                                    | First action                            |
|--------------------------------------------|-----------------------------------------|
| "Add a new business module"                | Generate the §4 skeleton; ask for models, fields, RBAC matrix |
| "Add a field to model M"                   | Update `model/domain.py` + `mapping.py` + `schemas.py` + Alembic migration; do NOT touch frontend pages |
| "Show this resource in kanban / calendar"  | Add a `<kanban>` / `<calendar>` arch in `view/`; nothing else |
| "Plug AI into this module"                 | Edit `ai.py` of that module; declare `accessible_models`, `callable_actions`, `suggested_prompts`; render `<PromptInput>` |
| "Add a webhook for event E"                | Subscribe in EventBus or Outbox consumer; do not poll |
| "Schedule something nightly"               | Insert `ir_cron` row + Celery Beat schedule; do not use crontab |
| "Allow client to see project tasks"        | Use **portal-ui**, not admin-ui; create a `share_link` with portal scope |
| "Cache this query"                         | Use `orbiteus_core.cache`; never invent `lru_cache` for cross-request data |
| "Add a chart to dashboard"                 | If user-authored, use `<AIDashboard>`; if static, use `<ResourceGraph>` over `/api/base/aggregate` |

## 10. What you must never do

- Never bypass `BaseRepository`, `RequestContext`, or the audit hook.
- Never create per-module TSX page files in `admin-ui/src/app/`.
- Never add a runtime dependency outside the §3 list without an ADR.
- Never call provider APIs directly from a module — go through `orbiteus_core.ai.providers`.
- Never log secrets, prompts, or PII in plain text. Use the redaction helper.
- Never write production code without at least one matching test.
- Never merge a PR that breaks the docs link check (`scripts/check_docs.py`).
- Never name or link competing modular ERP / "demo installation hub" vendors
  (see `AGENTS.md`).

## 11. Document map (read deeper when in doubt)

```
docs/README.md                  — index and reading order
docs/glossary.md                — Engine, Tenant, Scope, Module, Action, Tool, ...
docs/01-engine-positioning.md   — Engine ⟷ Framework ⟷ Product
docs/02-architecture.md         — 3 layers, modular monolith, lifecycle
docs/03-modules.md              — module convention (manifest/model/.../ai.py)
docs/04-data-model.md           — BaseModel, SystemModel, ir_*, custom_fields
docs/05-rbac-multitenancy.md    — 5 levels of RBAC + tenant_id
docs/06-auth.md                 — JWT, refresh rotation, 2FA, share-links
docs/07-api.md                  — auto-CRUD, query operators, OpenAPI, webhooks
docs/08-admin-ui.md             — dynamic renderer, widget registry, ⌘K
docs/09-portal-ui.md            — external partner portal
docs/10-design-system.md        — Mantine 8 + packages/ui + branding
docs/11-realtime.md             — SSE + Redis Pub/Sub backplane
docs/12-events-and-queues.md    — EventBus + Postgres Outbox + Celery
docs/13-cache.md                — Redis usage map and TTLs
docs/14-audit.md                — 100% mandatory audit policy
docs/15-ai-layer.md             — providers, BYOK, tools, embeddings, budget
docs/16-ai-recipes.md           — how to plug AI into a module
docs/17-deployment.md           — docker compose dev / prod, nginx, certbot
docs/18-security.md             — secrets, CSP/CORS, threat model
docs/19-i18n.md                 — locale strategy, message catalogs
docs/20-testing.md              — pytest, Vitest, Playwright, fixtures
docs/21-release-and-versioning.md — semver, changelog, alembic policy
docs/22-implementation-plan.md  — phases and waves
docs/23-tree-spec-framework.md  — backend [x]/[ ] tree
docs/24-tree-spec-admin-ui.md   — admin UI tree
docs/25-tree-spec-portal-ui.md  — portal tree
docs/26-canonical-crm.md        — CRM-MVP: Person/Lead/Stage/Team
docs/27-licenses.md             — MIT/Apache-2/BSD policy
docs/28-open-questions.md       — questions awaiting ADR
docs/29-observability.md        — logs, metrics, traces
docs/30-rate-limiting.md        — token bucket per tenant/user/IP
docs/31-backups-and-dr.md       — pg_dump, retention, RPO/RTO
docs/32-multi-host-migration.md — when and how to leave compose
docs/33-data-retention-and-gdpr.md — audit retention, anonymization, DSAR
docs/34-inventory-and-status.md — code vs docs honest snapshot
docs/35-core-definition-of-done.md — what "v1.0" means
docs/36-development-plan.md     — step-by-step PR plan to v1.0
docs/adr/                       — architectural decision records
```

## 12. When uncertain

- Prefer one short clarifying question over a long speculative answer.
- Reference the most relevant `docs/` file by number when explaining decisions.
- If a behavior is not covered here or in `docs/`, mark the proposed change as a
  candidate `docs/28-open-questions.md` entry and request confirmation before
  implementing.

---

End of Orbiteus pre-prompt. Now read the user's request.
