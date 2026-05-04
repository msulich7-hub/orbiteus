<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/symbol-readme.svg" alt="Orbiteus" width="160" />
  </a>

  <!-- LOCKED: README hero (pitch) — do not edit without explicit product-owner approval (see AGENTS.md). -->
  **Orbiteus — Own the software. Ship the vertical. Stop renting your workflow.**

  *An AI-native engine that turns months of integration into **weeks of differentiation** — for teams who need **production-grade** business apps without chaining themselves to someone else’s roadmap.*

  ![status](https://img.shields.io/badge/version-v1.0.0-blue)
  ![license](https://img.shields.io/badge/license-MIT-green)
  ![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)
  ![backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.13-3776AB)
  ![frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20Mantine%209-000000)
  ![db](https://img.shields.io/badge/db-PostgreSQL%2016%20%2B%20pgvector-336791)
</div>

---

## The problem

**Vertical businesses run on software that was never meant to exist as a SKU.** Off-the-shelf SaaS fits the median company — not the gym chain, the studio, the logistics operator, or the niche B2B market you actually serve. So teams either bend their process around generic tools, or they burn quarters wiring auth, tenants, permissions, audit, APIs, admin UI, jobs, and AI — before they write a single line of *their* competitive logic.

That is the tax: **integration debt disguised as “we’re building product.”**

---

## What Orbiteus is

Orbiteus is **not a finished app you subscribe to** — it is an **application engine**: multi-tenant identity, security, data layer, admin and partner surfaces, events, realtime, observability, and an **AI layer that respects the same rules as people**. You install the engine, register modules, and ship **your** product — with **your** margins, **your** data model, and **your** roadmap.

Think of it as **infrastructure for software businesses** — a challenger to “rent every workflow forever” SaaS.

---

## Who it is for

| Audience | What changes for them |
|----------|----------------------|
| **Founders & product-led teams** | You sell the **20%** that is your market — not another hand-rolled auth story or webhook retry loop. |
| **Engineering orgs under time pressure** | Serious teams **compress delivery** because the platform already carries tenancy, RBAC, audit, APIs, admin patterns, queues, and realtime. |
| **Builders using AI-assisted development** | When the guardrails are in the engine, **velocity does not trade away production quality** — security and compliance hooks are defaults, not afterthoughts. |
| **Anyone tired of SaaS lock-in** | **You own the deployment, the brand, and the economics** — not a vendor’s feature calendar. |

---

## How Orbiteus solves it

1. **Ship the differentiated core first** — Auth, multi-tenancy, layered permissions, audit, auto-APIs, dynamic admin UI patterns, background work, webhooks, and AI tools are **already in the box**; you focus on domain models and customer value.
2. **AI that ships safely** — Agents call tools through the same repository and policy layer as human users — **no shadow IT inside your own product.**
3. **One command to a working stack** — Local development spins Postgres (with pgvector), Redis, API, admin UI, and portal UI together so **demo day and diligence both see a real system**, not a slide.

---

## Quick start

```bash
git clone <repo-url>
cd orbiteus
docker compose up --build
```

| Surface | URL |
|--------|-----|
| Admin UI | http://localhost:3000 |
| Portal UI | http://localhost:3001 (dev compose; prod uses reverse proxy — see deployment docs) |
| API | http://localhost:8000/api |
| OpenAPI | http://localhost:8000/api/docs |
| Metrics | http://localhost:8000/metrics |

Default login (development only): `admin@example.com` / `admin1234`.  
Rotate `BOOTSTRAP_ADMIN_PASSWORD` and `SECRET_KEY` before any production traffic — the production profile refuses default secrets.

---

## Outcomes the engine is built to prove

| | |
|---|---|
| **Speed without recklessness** | Registry-driven modules wire models, security, views, actions, and optional AI in one place — so **delivery stays fast** while **policy stays enforced**. |
| **Zero throwaway CRUD** | Catch-all admin routes + view config — new tables ship with **matching UI patterns** without a separate front-end rewrite per entity. |
| **Enterprise-shaped defaults** | Tenant isolation at the repository layer, record rules, signed webhooks, outbox + workers, SSE with tenant-scoped topics. |
| **Investor- and buyer-ready story** | Observable, test-gated, documented — **serious software**, not a prototype dressed as a platform. |

For the engineering checklist against the internal Definition of Done, see [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) and [`CHANGELOG.md`](CHANGELOG.md).

---

## What ships in the box (summary)

- **Identity & sessions** — JWT access/refresh with rotation, TOTP + recovery codes, password reset, HttpOnly session for the admin shell, share tokens for portal users.
- **Data & rules** — Async SQLAlchemy 2, Alembic, soft delete hooks, record rules, strict tenant filters on repositories.
- **AI** — Provider adapters (Anthropic, OpenAI, Ollama), BYOK storage, streaming chat, tool dispatcher, embeddings with pgvector.
- **Ops** — Structured logs, Prometheus metrics, optional OpenTelemetry, backup and restore-drill documentation.
- **Quality gate** — CI aggregates docs checks, tests, audits, and license policy.

---

## For engineers (stack, modules, tests)

> **AI agents** working in this repository: read [`docs/pre-prompt.md`](docs/pre-prompt.md) first — canonical stack and convention contract. Skipping it leads to invented dependencies and bypassed primitives.

### Tech stack (authoritative detail)

Binding list: [`docs/pre-prompt.md`](docs/pre-prompt.md) (stack section). In short: Python 3.13, FastAPI, SQLAlchemy 2 + asyncpg, Pydantic v2, Redis, Celery 5, PostgreSQL 16 + pgvector, Next.js 16 + React 19 + Mantine 9.

**Monorepo (npm workspaces):** `admin-ui` and `portal-ui` only. Shared widgets and AI surfaces live under **`admin-ui/src/orbiteus-ui/`**; copy into `portal-ui` when the partner app needs the same UX (two deployable apps).

### Module layout

Full convention: [`docs/03-modules.md`](docs/03-modules.md). Skeleton:

```
modules/<name>/
  manifest.py
  model/domain.py, mapping.py, schemas.py
  controller/repositories.py, services.py, router.py
  security/access.yaml
  view/*.xml, config.py
  actions.py, ai.py, bootstrap.py, docs/spec.md
```

Register once:

```python
registry.register("your_module")
```

You get migrations, REST + OpenAPI, dynamic list/form/kanban/calendar/graph patterns, Command Palette actions, AI tool surface, audit, RBAC, and realtime hooks — without copying CRUD from another module.

### Architecture at a glance

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 16)   |     |   portal-ui (Next.js 16)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/*  (admin-ui: server proxy; portal: rewrites + same-origin)|
              v          v                       v            v
+------------------------------------------------------------------+
|  FastAPI (Gunicorn + UvicornWorker in production)               |
|  orbiteus_core: registry, repositories, auto-router, AI,        |
|                 auth, RBAC, audit, events, cache, realtime       |
|  modules:       base, auth, crm (reference sample), …          |
+----------+----------------------+--------------------+-----------+
           |                      |                    |
+----------v---------+  +---------v--------+  +--------v---------+
|  PostgreSQL 16     |  |  Redis 7         |  |  Celery 5        |
|  + pgvector        |  |  cache, pub/sub, |  |  + Beat          |
|  (+ PgBouncer)     |  |  rate limits,   |  |  outbox drain    |
+--------------------+  |  session revoke  |  |  + webhooks       |
                        +------------------+------------------+
```

### Running tests

```bash
# backend
PYTHONPATH=backend pytest -q --cov --cov-report=term

# admin UI unit tests
npm test --workspace admin-ui

# Playwright (stack on :3000)
npm run e2e --workspace admin-ui
```

Details: [`docs/20-testing.md`](docs/20-testing.md) and `.github/workflows/ci.yml`.

---

## Documentation map

| Topic | File |
|-------|------|
| Pre-prompt (read first) | [`docs/pre-prompt.md`](docs/pre-prompt.md) |
| Architecture | [`docs/02-architecture.md`](docs/02-architecture.md) |
| Modules | [`docs/03-modules.md`](docs/03-modules.md) |
| Data model + `ir_*` | [`docs/04-data-model.md`](docs/04-data-model.md) |
| RBAC + multi-tenancy | [`docs/05-rbac-multitenancy.md`](docs/05-rbac-multitenancy.md) |
| Auth | [`docs/06-auth.md`](docs/06-auth.md) |
| Auto-CRUD API + webhooks | [`docs/07-api.md`](docs/07-api.md) |
| Admin UI | [`docs/08-admin-ui.md`](docs/08-admin-ui.md) |
| Design system (Mantine + `orbiteus-ui`) | [`docs/10-design-system.md`](docs/10-design-system.md) |
| Portal UI | [`docs/09-portal-ui.md`](docs/09-portal-ui.md) |
| Realtime | [`docs/11-realtime.md`](docs/11-realtime.md) |
| Events + queues | [`docs/12-events-and-queues.md`](docs/12-events-and-queues.md) |
| Audit | [`docs/14-audit.md`](docs/14-audit.md) |
| AI layer | [`docs/15-ai-layer.md`](docs/15-ai-layer.md) |
| Deployment | [`docs/17-deployment.md`](docs/17-deployment.md) |
| Security | [`docs/18-security.md`](docs/18-security.md) |
| Testing | [`docs/20-testing.md`](docs/20-testing.md) |
| Observability | [`docs/29-observability.md`](docs/29-observability.md) |
| Backups + DR | [`docs/31-backups-and-dr.md`](docs/31-backups-and-dr.md) |
| Inventory ledger | [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) |
| Definition of Done | [`docs/35-core-definition-of-done.md`](docs/35-core-definition-of-done.md) |
| ADRs | [`docs/adr/`](docs/adr/) |

---

## Contributing

We welcome fixes, docs, and modules that follow the registry contract. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md).

---

## Versioning + release

Current line is **`v1.0.0`**. Release notes: [`CHANGELOG.md`](CHANGELOG.md). Honest code-vs-docs progress: [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md).

---

## License

MIT — see [`LICENSE`](LICENSE). Third-party manifests: [`THIRD_PARTY_LICENSES.python.json`](THIRD_PARTY_LICENSES.python.json), [`THIRD_PARTY_LICENSES.node.json`](THIRD_PARTY_LICENSES.node.json) (regenerated via `scripts/generate_licenses.sh`; CI enforces a no-GPL policy — see `docs/27-licenses.md`).
