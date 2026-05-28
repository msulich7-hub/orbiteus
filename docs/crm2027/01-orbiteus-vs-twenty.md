# 01 — Orbiteus vs Twenty: Comparison & Feasibility Verdict

> A feature-by-feature and architecture-by-architecture comparison of the
> Orbiteus engine (FastAPI / Python) against Twenty (NestJS / TypeScript), and a
> defended answer to the core question: *can Orbiteus be improved and refactored
> to be close to Twenty — and is it the right base for the best CRM of 2027?*

## 1. The two architectures at a glance

| Axis | **Orbiteus** | **Twenty** |
|---|---|---|
| Language / runtime | Python 3.13, FastAPI | TypeScript, NestJS |
| Frontend | Next.js 16 + React 19 + Mantine 9 | React + Jotai + Linaria |
| DB | PostgreSQL 16 + pgvector | PostgreSQL |
| Cache / queue | Redis + Celery 5 | Redis + BullMQ |
| Monorepo | npm workspaces (admin-ui, portal-ui) | Yarn workspaces / Nx |
| **Data model paradigm** | **Code-first** modules (dataclass + SQLAlchemy mapping) | **Metadata-first** — objects/fields are data, schema generated per workspace |
| Multi-tenancy | Shared schema, `tenant_id` column, repo-enforced filter | Per-workspace schema (schema-per-tenant) |
| API | Auto-CRUD **REST** + OpenAPI | Auto-generated **GraphQL** (+ REST), core + metadata schemas |
| Customization | `custom_fields` JSONB + `ir_model_field` (code/seed), no runtime UI yet | Full runtime no-code object/field/view builder |
| AI | BYOK providers, tool dispatcher under RBAC, embeddings, audited | AI agents + chat (newer, less governance depth) |
| Audit | **Mandatory, 100%, per-field diff, actor=user/ai/portal/system** | Lighter / activity-log oriented |
| RBAC | 5 levels (model access, record rules, actions, AI scopes, portal scope) + Redis cache | Roles + field-level permissions |
| Realtime | SSE + Redis pub/sub, tenant-scoped topics | Subscriptions |
| Reliability | EventBus + **Postgres outbox** + Celery, dead-letter, HMAC webhooks | BullMQ jobs |
| External users | **Dedicated portal-ui** + signed share links | Not a first-class portal |
| Workflow engine | Module-level `AutomationRule` (rules) + cron; generic engine deferred (ADR-0015) | Built-in workflow automation (early stage) |
| Email/calendar sync | Stub (`EmailLog`), no IMAP/Gmail/CalDAV | **Two-way Gmail/IMAP + CalDAV** sync |
| Maturity as CRM | Pipedrive-class sales engine | Broad CRM, strong customization, growing |

## 2. Where Orbiteus already wins

These are not gaps to close — they are advantages to **keep and market**:

1. **Mandatory, complete audit.** Every CRUD, auth event, AI tool call, and
   portal mutation writes `ir_audit_log` with actor + per-field diff. This is
   deeper than Twenty's default and is a genuine enterprise/regulatory edge.
2. **Five-level RBAC with Redis cross-replica cache.** Model access, record
   rules (row-level domains), action gating, AI scopes, and a separate portal
   scope. Proven by cross-tenant negative tests.
3. **AI that obeys RBAC.** The AI tool dispatcher routes provider tool-calls
   through `BaseRepository` — the human's `RequestContext` is the upper bound on
   what the AI can do. No elevated AI context exists. This is the safe-AI story
   most CRMs are still chasing.
4. **Outbox-grade reliability.** Side effects are atomic with the business
   transaction (`ir_outbox`), drained by Celery with exponential backoff and a
   dead-letter path; webhooks are HMAC-signed. Twenty's BullMQ jobs are solid but
   the transactional-outbox guarantee is a differentiator.
5. **A real partner portal.** `portal-ui` + signed share links + portal-scoped
   RBAC + portal realtime. Twenty has no first-class external portal.
6. **Zero-TSX dynamic renderer.** New models render list/form/kanban/calendar/
   graph from view XML + schema introspection without new frontend files.
7. **Self-host in one command**, with prod compose, PgBouncer, nginx/TLS,
   Prometheus metrics, backups + restore drill.

## 3. Where Twenty wins (the gaps we must close)

These are the deltas the program is built to erase (sized in
[`02-gap-analysis.md`](./02-gap-analysis.md)):

1. **Runtime metadata builder (the moat).** End users create objects, fields,
   relations, and views from the UI; the API/UI/permissions regenerate. Orbiteus
   has the *bones* (`ir_model`, `ir_model_field`, `custom_fields`, `is_custom`)
   but no runtime DDL/builder and no UI. **Highest-priority gap.**
2. **Rich field-type system.** Twenty ships emails[], phones[], links[], address,
   full-name, currency, rating, rich-text, actor, relation (m2m/o2m), select/
   multi-select. Orbiteus has a smaller widget set. **High priority.**
