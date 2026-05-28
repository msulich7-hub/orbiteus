# 03 — Architecture Strategy: The Hybrid Metadata Engine

> How Twenty's runtime-customization superpower grafts onto the Orbiteus engine
> without breaking a single hard rule. This chapter defines the new core
> primitives the program introduces and the contracts they must honor.

## 1. Design tenet

> **Code-first for the platform and the standard CRM. Metadata-first for
> tenant-specific extension.** Both flow through the *same* repository, RBAC,
> audit, realtime, outbox, and AI dispatch.

Standard objects (Organization, Person, Lead, …) stay code-defined: typed, fast,
test-covered. Tenants extend their CRM at runtime — new custom objects, new
fields on standard or custom objects, new views — and those extensions are
served by the *existing* engine machinery, not a parallel stack.

## 2. The metadata layer (new core primitive: `orbiteus_core/metadata/`)

### 2.1 What already exists (reuse, don't reinvent)

- `ir_model` (`IrModel`) — model registry (`model_name`, `label`, `module`).
- `ir_model_field` (`IrModelField`) — field registry with `field_type`,
  `is_custom`, `selection_values`, `related_model`, `required`, `readonly`.
- `custom_fields` JSONB column on **every** `BaseModel` record.
- `ir_ui_view` — view arch storage with XPath inheritance.
- `BaseRepository`, `AutoRouter`, `ui_config`, `view_loader` — all introspect the
  registry today.

### 2.2 What we add

A **MetadataService** that turns runtime metadata changes into live, governed
schema — choosing per field between two storage strategies:

| Strategy | When | How |
|---|---|---|
| **A. JSONB-backed virtual columns** (default) | custom fields on existing/standard objects; low-cardinality; fast to ship | stored in `custom_fields` JSONB; indexed via Postgres expression/GIN indexes on demand; surfaced as first-class fields in `ui_config`, auto-router filters, audit diffs, AI tools |
| **B. Materialized physical columns/tables** (opt-in) | custom *objects*, or custom fields that need FK integrity, uniqueness, heavy filtering/sorting | controlled DDL via `MetadataService.materialize()`, guarded by `pg_try_advisory_lock`, executed in a one-shot migration-style transaction, recorded in `ir_model`/`ir_model_field` |

This **hybrid storage** is the crux: JSONB gives instant, safe customization
(no DDL, no lock risk) for the 90% case; materialization gives relational rigor
where it matters — both presented identically to the rest of the engine.

### 2.3 New `ir_*` tables (proposed)

| Table | Purpose |
|---|---|
| `ir_custom_object` | tenant-scoped custom object definitions (name, label, icon, storage strategy, materialized table name) |
| extend `ir_model_field` | add `storage` (jsonb/column), `default_json`, `widget`, `help`, `group_id`, `is_required_in_stage` |
| `ir_field_group` | logical field groups for record-page layout |
| `ir_relation` | typed relations between objects (m2o/o2m/m2m), join-table metadata for m2m |
| `ir_view` (promote `crm.queue`) | saved views: object, layout (table/kanban/calendar/timeline), filter JSON, sort JSON, group-by, visibility, owner/shared |

All tenant-scoped tables carry `tenant_id` and obey the standard repository
filter. Custom-object *materialized* tables also carry the full base-column set
(`tenant_id`, `company_id`, `custom_fields`, audit attribution) so they inherit
isolation and audit for free.

### 2.4 Hard-rule compliance

The metadata engine **must**:

- Route every read/write through `BaseRepository` (tenant filter + RBAC + audit).
  Custom objects get an auto-generated repository at registration time.
- Emit `ir_audit_log` for metadata changes themselves (creating a field is an
  audited operation, `actor=user`, model=`ir.model.field`).
- Publish realtime + outbox events on custom-object records exactly like
  standard ones (topics `tenant:{t}:model:{custom_model}:record:{id}`).
- Expose custom objects/fields to the AI tool dispatcher automatically, gated by
  the same `accessible_models` / RBAC scoping.
- Never run unbounded `ALTER TABLE` in a request handler. Materialization is a
  background, advisory-locked, idempotent operation (Celery task), surfaced to
  the user as "applying changes…" with realtime completion.

## 3. The field-type system (new: `orbiteus_core/fields/`)

A registry of **field types**, each declaring: storage shape, Pydantic
read/write schema, validation, default widget, filter operators, audit-diff
formatter, and AI serialization. Adding a field type = registering one class; the
auto-router, ui-config, widget registry, and AI dispatcher pick it up.

Launch set (Twenty parity + extras), defined fully in
[`04-data-model.md`](./04-data-model.md): `text`, `long_text`, `rich_text`,
`number`, `integer`, `boolean`, `date`, `datetime`, `select`, `multi_select`,
`email`, `emails`, `phone`, `phones`, `url`, `links`, `address`, `full_name`,
`currency`/`monetary`, `percent`, `rating`, `uuid`, `actor`, `relation`
(m2o/o2m/m2m), `json`, `attachment`, `duration`, `geolocation`, and the derived
types `formula`/`computed` and `rollup`/`aggregate`.

## 4. The view layer (extend `view_loader` + `ui_config`)

- Promote `crm.queue` to a core **`ir_view`** primitive: any object can have
  saved views (table / kanban / calendar / timeline / gallery / graph), each with
  a stored filter, sort, group-by, visible columns, and share scope.
