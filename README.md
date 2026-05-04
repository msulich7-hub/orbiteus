<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/symbol-readme.svg" alt="Orbiteus" width="160" />
  </a>

  **Orbiteus** — an AI-native engine for building business applications and internal AI agents.

  ![status](https://img.shields.io/badge/version-v1.0.0--rc1-blue)
  ![license](https://img.shields.io/badge/license-MIT-green)
  ![backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.13-3776AB)
  ![frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20Mantine%209-000000)
  ![db](https://img.shields.io/badge/db-PostgreSQL%2016%20%2B%20pgvector-336791)
</div>

> **Read me first if you're an AI agent:** [`docs/pre-prompt.md`](docs/pre-prompt.md).
> It is the canonical context for any agent (Cursor, Codex, Claude Code, custom)
> working on Orbiteus or building modules on top of it. Agents that skip it tend
> to invent libraries and bypass the framework primitives — both forbidden.

---

## What is Orbiteus?

Orbiteus is **not a finished product**. It is an **engine** — framework
primitives plus a small set of opinionated, batteries-included subsystems
(auth, RBAC, multitenancy, audit, cache, events, realtime, AI layer) and one
*canonical product example* (CRM-MVP) that demonstrates the platform. You
install the engine, register modules, brand the UI, and get a business
application shaped to your processes — not the other way around.

The contract:

  `registry.register("your_module")` →
  - SQL tables (created at startup),
  - REST API + OpenAPI per model,
  - dynamic UI (list / form / kanban / calendar / graph),
  - Command Palette actions, AI tool surface, audit, RBAC, realtime
    fan-out — all generated automatically.

Zero TSX per module. Zero "I copied a CRUD endpoint from another module".

## Why another framework?

| Need                                              | Orbiteus answer |
|---------------------------------------------------|-----------------|
| Multi-tenant ERP-shaped data model with RBAC      | `BaseRepository` enforces `tenant_id` + 5-level RBAC + record rules + soft delete + audit + attribution on every read/write |
| Plug-and-play AI tools that respect user RBAC     | Provider adapters (Anthropic / OpenAI / Ollama), BYOK, tool calling that goes through the same repository — AI never elevated |
| "Zero TSX per module"                             | Catch-all routes + widget registry + view-XML driven layout. New module → new tables + auto UI |
| Realtime across replicas                          | SSE on `/api/realtime/subscribe`, Redis Pub/Sub backplane, tenant-scoped topics |
| Boring, auditable infra                           | Single `docker compose up` brings a Postgres 16 + pgvector + Redis 7 + Celery worker + Celery Beat + nginx + Next 16 admin + portal stack |
| External-partner portal                           | Share-link tokens with explicit perms; portal-ui has its own realtime feed and read-only-by-default view declarations |

## Quick start (single command)

```bash
git clone <repo-url>
cd orbiteus
docker compose up --build
```

| Surface       | URL                                       |
|---------------|-------------------------------------------|
| Admin UI      | http://localhost:3000                     |
| Portal UI     | http://localhost:3000 (subpath via nginx) |
| API           | http://localhost:8000/api                 |
| OpenAPI docs  | http://localhost:8000/api/docs            |
| `/metrics`    | http://localhost:8000/metrics             |

Default login (dev only): `admin@example.com` / `admin1234`.
Rotate `BOOTSTRAP_ADMIN_PASSWORD` and `SECRET_KEY` before any production
traffic — the prod profile refuses to start otherwise.

## Architecture in one page

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 16)   |     |   portal-ui (Next.js 16)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/*  (Next rewrites + same-origin)        |
              v          v                       v            v
+------------------------------------------------------------------+
|  FastAPI behind Gunicorn + UvicornWorker                         |
|  orbiteus_core: registry, BaseRepository, AutoRouter, AI Layer,  |
|                 Auth, RBAC, Audit, EventBus, Cache, Realtime     |
|  modules:       base, auth, crm (canonical sample), ...          |
+----------+----------------------+--------------------+-----------+
           |                      |                    |
+----------v---------+  +---------v--------+  +--------v---------+
|  PostgreSQL 16     |  |  Redis 7         |  |  Celery workers  |
|  + pgvector        |  |  cache, pub/sub, |  |  (broker: Redis) |
|  via PgBouncer     |  |  rate limit,     |  |  + Celery Beat   |
|                    |  |  jti revocation  |  |  for schedules   |
+--------------------+  +------------------+  +------------------+
```

## What ships out of the box (v1.0.0-rc1)

* **Boring infra** — `docker compose --profile prod up -d --build` brings up
  Postgres + pgvector + PgBouncer + Redis + backend (Gunicorn + UvicornWorker)
  + Celery worker + Beat + admin-ui + portal-ui + nginx, with healthchecks
  and a one-shot `migrate` service.
* **Auth** — JWT (15 min access / 7 days refresh, refresh rotates), TOTP 2FA
  + recovery codes, password reset over email (single-use, time-bound),
  HttpOnly cookie session for the Admin UI, share-link tokens for portal.
* **RBAC** — 5 levels (group, model, record-rule, action, AI scope). Cache
  in Redis with cross-replica `rbac.invalidate` pub/sub.
* **Audit** — `ir_audit_log` populated on every CRUD by `BaseRepository`,
  plus `actor=ai` rows from AI tool calls and `actor=user` rows from auth
  events. PII redaction before persisting.
* **Events + queues** — EventBus for in-request hooks, `ir_outbox` committed
  atomically with business writes, Celery drains with bounded retry +
  `dead` terminal state, Celery Beat reads `ir_cron`.
* **Realtime** — `/api/realtime/subscribe` SSE multi-topic, Redis Pub/Sub
  backplane, tenant-scoped, portal-scoped variant for share-link tokens.
* **AI layer** — Anthropic / OpenAI / Ollama provider adapters with a stable
  ABC, BYOK with Fernet-at-rest, AI tool calls that go through the same
  repository (never elevated), `pgvector` `ir_embedding` table,
  `POST /api/ai/chat` (streaming + tool calling), `/api/ai/dashboard`.
* **Admin UI** — dynamic renderer, widget registry (text / number / monetary
  / date / many2one / badge / statusbar / tags / readonly / …), list +
  form + kanban + calendar + graph views, Command Palette (⌘K), realtime
  list refresh, empty states + loading skeletons, `/welcome` + `/login` +
  `/` split.
* **Portal UI** — share-link landing at `/s/[token]`, comment + attachment
  surfaces (gated by share-token permissions), portal-scoped realtime that
  refreshes the page when the underlying record changes.
* **Observability + ops** — JSON logs with `request_id`, Prometheus
  `/metrics` (14 series families covering HTTP / DB / Redis / Celery /
  Outbox / AI / Realtime), OpenTelemetry tracing opt-in, S3-capable
  nightly backups + executed restore drill.
* **CI gate** — docs validators + backend pytest with coverage XML +
  frontend Vitest + `next build` + Playwright (5 deterministic + 6
  env-gated) + `pip-audit` + `npm audit` + `detect-secrets` baseline +
  no-GPL license audit. One aggregator `gate` job for branch protection.

The full per-section progress against [`docs/35-core-definition-of-done.md`](docs/35-core-definition-of-done.md)
is tracked in [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md).

## Tech stack (binding — see `docs/pre-prompt.md` §3)

### Backend
- Python 3.13+, FastAPI, **Gunicorn + UvicornWorker** (production server)
- SQLAlchemy 2 (imperative mapping), asyncpg, Alembic
- **PgBouncer** in transaction pooling mode in front of PostgreSQL 16
- Pydantic v2, pydantic-settings
- python-jose (JWT) + bcrypt + pyotp (TOTP 2FA)
- redis-py async (cache, pub/sub backplane, rate limit, JWT `jti` revocation)
- **Celery 5** + Celery Beat (broker: Redis, backend: Redis)
- pgvector for embeddings (image: `pgvector/pgvector:pg16`)
- Anthropic SDK (default), OpenAI SDK (secondary), Ollama HTTP (optional)

### Frontend
- **Next.js 16** (App Router), **React 19**
- **Mantine 9** as the only design system (no shadcn / MUI / Chakra / Ant)
- npm workspaces with `packages/ui` shared between `admin-ui` and `portal-ui`

### Infra
- Docker + Docker Compose; nginx (reverse proxy + TLS via certbot)
- PostgreSQL 16 + pgvector, Redis 7

## Building a module

The full convention is in [`docs/03-modules.md`](docs/03-modules.md). Skeleton:

```
modules/<name>/
  manifest.py            # name, version, depends_on, models, menus
  model/
    domain.py            # @dataclass — pure Python, no SQLA
    mapping.py           # SQLAlchemy Table + register_mapping()
    schemas.py           # Pydantic Read / Write
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
```

Then in `backend/api.py`:

```python
registry.register("your_module")
```

You instantly get:

* SQL tables (Alembic auto-revision against the metadata),
* `GET/POST/PUT/DELETE /api/your_module/your_model[/{id}]`,
* OpenAPI per model,
* widget-registry-driven UI (list / form / kanban / calendar / graph),
* Command Palette actions,
* AI tool surface (every Action is callable as a tool, plus QueryTool per
  model declared in `ai.py`),
* audit / RBAC / realtime — for free.

## Running tests

```bash
# backend (pytest with coverage)
PYTHONPATH=backend pytest -q --cov --cov-report=term

# frontend unit tests
npm test --workspace admin-ui

# Playwright E2E (requires a running stack on :3000)
npm run e2e --workspace admin-ui
```

The full CI gate runs in `.github/workflows/ci.yml`. See
[`docs/20-testing.md`](docs/20-testing.md) for the test pyramid.

## Documentation map

| Topic | File |
|---|---|
| Pre-prompt for AI agents (read first)            | [`docs/pre-prompt.md`](docs/pre-prompt.md) |
| Architecture                                     | [`docs/02-architecture.md`](docs/02-architecture.md) |
| Module convention                                | [`docs/03-modules.md`](docs/03-modules.md) |
| Data model + `ir_*` tables                       | [`docs/04-data-model.md`](docs/04-data-model.md) |
| RBAC + multi-tenancy                             | [`docs/05-rbac-multitenancy.md`](docs/05-rbac-multitenancy.md) |
| Auth (JWT, refresh rotation, 2FA, share-links)   | [`docs/06-auth.md`](docs/06-auth.md) |
| Auto-CRUD API + query operators + webhooks       | [`docs/07-api.md`](docs/07-api.md) |
| Admin UI dynamic renderer                        | [`docs/08-admin-ui.md`](docs/08-admin-ui.md) |
| Portal UI                                        | [`docs/09-portal-ui.md`](docs/09-portal-ui.md) |
| Realtime (SSE + Redis Pub/Sub)                   | [`docs/11-realtime.md`](docs/11-realtime.md) |
| Events + queues (EventBus + Outbox + Celery)     | [`docs/12-events-and-queues.md`](docs/12-events-and-queues.md) |
| Audit policy                                     | [`docs/14-audit.md`](docs/14-audit.md) |
| AI layer (providers, BYOK, tools, embeddings)    | [`docs/15-ai-layer.md`](docs/15-ai-layer.md) |
| Deployment (compose dev / prod, nginx, certbot)  | [`docs/17-deployment.md`](docs/17-deployment.md) |
| Security (CSP, secrets, threat model)            | [`docs/18-security.md`](docs/18-security.md) |
| Testing (pytest, Vitest, Playwright)             | [`docs/20-testing.md`](docs/20-testing.md) |
| Observability (logs, metrics, traces)            | [`docs/29-observability.md`](docs/29-observability.md) |
| Backups + DR                                     | [`docs/31-backups-and-dr.md`](docs/31-backups-and-dr.md) |
| Inventory vs docs (running ledger)               | [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) |
| Definition of Done                               | [`docs/35-core-definition-of-done.md`](docs/35-core-definition-of-done.md) |
| ADRs                                             | [`docs/adr/`](docs/adr/) |

## Versioning + release

This release is `v1.0.0-rc1` — see [`CHANGELOG.md`](CHANGELOG.md) for the
release notes and [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md)
for the per-section DoD ledger. The `v1.0.0` GA tag waits for the items
flagged `rc1 → GA` in the inventory.

## License

MIT — see [`LICENSE`](LICENSE). Third-party license inventory in
[`THIRD_PARTY_LICENSES.python.json`](THIRD_PARTY_LICENSES.python.json) and
[`THIRD_PARTY_LICENSES.node.json`](THIRD_PARTY_LICENSES.node.json), regenerated
by `scripts/generate_licenses.sh`. The CI gate refuses GPL/AGPL/LGPL families
outside an explicit dynamic-link allow-list (see `docs/27-licenses.md`).
