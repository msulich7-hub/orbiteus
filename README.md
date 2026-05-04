<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/symbol-readme.svg" alt="Orbiteus" width="160" />
  </a>

  **Orbiteus** — A full-stack foundation framework for AI agents and business software.

  *Build custom ERP-shaped tools, CRMs, internal apps, and partner portals in days, not months. Start with roughly 80% of the hard work already done.*

  ![status](https://img.shields.io/badge/version-v1.0.0-blue)
  ![license](https://img.shields.io/badge/license-MIT-green)
  ![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)
  ![backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.13-3776AB)
  ![frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20Mantine%209-000000)
  ![db](https://img.shields.io/badge/db-PostgreSQL%2016%20%2B%20pgvector-336791)
</div>

> **AI agents working in this repo:** read [`docs/pre-prompt.md`](docs/pre-prompt.md) first. It is the canonical stack + convention contract. Skipping it leads to invented dependencies and bypassed primitives — both out of bounds.

---

## Why Orbiteus exists

AI coding assistants are fast at *writing* code. They are weak at deciding **where** it lives, **how** layers stay consistent, and **whether** thirty engineers will ship the same patterns six months from now.

**Orbiteus is the open-source foundation that fixes that** — not a single vertical product, but a **generalist engine** for serious business tools:

- **Living architecture** — module registry, repositories, auto-CRUD, and UI config so new domain code lands in predictable places instead of ad-hoc folders.
- **Spec- and doc-first** — `docs/pre-prompt.md`, ADRs, and tests are part of the product; agents and humans share the same source of truth.
- **Production-shaped defaults** — multi-tenant data isolation, RBAC, audit trail, background jobs, outbox + webhooks, realtime, observability, and security gates — before you write your first business rule.
- **AI that stays inside guardrails** — bring your own model keys (BYOK); tool calls execute through the same RBAC and repositories as human users — never elevated.
- **One canonical sample** — a small CRM module proves list / form / kanban / calendar / graph + AI actions; it is an example, not the ceiling of what you can build.
- **MIT, self-hosted, full code ownership** — no per-seat pricing trap on the engine itself.

**End with “almost-ready apps”. Ship professional. Ship fast.**

---

## Who it is for

- **Engineering leaders** who already rolled out AI assistants and noticed velocity without structure does not scale.
- **Product-minded developers** who want internal tools and customer-facing backends that still look like software after the demo.
- **Small teams and ambitious builders** who need ERP-*shaped* reliability (tenants, permissions, audit) without committing to a single vendor’s product map.

---

## Core use cases

Orbiteus is **not** “ERP only”. It is a **business-tool foundation**: you mix modules, models, and workflows while keeping a production-ready spine.

| | |
|---|---|
| **Internal ops** | Line-of-business apps, approvals, master data, and admin surfaces generated from your module definitions. |
| **CRM & pipeline** | Reference module (Person, Lead, Stage, Team) with list, kanban, calendar, graph, and realtime — clone the pattern for your domain. |
| **Headless / API-first** | Typed REST + OpenAPI per registered model for mobile, web, or integrations — same tenancy and rules as the UI. |
| **Partner & field portals** | Share-link access with explicit permissions; separate Next.js portal app with scoped realtime. |
| **AI copilots & agents** | Chat, streaming, tool registry, and dashboard aggregates — always under caller RBAC. |
| **Multi-tenant SaaS backends** | Strict `tenant_id` discipline, record rules, and tests that prove cross-tenant isolation. |

---

## Highlights

| | |
|---|---|
| **Modular monolith** | `registry.register("your_module")` wires models, security, views, actions, and optional AI surface in one place. |
| **Zero TSX per business module** | Catch-all admin routes + widget registry + view XML — new tables and APIs ship with matching UI patterns. |
| **Multi-tenant by default** | Repository-enforced tenancy; negative tests for cross-tenant access. |
| **Layered RBAC** | Model access, record rules, actions, and AI scopes; Redis-backed cache with cross-replica invalidation. |
| **Audit everything that matters** | CRUD, auth events, AI tool calls — with redaction hooks for sensitive payloads. |
| **Events, outbox, webhooks** | Atomic outbox rows, Celery workers, bounded retries, dead-letter path, HMAC-signed delivery. |
| **Realtime** | SSE + Redis Pub/Sub; tenant-scoped topics; admin lists and portal views can subscribe safely. |
| **Boring infra in one command** | Docker Compose brings Postgres 16 + pgvector, Redis, workers, admin UI, portal UI, and nginx-shaped reverse proxy patterns. |
| **CI you can trust** | Docs checks, pytest + coverage artifact, Vitest, `next build`, Playwright, audits, secrets baseline, and license policy on every merge. |

---

## What “start with ~80% done” means here

**Buy vs. build?** You get a hardened **platform layer** — auth, tenants, RBAC, audit, jobs, realtime, AI harness, admin renderer, portal pattern — and you invest your margin in the **20%** that differentiates your business (data model, workflows, UX, integrations).

The remaining work is *your* modules and rules, not re-implementing session management for the fiftieth time.

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
| Portal UI | same host via reverse proxy in prod compose (see deployment docs) |
| API | http://localhost:8000/api |
| OpenAPI | http://localhost:8000/api/docs |
| Metrics | http://localhost:8000/metrics |

Default login (development only): `admin@example.com` / `admin1234`.  
Rotate `BOOTSTRAP_ADMIN_PASSWORD` and `SECRET_KEY` before any production traffic — the production profile refuses default secrets.

---

## Architecture at a glance

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 16)   |     |   portal-ui (Next.js 16)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/*  (Next rewrites + same-origin)        |
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
+--------------------+  |  session revoke  |  + webhooks       |
                        +------------------+------------------+
```

---

## What ships in the box (summary)

For the full checklist against the internal Definition of Done, see [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) and [`CHANGELOG.md`](CHANGELOG.md). In one breath:

- **Identity & sessions** — JWT access/refresh with rotation, TOTP + recovery codes, password reset flow, HttpOnly cookie session for the admin shell, share tokens for portal.
- **Data & rules** — Async SQLAlchemy 2, Alembic, soft delete hooks, attribution columns, record rules, strict tenant filters on repositories.
- **AI** — Provider adapters (Anthropic, OpenAI, Ollama), BYOK storage, streaming chat, tool dispatcher, embeddings table with pgvector.
- **Ops** — Structured logs, Prometheus metrics families, optional OpenTelemetry, backup scripts and restore-drill documentation.
- **Quality gate** — GitHub Actions workflow aggregating docs, tests, audits, and license reports.

---

## For engineers (stack & modules)

### Tech stack (authoritative detail)

Binding list lives in [`docs/pre-prompt.md`](docs/pre-prompt.md) (stack section). In short: Python 3.13, FastAPI, SQLAlchemy 2 + asyncpg, Pydantic v2, Redis, Celery 5, PostgreSQL 16 + pgvector, Next.js 16 + React 19 + Mantine 9 in a workspace layout.

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

You get migrations against declared tables, REST + OpenAPI for each model, dynamic list/form/kanban/calendar/graph, Command Palette actions, AI tool surface, audit, RBAC, and realtime hooks — without copying CRUD from another module.

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

We welcome fixes, docs, and modules that follow the registry contract. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) (branching, review expectations, and the PR checklist) and [`AGENTS.md`](AGENTS.md) for automation policy.

---

## Versioning + release

Current line is **`v1.0.0`**. Release notes: [`CHANGELOG.md`](CHANGELOG.md). Honest code-vs-docs progress: [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md).

---

## License

MIT — see [`LICENSE`](LICENSE). Third-party manifests: [`THIRD_PARTY_LICENSES.python.json`](THIRD_PARTY_LICENSES.python.json), [`THIRD_PARTY_LICENSES.node.json`](THIRD_PARTY_LICENSES.node.json) (regenerated via `scripts/generate_licenses.sh`; CI enforces a no-GPL policy with a small compatibility allow-list — see `docs/27-licenses.md`).