3. **Timeline / chatter / notes.** Per-record activity feed, notes (rich text),
   mentions, attachments inline. Orbiteus marks "Activities/chatter MISSING" in
   core; the CRM module has `Activity` but no unified timeline. **High priority.**
4. **Two-way email & calendar sync.** Gmail/IMAP email-in-CRM + CalDAV calendar.
   Orbiteus has only a logging stub. **High priority** (revenue-critical for CRM).
5. **Generic workflow automation.** Twenty has a visual trigger→action builder.
   Orbiteus deferred a generic engine (ADR-0015, no Temporal). **High priority** —
   needs a new ADR for a Postgres-backed FSM/automation engine.
6. **GraphQL API.** Auto-generated, with metadata discovery. Orbiteus is REST.
   Decision: **REST now, GraphQL as an ADR + later wave** (see
   [`07-adr-index.md`](./07-adr-index.md)). Not a blocker for parity.
7. **Apps / extensibility ecosystem + CLI/SDK.** Twenty's `create-twenty-app`,
   private apps. Orbiteus has code modules but no packaged app/SDK story. **Medium.**
8. **CSV import/export, dedup/merge, enrichment.** Orbiteus: import/export
   MISSING. **Medium-high** (every CRM needs import on day one).
9. **Polish of saved views / filters / favorites / command menu.** Orbiteus has
   `Queue` (saved views) and ⌘K, but UX is thinner than Twenty's. **Medium.**

## 4. The fundamental tension — and how we resolve it

The deepest difference is **code-first vs metadata-first**.

- Twenty makes *everything* metadata: even "standard" objects are seeded
  metadata, materialized into a per-workspace schema. This is what enables
  no-code customization and self-regenerating APIs.
- Orbiteus makes *everything* code: modules are Python; `custom_fields` JSONB is
  the escape hatch for runtime additions. This is what enables the strong typed
  guarantees, the audit/RBAC rigor, and AI-agent authorability.

**Resolution (the hybrid, chapter 03):** keep code-first modules as the *engine
and product backbone*, and introduce a **metadata layer** that lets tenants add
custom objects and fields at runtime, materialized through a controlled DDL path
(or JSONB-backed virtual columns) and surfaced through the *same* auto-router,
RBAC, audit, realtime, and AI tool dispatcher. Standard CRM objects stay
code-defined (fast, typed, testable); customer-specific extensions become
metadata. Best of both worlds.

## 5. Feasibility verdict

> **Yes.** Orbiteus can be improved and refactored to match Twenty's
> customization superpower and, on the strengths it already has (audit, RBAC,
> AI-native dispatch, outbox reliability, portal), to *surpass* it as the
> foundation for an AI-first CRM in 2027.

Why this is credible, not optimistic:

- **The hard 80% is already done and tested.** Orbiteus is at v1.0.0-rc1 with
  88/90 DoD checkboxes. The expensive, error-prone substrate (multi-tenancy,
  RBAC, audit, events, outbox, realtime, AI dispatch, deploy) exists and is
  covered by tests. We are adding product surface, not rebuilding foundations.
- **The metadata bones exist.** `ir_model`, `ir_model_field` (with `is_custom`,
  `selection_values`, `related_model`), and `custom_fields` JSONB on every record
  mean the metadata engine is an *extension*, not a from-scratch build.
- **The CRM is already Pipedrive-class.** Pipelines, stages, rotting, lifecycle,
  UTM, scoring, prospects, activities, teams, automation rules, stage history are
  present. We extend, not start.
- **The AI advantage compounds.** Because every object goes through the tool
  dispatcher, every new metadata object/field becomes AI-addressable for free —
  a structural advantage over bolt-on copilots.

### Honest risks (full register in [`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md))

- **Runtime DDL is dangerous** — multi-tenant migrations, lock contention, schema
  drift. Mitigation: ADR for a constrained metadata-object engine (JSONB-first,
  optional materialization), advisory locks, per-tenant guard rails.
- **Email/calendar sync is a swamp** — OAuth, IMAP quirks, dedup, threading.
  Mitigation: scope to Gmail + IMAP + CalDAV in phases; lean on the outbox for
  retries; treat as its own wave.
- **Workflow engine scope creep** — Mitigation: a thin Postgres-backed FSM, not
  Temporal (revisit ADR-0015 with a new ADR), shipped behind a feature flag.
- **Maintaining engine purity** — every addition must respect the hard rules.
  Mitigation: each task in [`06-task-backlog.md`](./06-task-backlog.md) cites the
  primitive it uses and forbids bypasses; CI keeps the guarantees honest.

## 6. Strategic recommendation

Adopt the **hybrid metadata** strategy, keep **REST now / GraphQL later**, and
sequence the program so the customization moat (metadata + field types + views)
lands first, then communications and automation (the revenue-critical CRM
surfaces), then intelligence and analytics, then marketing and the apps
ecosystem. Detailed sequencing: [`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md).
