# 09 — Non-Functional Requirements

> The quality bar CRM 2027 must clear to credibly claim "best on the market".
> These targets are testable and tie back to the success metrics in
> [`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md). They inherit
> the engine's existing guarantees (see [`../18-security.md`](../18-security.md),
> [`../29-observability.md`](../29-observability.md),
> [`../05-rbac-multitenancy.md`](../05-rbac-multitenancy.md)).

## 1. Performance & scalability

| Metric | Target | Notes |
|---|---|---|
| p95 list/read API | < 200 ms | at 5–10k DAU on a single host (compose + PgBouncer). |
| p95 write API | < 400 ms | excludes async side effects (outbox). |
| Custom-object query (JSONB filter) | < 300 ms | with expression/GIN index on hot fields; materialize if exceeded. |
| Realtime fan-out latency | < 1 s | SSE + Redis pub/sub, tenant-scoped. |
| Email/calendar sync lag | < 5 min | matches Twenty's sync cadence; idempotent. |
| Workflow action latency | < 1 min (non-wait) | via outbox; `wait` actions are explicit. |
| Import throughput | ≥ 10k rows/job | resumable, outbox-backed for large jobs. |
| Scale-out path | documented | single host → k8s per [`../32-multi-host-migration.md`](../32-multi-host-migration.md). |

## 2. Reliability & data integrity

- **At-least-once** delivery for webhooks/automation/notifications via the
  Postgres outbox; bounded exponential backoff; dead-letter visibility.
- **No synchronous third-party calls** in request handlers (email, AI, webhooks
  all go through the outbox/Celery).
- **Atomicity:** business write + its side-effect enqueue commit together or roll
  back together.
- **Idempotency:** sync jobs and imports are idempotent and resumable.
- **Backups + restore drill** (exist) extended to cover new tables; RPO/RTO per
  [`../31-backups-and-dr.md`](../31-backups-and-dr.md).
- **Migrations** are advisory-locked (`pg_try_advisory_lock`); runtime
  materialization uses the same safety.

## 3. Security

- **Multi-tenant isolation** is provable: cross-tenant read/list/write/delete
  return 404 (no existence leak); cross-tenant realtime/topic returns 403 —
  negative tests required for **every new object**, including custom objects.
- **RBAC** mandatory on every path (model access + record rules + actions + AI
  scope + portal scope); add **field-level RBAC** (CRM27-101).
- **AI never bypasses RBAC**: the caller's `RequestContext` is the upper bound;
  no elevated AI context; negative tests on every AI surface.
- **Secrets**: OAuth tokens (comms) and BYOK AI keys encrypted at rest (Fernet);
  API keys hashed; never logged (redaction helper). New secrets
  (`COMMS_SECRET_KEY`) follow the `.env`-only rule.
- **Transport**: CSP/HSTS/security headers (exist); same-origin API proxy.
- **Dependency hygiene**: no-GPL license gate; new deps (comms, GraphQL, PDF)
  must pass it (see [`07-adr-index.md`](./07-adr-index.md)).
- **Threat model** updated per new surface (email ingestion, API keys, custom
  DDL) — extend [`../18-security.md`](../18-security.md).

## 4. Auditability & compliance

- **100% audit**, opt-out-only, per-field diff, with actor (`user`/`ai`/`portal`/
  `system`) — extended to: metadata changes, workflow runs, email/calendar sync,
  imports, merges, API-key use.
- **GDPR**: DSAR export + right-to-erasure tooling, retention policies, audit-log
  retention/partitioning — extend [`../33-data-retention-and-gdpr.md`](../33-data-retention-and-gdpr.md).
- **Data residency**: self-hostable in one command; no mandatory third-party
  egress except user-connected providers (email/calendar/AI BYOK).

## 5. Observability

- Prometheus series (exist, 14 families) extended for: sync lag, workflow
  runs/failures, import jobs, AI tokens by surface, metadata operations.
- Structured JSON logs with `request_id`/`tenant_id`/`user_id`/`actor` on all new
  paths; redaction enforced.
- OpenTelemetry opt-in spans across sync + workflow + AI.

## 6. Usability & accessibility

- **Time-to-first-pipeline < 10 min** (no code): guided onboarding seeds a
  pipeline, stages, and a sample deal.
- **Zero bespoke per-object TSX** — even custom objects render through the engine
  renderer (hard rule preserved).
- **Keyboard-first**: ⌘K everywhere; record navigation; bulk actions.
- **WCAG 2.1 AA** for admin + portal (Mantine baseline + a11y checks in CI).
- **Realtime, optimistic UI** with conflict-safe reconciliation.

## 7. Internationalization

- Message catalogs (complete CRM27-103); locale + timezone per user (fields
  exist on `base.user`); currency per company; remove all Polish string leaks
  from tracked content.

## 8. Testing & CI (the gate stays honest)

- Every task: ≥1 matching test; backend pytest + coverage ≥ engine threshold;
  Vitest for widgets; `next build`; Playwright deterministic subset green;
  env-gated advanced E2E for seeded flows.
- **Negative-test mandate**: cross-tenant isolation + AI-RBAC for every new
  object and surface.
- Docs validator (`scripts/check_docs.py`) green; this folder's cross-links
  resolve.
- New dependencies pass `pip-audit`/`npm audit` + no-GPL license gate.

## 9. Definition of "best on the market" (the scoreboard)

CRM 2027 may claim category leadership when, simultaneously:

1. **Customization** ≥ Twenty (runtime objects/fields/relations/views, no code).
2. **AI** is native and governed (100% audited AI writes; provable RBAC bounds).
3. **Reliability** is outbox-grade (at-least-once, dead-letter, no sync egress).
4. **Trust** is built-in (provable isolation, mandatory audit, GDPR tooling,
   self-host).
5. **Revenue surface** is complete (pipeline → quote → contract + forecasting).
6. **Communications** are two-way and on-record (email + calendar sync).
7. **Performance** meets §1 at target scale.

M1–M3 establish parity-and-better on (1)(2)(3)(4)(6); M4–M5 complete (5) and the
analytics/platform breadth.
