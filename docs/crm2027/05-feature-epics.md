# 05 — Feature Epics (The Encyclopedia)

> Every capability of CRM 2027, organized into epics under the ten product
> pillars from [`00-vision-and-positioning.md`](./00-vision-and-positioning.md).
> Each epic states intent, key features, the Orbiteus primitives it builds on,
> acceptance signals, and AI hooks. Tasks that realize these epics are in
> [`06-task-backlog.md`](./06-task-backlog.md).

Epic ID convention: `E-<DOMAIN>`. Sizes (S/M/L/XL) per
[`02-gap-analysis.md`](./02-gap-analysis.md).

---

## E-META — Metadata & customization engine **(XL, foundational)**

**Intent.** Let tenants build their own objects, fields, and relations at
runtime, no code — Twenty's moat — served by the existing engine.

**Features.**
- Custom object builder (name, icon, label, storage strategy).
- Custom field builder for any object (all field types from
  [`04-data-model.md`](./04-data-model.md)), JSONB-default with opt-in
  materialization.
- Relation builder (m2o / o2m / m2m) with `ir_relation` metadata.
- Field groups + record-page layout editor.
- Safe runtime DDL via advisory-locked, audited, background `MetadataService`.
- Automatic API (REST), UI (renderer), RBAC, audit, realtime, and AI exposure
  for every new object/field — zero redeploy, zero bespoke TSX.

**Builds on.** `ir_model`, `ir_model_field`, `custom_fields` JSONB, `AutoRouter`,
`ui_config`, `BaseRepository`, audit, outbox.

**Acceptance signals.** A user adds an object + 3 fields + a relation in the UI;
within seconds it is queryable via `/api/<tenant-module>/<object>`, renders a
table/form, appears in the audit log, emits realtime events, and is callable by
the AI copilot — all under their RBAC.

**AI hooks.** New objects auto-register as AI query/action tools; copilot can
even *propose* schema ("add a `renewal_date` field to Account").

---

## E-FIELD — Rich field-type system **(L, foundational)**

**Intent.** Match/exceed Twenty's field palette.

**Features.** Implement the full type registry (ch. 04 §1): emails[], phones[],
links, address, full_name, currency, percent, rating, actor, relation,
multi_select, rich_text, duration, geolocation, plus derived formula & rollup
(later). Each type ships: schema, validation, widget (admin + portal), filter
operators, audit formatter, AI serialization.

**Builds on.** `ui_config`, widget registry (`orbiteus-ui/widgets`), auto-router
query operators.

**Acceptance signals.** Every type renders in list + form + filter; round-trips
through audit diffs; is filterable in the view builder; is serialized for AI.

---

## E-VIEW — Records, views & navigation **(L)**

**Intent.** Best-in-class data browsing and record work.

**Features.**
- Views: table (inline edit, resize/reorder/pin columns), kanban (group-by any
  select/relation), calendar, timeline, gallery, graph.
- **Saved views** (`ir_view`): per object, shared/private, with stored filter +
  sort + group-by + visible columns.
- **Advanced filter builder** (filter DSL → auto-router operators).
- **Multi-column sort**, **group-by** on table.
- **Record detail page**: field groups, related lists, inline timeline, copilot.
- **Bulk actions** on multi-select (assign, tag, delete, run workflow, export).
- **Favorites / pins**, **recently viewed**, enhanced **⌘K** (records + actions
  + recents + AI ask).
- Per-record realtime presence ("Anna is viewing").

**Builds on.** Dynamic renderer, `crm.queue`→`ir_view`, realtime, aggregate
endpoint, filter DSL.

**Acceptance signals.** A rep saves "My hot deals closing this month" as a kanban
view, shares it with the team, bulk-assigns 10 deals, and pins it — all without
a page reload, reflected in realtime.

---

## E-PIPE — Pipeline & revenue **(M, mostly exists)**

**Intent.** Keep the Pipedrive-class engine; add forecasting.