- Add a **filter DSL** (JSON) that compiles to the existing auto-router query
  operators (`__contains`, `__gte`, `__in`, …) so filters are reusable by the
  API, the UI builder, and the AI ("show me deals over 50k closing this month").
- Add a **record-page layout** primitive (field groups + related lists +
  timeline) rendered by the existing dynamic renderer — still zero bespoke TSX
  per object.

## 5. The activity/timeline primitive (new: core `activity` + `timeline`)

A unified **timeline** that aggregates, per record: audit-derived field changes,
notes, comments, tasks/activities, emails, calendar events, and workflow actions.
Backed by:

- Promote chatter to core: `mail_message` (note/comment, rich text, author,
  mentions), reusing `ir_attachment` for files.
- A **timeline view** that reads `ir_audit_log` + `mail_message` + `crm.activity`
  + `crm.email_log` for a `(res_model, res_id)` and renders chronologically.
- `@mention` → in-app notification (new `notification` primitive) + optional email
  via the outbox.

## 6. The workflow engine (new: `orbiteus_core/workflow/`, gated by ADR)

ADR-0015 deferred a generic engine and excluded Temporal. CRM 2027 needs
automation, so we introduce a **thin, Postgres-backed automation/FSM engine** —
*not* Temporal — under a new ADR (see [`07-adr-index.md`](./07-adr-index.md)):

- **Triggers:** record events (created/updated/stage-changed/field-changed), time
  (cron via `ir_cron`), inbound (webhook/email), manual.
- **Conditions:** the same filter DSL as views.
- **Actions:** create/update record, create activity/task, send email
  (template), assign/round-robin, set field, webhook, call AI tool, wait/delay.
- **Execution:** every action is enqueued through the **outbox** (atomic,
  retried, dead-lettered) and **audited**; long waits use `ir_cron`/Beat. No
  synchronous third-party calls in request handlers.
- **Authoring:** stored as JSON (trigger + condition + ordered actions); a visual
  builder is a frontend wave, but the engine is API-first from day one.

This stays within the boring-tech filter (Postgres + Celery + outbox, all
already in the stack) and gives Twenty-parity automation without a new heavy
dependency.

## 7. Communications architecture (new: `modules/comms/`)

- **Email transport** already exists (`orbiteus_core/mail.py`); add
  template-driven send (`ir_mail_template`) + the outbox for delivery.
- **Inbound/sync** as a dedicated module with provider adapters
  (`orbiteus_core/comms/providers/`): **Gmail (OAuth)**, **IMAP/SMTP**,
  **CalDAV/Google Calendar**. Sync runs as periodic Celery tasks; messages are
  matched to records by participant email and logged on the timeline.
- **OAuth tokens** stored encrypted (reuse the Fernet pattern from BYOK AI
  credentials, `AI_SECRET_KEY` → a `COMMS_SECRET_KEY`).
- Treat sync as eventually-consistent, idempotent, and outbox-retried.

## 8. API strategy: REST now, GraphQL later

- **Now:** the existing auto-CRUD REST + OpenAPI covers standard *and* custom
  objects (the auto-router reads the registry, so custom objects are free).
- **Later (ADR + dedicated wave):** a **GraphQL gateway** generated from the same
  metadata registry — a *core* schema (standard objects) and a *metadata* schema
  (per-tenant custom objects), mirroring Twenty. It reuses `BaseRepository`, so
  RBAC/audit are inherited. Until then, REST is the contract; GraphQL is additive,
  never a rewrite.
- **API keys** (new): programmatic access tokens scoped per tenant + role, for
  apps/integrations, audited like any actor.

## 9. AI architecture (widen the existing lead)

The AI dispatcher already routes provider tool-calls through `BaseRepository`.
CRM 2027 widens it:

- **Auto-expose metadata:** every custom object/field becomes an AI-addressable
  query/action tool automatically (gated by `accessible_models` + RBAC).
- **Finish embeddings/retrieval:** wire `ir_embedding` refresh via the outbox and
  expose `semantic_search(model, query)` as a first-class tool.
- **NL → report:** complete `/api/ai/dashboard` (NL → aggregate spec → recharts),
  and add NL → saved-view/filter.
- **Workflow actions can call AI tools** (e.g. "on new deal, summarize the
  account and draft a follow-up email") — under the rule owner's RBAC.
- **Copilot surfaces:** record-page copilot, list copilot ("clean up these
  duplicates"), and a global assistant — all the same governed dispatcher.

## 10. What does *not* change (the load-bearing walls)

- `BaseRepository` is still the only path to data.
- Multi-tenancy (`tenant_id`) and RBAC are still mandatory and unbypassed.
- Audit is still 100% and opt-out-only.
- Outbox is still the only way to do side effects after a transaction.
- Realtime is still SSE + Redis pub/sub, tenant-scoped.
- The admin UI is still a renderer — **zero bespoke TSX per object**, even custom
  ones (the metadata engine feeds the same renderer).
- Boring-tech filter still governs dependencies (new ones need ADRs).

## 11. Dependency / sequencing implications

The metadata engine (§2) and field types (§3) are the **foundation** for almost
everything user-facing; they ship first. The view layer (§4) and timeline (§5)
ride on them. Communications (§7) and workflow (§6) are independent XL tracks that
can parallelize once the metadata foundation is stable. GraphQL (§8) is last and
optional for parity. The concrete order is in
[`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md).
