# 07 — ADR Index (Decisions This Program Requires)

> Orbiteus binds every architectural decision to an immutable ADR
> (`docs/adr/NNNN-*.md`, template `docs/adr/_template.md`). The CRM 2027 program
> introduces new core primitives and a couple of new dependencies, so it needs
> new ADRs. They are **proposed** here and authored by task **CRM27-01** in
> [`06-task-backlog.md`](./06-task-backlog.md). The existing ADRs run 0001–0018;
> these continue the sequence.
>
> Note: filenames below are written as code spans (not links) on purpose — the
> files don't exist yet, and the docs link-checker (`scripts/check_docs.py`)
> only tolerates links to existing markdown. When CRM27-01 creates them, link
> them from `docs/adr/README.md`.

## Proposed ADRs

### `0019-metadata-engine-hybrid-storage.md`
**Decision.** Introduce a runtime metadata engine with **hybrid storage**: JSONB
(`custom_fields`) by default for custom fields, opt-in materialized columns/tables
for custom objects and integrity-critical fields, via an advisory-locked,
audited, background `MetadataService`.
**Why an ADR.** New core primitive; runtime DDL is a load-bearing, risky
decision. Supersedes the implicit "code-first only" stance.
**Alternatives considered.** Pure JSONB (rejected: weak integrity/perf for custom
objects); schema-per-tenant à la Twenty (rejected: conflicts with shared-schema
`tenant_id` model + audit/RBAC machinery); EAV tables (rejected: query pain).

### `0020-field-type-registry.md`
**Decision.** A pluggable field-type registry (`orbiteus_core/fields/`) where each
type declares storage, schema, validation, widget, filter operators, audit
formatter, and AI serialization.
**Why an ADR.** Cross-cutting primitive touching auto-router, ui-config, widgets,
audit, AI. Locks the extension contract for field types.

### `0021-saved-views-as-core-primitive.md`
**Decision.** Promote `crm.queue` to a core `ir_view` primitive (table/kanban/
calendar/timeline/gallery/graph) with stored filter/sort/group/columns/visibility,
plus a JSON **filter DSL** compiling to existing auto-router operators.
**Why an ADR.** Moves a module concept into core; defines the filter DSL reused by
views, workflow, and AI.

### `0022-timeline-and-chatter-primitive.md`
**Decision.** Add a core `mail.message` (note/comment/log, rich text, mentions,
threading) and a unified timeline aggregating audit + messages + activities +
emails + calendar + workflow per record; plus a `notification` primitive
(in-app realtime + email via outbox).
**Why an ADR.** New core data + cross-cutting timeline; closes the "Activities/
chatter MISSING" gap deliberately rather than ad-hoc.

### `0023-workflow-fsm-postgres.md` (supersedes the deferral in ADR-0015)
**Decision.** Build a **thin Postgres-backed automation/FSM engine**
(`orbiteus_core/workflow/`): trigger → condition (filter DSL) → ordered actions,
executed through the outbox (atomic, retried, dead-lettered) and audited; long
waits via `ir_cron`/Beat. **Not Temporal.**
**Why an ADR.** ADR-0015 deferred a generic engine and excluded Temporal; CRM
2027 needs automation now. This explicitly revisits that decision within the
boring-tech filter (no new heavy dependency).
**Alternatives.** Temporal (rejected again: heavyweight, ADR-0015 rationale
stands), external iPaaS (rejected: lock-in, data egress, audit gap).

### `0024-comms-email-calendar-sync.md`
**Decision.** Add a `modules/comms/` with provider adapters (Gmail OAuth, IMAP/
SMTP, Google Calendar/CalDAV); periodic Celery sync; OAuth tokens encrypted with
a `COMMS_SECRET_KEY` (Fernet pattern from BYOK AI credentials); idempotent,
outbox-retried sync; messages/events matched to records by participant email.
**Why an ADR.** New module + new external integrations + new secret + new
periodic-sync pattern. May introduce vetted libraries (IMAP/Google client) — each
must pass the no-GPL license gate.
**Dependencies to vet.** `google-api-python-client`/`google-auth`,
`imapclient`/stdlib `imaplib`, `caldav` — confirm MIT/Apache/BSD.

### `0025-graphql-gateway-later.md`
**Decision.** Defer GraphQL to a dedicated later wave; when built, generate a
**core schema** (standard objects) and a **metadata schema** (per-tenant custom
objects) from the registry, resolving through `BaseRepository` so RBAC/audit are
inherited. REST + OpenAPI remains the primary contract.
**Why an ADR.** Records the "REST now, GraphQL later" choice and constrains the
eventual implementation (no parallel data path).
**Dependency to vet.** `strawberry-graphql` or `ariadne` (both
schema-first/decorator, async-friendly) — pick in the wave, license-gated.

### `0026-api-keys-and-app-tokens.md`
**Decision.** Add programmatic **API keys** (hashed at rest, scoped per tenant +
role, audited as a distinct actor), enabling apps/integrations and the future
apps ecosystem.
**Why an ADR.** New auth surface alongside JWT/cookie/share-link; security-
sensitive.

### `0027-pdf-report-pipeline.md` (optional, if not folded into a feature PR)
**Decision.** Jinja → PDF pipeline (WeasyPrint or headless Chromium) for quotes
and reports, executed via the outbox.
**Why an ADR.** Was listed as a deferred primitive in `pre-prompt.md`; introduces
a rendering dependency that must be license-vetted and sandboxed.

## ADR authoring checklist (for CRM27-01)

For each ADR above:
- [ ] Use `docs/adr/_template.md`; status `Accepted`.
- [ ] State decision, context, alternatives, consequences.
- [ ] If it adds a dependency, list it and confirm MIT/Apache/BSD (no-GPL gate).
- [ ] Link it from `docs/adr/README.md`.
- [ ] Update `scripts/check_docs.py` `REQUIRED_ADR_IDS` range and
      `docs/pre-prompt.md`/`docs/README.md` doc maps as needed; keep
      `tests/test_docs.py` green.