**Features.** Multi-pipeline, stages, rotting, stage history, prospect→deal
conversion (all exist). Add: **weighted forecasting** (by stage probability and
close date), forecast board (commit/best-case/pipeline), close-date slippage,
win/loss analytics, deal age & velocity.

**Builds on.** Existing CRM module, aggregate endpoint, `ir_view`.

**AI hooks.** "What's my forecast for Q3?", "Which deals are slipping?"

---

## E-CPQ — Products, quotes & contracts **(L)**

**Intent.** Turn deals into priced, sendable quotes and signed contracts.

**Features.** Product catalog, price books/entries, quote builder with line items
(qty, discount, tax, rollup totals), quote PDF (Jinja → PDF), send + accept
tracking, convert quote → contract/subscription with MRR/ARR + renewal tracking.

**Builds on.** New CRM objects (ch. 04 §2.2), `ir_sequence`, outbox (send),
PDF pipeline (new), `ir_mail_template`.

**AI hooks.** "Draft a quote for this deal with our standard package."

---

## E-ACT — Activities, notes & collaboration **(L)**

**Intent.** A living record — every interaction in one timeline.

**Features.**
- Unified **timeline/chatter** per record (audit changes + notes + comments +
  tasks + emails + calendar + workflow actions, chronological).
- **Notes** (rich text), **comments** (threaded), **@mentions**, **tasks** with
  due dates, priorities, reminders, recurrence.
- **Attachments** drag-drop (finish admin UI).
- **Notifications** (in-app realtime + email via outbox) for mentions,
  assignments, reminders, SLA breaches.

**Builds on.** New `mail.message`, `notification` primitives, `ir_attachment`,
`crm.activity`, realtime, outbox, `ir_audit_log` (as a timeline source).

**AI hooks.** "Summarize the last 5 interactions with this account."

---

## E-COMMS — Email & calendar **(XL)**

**Intent.** The CRM is the inbox: two-way email + calendar, logged on records.

**Features.**
- **Email send** (template-driven, tracked) via SMTP + outbox.
- **Two-way Gmail sync** (OAuth), **IMAP/SMTP** mailbox connect.
- **Calendar sync** (Google + CalDAV), events on records.
- Auto-match messages/events to records by participant email.
- Inbox surface, templates, basic sequences/cadences (later wave).

**Builds on.** New `modules/comms/`, provider adapters, encrypted OAuth tokens
(Fernet pattern), Celery periodic sync, outbox, timeline.

**Acceptance signals.** Connect Gmail; emails to/from a contact appear on their
timeline within the sync window; sending from CRM logs the message; a meeting
created in Google appears as a calendar event linked to the deal.

**AI hooks.** "Draft a reply", "Find the email where they mentioned pricing."

---

## E-FLOW — Workflow & automation **(XL)**

**Intent.** Twenty-parity automation, Orbiteus-grade reliability.

**Features.** Trigger (record event / time / inbound / manual) → condition
(filter DSL) → ordered actions (create/update, activity/task, email, assign/
round-robin, set field, webhook, AI tool, wait). Visual builder (frontend wave).
Assignment rules, scoring engine, SLAs/escalations (later). Every action atomic
via outbox, retried, dead-lettered, audited; `workflow.run` execution log.

