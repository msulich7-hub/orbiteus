<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/symbol-readme.svg" alt="Orbiteus" width="160" />
  </a>

  <!-- LOCKED: README hero tagline — do not edit without explicit product-owner approval (see AGENTS.md). -->
  **Orbiteus — A Full-Stack Development Framework for AI Agents. Build custom ERP, CRM & Business Tools in days not months. Start with 80% of the job done.**

  ![status](https://img.shields.io/badge/version-v1.0.0-blue)
  ![license](https://img.shields.io/badge/license-MIT-green)
  ![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)
  ![backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.13-3776AB)
  ![frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20Mantine%209-000000)
  ![db](https://img.shields.io/badge/db-PostgreSQL%2016%20%2B%20pgvector-336791)
</div>

> **AI agents** touching this repository: read [`docs/pre-prompt.md`](docs/pre-prompt.md) first. It is the canonical stack and convention contract. Skipping it leads to invented dependencies and bypassed framework primitives — both out of bounds.

---

## What Orbiteus is optimising for

Agentic coding is great at producing diffs. It is weak at **keeping** a large Python + Next codebase aligned on one tenancy model, one RBAC story, one audit trail, and one deployment story. Orbiteus turns those cross-cutting choices into **shared primitives** so human maintainers and **coding agents** converge on the same seams.

The engine is **general-purpose business software infrastructure** — not a single SaaS SKU. You register modules; the registry wires persistence, HTTP surface, admin UI metadata, security, background work, realtime fan-out, and an **agent-safe** AI tool path (BYOK; tools never run above the caller’s permissions).

Concretely, the repo ships:

1. **A module spine** — `registry.register("…")`, repositories, auto-CRUD, view XML, Command Palette actions, and optional `ai.py` declarations so new domain code has obvious landing zones.
2. **Doc-first guardrails** — `docs/pre-prompt.md`, ADRs, and automated tests are treated as part of the contract, not appendix prose.
3. **Production defaults before line one of your domain** — multi-tenant isolation, layered RBAC, audit events, outbox + webhooks, Celery schedules, SSE + Redis backplane, metrics, backups, and CI gates.
4. **A reference CRM slice** — proves list / form / kanban / calendar / graph + realtime + AI tools; copy the pattern for any other vertical.
5. **MIT source you host yourself** — you own the deployment; the framework is not a per-seat tax on your runtime.

---

## Who it is for

- **Engineering leaders** who already adopted agentic IDEs and saw raw speed without a shared architectural spine.
- **Builders shipping internal or customer-facing tools** who want post-demo software: typed APIs, enforced isolation, and operability.
- **Small teams** who need ERP-*grade* controls (tenants, permissions, audit) without renting someone else’s entire product roadmap.

---

## Typical builds on this foundation

Orbiteus is **not** “ERP only”. It is a **neutral substrate** for line-of-business software: you compose modules while the engine keeps the guardrails consistent.

| | |
|---|---|
| **Internal ops** | Line-of-business apps, approvals, master data, and admin surfaces generated from your module definitions. |
| **CRM & pipeline** | Reference module (Person, Lead, Stage, Team) with list, kanban, calendar, graph, and realtime — clone the pattern for your domain. |
| **Headless / API-first** | Typed REST + OpenAPI per registered model for mobile, web, or integrations — same tenancy and rules as the UI. |
| **Partner & field portals** | Share-link access with explicit permissions; separate Next.js portal app with scoped realtime. |
| **Agentic AI on your data model** | Streaming chat, tool registry, dashboard aggregates — always under caller RBAC. |
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

## Where your time goes after clone

The hero line calls out **80% of the job done** on the *plumbing*: identity, tenancy, RBAC, audit, queues, webhooks, realtime, observability, CI, admin renderer, portal pattern, and an agent-aware AI harness. Your calendar should tilt toward **domain tables, workflows, UX, and integrations** — the slice that actually differentiates a business — instead of re-deriving session and permission infrastructure on every greenfield.

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