**Builds on.** New `orbiteus_core/workflow/` (Postgres FSM, new ADR superseding
ADR-0015's deferral), outbox, `ir_cron`/Beat, filter DSL, AI dispatcher.

**Acceptance signals.** "When a deal enters 'Proposal', create a follow-up task,
notify the owner, and email the template" runs reliably, is retried on failure,
and shows in the audit log + run log.

**AI hooks.** Actions can invoke AI tools; copilot can author rules from NL.

---

## E-AI — Intelligence & copilot **(L, widen existing lead)**

**Intent.** The copilot is the command line; AI is native, governed, audited.

**Features.**
- Copilot surfaces: global, list-level, record-level.
- NL CRUD across all objects (incl. custom) under RBAC, audited `actor=ai`.
- **Semantic search** (finish `ir_embedding` refresh + retrieval).
- **NL → report/dashboard** (finish `/api/ai/dashboard`), NL → saved view.
- **Enrichment** (company/contact data), **summarize**, **next-best-action**,
  **AI dedup suggestions**, **draft email/quote**.
- Budget guard + PII redaction (exist) extended to new surfaces.

**Builds on.** AI dispatcher, tool registry, pgvector, aggregate endpoint,
metadata auto-exposure.

**Acceptance signals.** Negative tests prove the copilot cannot read/write
outside the caller's RBAC; every AI write is audited.

---

## E-ANALYTICS — Dashboards, reports & goals **(L)**

**Intent.** Decisions from data, no spreadsheets.

**Features.** Composable dashboards (KPI/bar/line/pie/table/funnel widgets from
the aggregate + filter DSL), saved & scheduled reports (CSV/PDF via outbox +
`ir_cron`), forecasting board, goals/quotas with actual-vs-target rollups,
win/loss & activity analytics.

**Builds on.** Aggregate endpoint, `analytics.*` objects, PDF pipeline, outbox,
recharts (`AIDashboard` foundation).

**AI hooks.** NL → dashboard widget; "explain this dip".

---

## E-DATA — Import, export, dedup & migration **(M)**

**Intent.** Day-one data onboarding and hygiene.

**Features.** CSV/Excel **import** with field mapping + validation + preview +
rollback (generic `ir_import` engine), generic **export** (CSV/Excel) of any
view, **dedup/merge** (rule + AI-suggested) for person/organization, migration
importers (from Twenty, Pipedrive, HubSpot CSV) as templates.

**Builds on.** `BaseRepository`, outbox (large jobs), filter DSL, field types.

**Acceptance signals.** Import 10k contacts with a saved mapping; dupes flagged;
a failed row reports cleanly and the job is resumable.

---

## E-MKT — Marketing **(L, later waves)**

**Intent.** Close the HubSpot gap incrementally.

**Features.** Campaigns + UTM attribution (UTM already on lead/prospect),
segments (saved filters as audiences), web forms / lead capture → prospect inbox,
email sequences/cadences, landing-page embeds.

**Builds on.** `crm.campaign`/`crm.segment`/`crm.source`, comms, workflow, forms.

---

## E-PLAT — Platform, API & governance **(XL across items)**

**Intent.** Make CRM 2027 a platform, not just an app.

**Features.**
- **API keys** (programmatic, scoped, audited).
- **GraphQL gateway** (core + metadata schemas) — later wave + ADR.
- Webhooks subscription UI (exists; add management surface).
- **Field-level RBAC**, **multi-company switch UX**.
- **i18n** completion (message catalogs; remove Polish leaks).
- **Apps / SDK / CLI** ecosystem (later) — package a module as an installable
  app; private apps per tenant.
- **Mobile / PWA** (later).
- Audit retention + GDPR DSAR tooling (extend existing).

**Builds on.** Auth, RBAC, registry, metadata engine, outbox, OpenAPI.

---

## E-PORTAL — External portal **(M, advantage to extend)**

**Intent.** Keep and grow the differentiator Twenty lacks.

**Features.** Customer/partner portal (exists) — extend to: quote acceptance,
shared deal rooms, ticket/comment threads, document sharing, scoped realtime.

**Builds on.** `portal-ui`, share links, portal RBAC scope, comms, CPQ.

---

## Epic → pillar map

| Pillar | Epics |
|---|---|
| Model | E-META, E-FIELD |
| Records & Views | E-VIEW |
| Pipeline & Revenue | E-PIPE, E-CPQ |
| Activities & Collaboration | E-ACT |
| Communications | E-COMMS |
| Automation | E-FLOW |
| Intelligence | E-AI |
| Analytics | E-ANALYTICS |
| Marketing | E-MKT |
| Platform | E-PLAT, E-DATA, E-PORTAL |
