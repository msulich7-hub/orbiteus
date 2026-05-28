# 06 — Task Backlog (Waves & Tasks)

> The executable plan. Tasks are grouped into **waves** (dependency-ordered, like
> [`../36-development-plan.md`](../36-development-plan.md)). Each task has a stable
> ID `CRM27-<NN>`, an epic, a size, dependencies, a Definition of Done, required
> tests, and any ADR it needs. Every task obeys the engine hard rules
> ([`../pre-prompt.md`](../pre-prompt.md)) — it names the primitive it uses and
> forbids bypasses.

**Global per-task DoD (applies to all):** routes/data go through
`BaseRepository`; tenant isolation + RBAC enforced; audit emitted; side effects
via outbox; docs updated in the same PR; CI green (pytest + cov ≥ engine
threshold, Vitest, `next build`, Playwright deterministic subset); no new runtime
dep without an ADR; no bespoke per-object TSX.

Status values: `TODO` (default for all here).

---

## Wave 0 — Foundations & decisions (unblocks everything)

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-01 | Write ADRs: metadata engine, field-type registry, workflow FSM (supersede ADR-0015 deferral), GraphQL-later, comms providers, API keys | E-PLAT | M | — | ADRs merged in `docs/adr/` per `_template.md`; linked from `adr/README.md`; `check_docs.py` green. See [`07-adr-index.md`](./07-adr-index.md). |
| CRM27-02 | Field-type registry skeleton (`orbiteus_core/fields/`): base class + register hook; port existing types (text/number/bool/email/select/many2one/monetary/tags) | E-FIELD | M | 01 | Existing models render unchanged via registry; unit tests per ported type; ui-config emits type metadata. |
| CRM27-03 | Filter DSL (JSON → auto-router operators) shared by views/workflow/AI | E-VIEW | M | — | `tests/test_filter_dsl.py`: DSL compiles to existing operators; tenant-scoped; rejects unknown fields. |

---

## Wave 1 — Metadata engine (the moat)

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-10 | `ir_custom_object` + extend `ir_model_field` (`storage`, `widget`, `default_json`, `group_id`, `help`); migrations | E-META | M | 01 | Migration + advisory lock; audit on metadata mutations; tests for schema. |
| CRM27-11 | `MetadataService`: create/edit custom field (JSONB storage) on any object; live in ui-config + auto-router filters + audit + AI | E-META | L | 02,10 | Add field via service → appears in REST, ui-config, audit diff, AI tool; `tests/test_metadata_jsonb_field.py`. |
| CRM27-12 | Custom **object** creation with materialized table (advisory-locked, background Celery, idempotent) + auto repository/router | E-META | XL | 11 | Create object → physical table with base columns; CRUD via auto-router; tenant isolation negative test; realtime + audit on its records. |
| CRM27-13 | `ir_relation` + relation builder (m2o/o2m/m2m incl. join table) | E-META | L | 12 | Relations queryable + expandable (`?expand=`); m2m join metadata; tests. |
| CRM27-14 | Admin-UI metadata builder (objects/fields/relations) — driven by renderer, zero bespoke per-object TSX | E-META | L | 11,12,13 | UI creates object+fields+relation; Playwright happy-path (env-gated); a11y pass. |
| CRM27-15 | Optional materialization of a JSONB custom field → column (online, backfill, advisory-locked) | E-META | M | 11 | Migrate field storage with zero data loss; rollback path; test. |

---

## Wave 2 — Field types & views

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-20 | Implement composite field types: `emails`, `phones`, `links`, `address`, `full_name`, `rating`, `percent`, `duration`, `multi_select`, `actor` | E-FIELD | L | 02 | Each: schema+validation+widget+filter+audit+AI; Vitest per widget; `tests/test_field_types.py`. |
| CRM27-21 | `rich_text` type + sanitizer + RichEditor widget (admin + portal copy) | E-FIELD | M | 02 | Stored sanitized; renders; mention-ready; tests. |
| CRM27-22 | Promote `crm.queue` → core `ir_view`; saved views (filter/sort/group/columns/visibility) | E-VIEW | M | 03 | Migrate rows; CRUD; per-object views; `tests/test_saved_views.py`. |
| CRM27-23 | Advanced filter builder UI (filter DSL) | E-VIEW | M | 03,22 | Build/save filter; reused by table/kanban; Vitest. |
| CRM27-24 | Table view upgrades: inline edit, column resize/reorder/pin, multi-sort, group-by | E-VIEW | M | 22 | Vitest + Playwright env-gated; realtime-safe. |
| CRM27-25 | Finish calendar + graph views; wire to view types | E-VIEW | S | 22 | Calendar from datetime field; graph from aggregate; tests. |
| CRM27-26 | Record detail page: field groups + related lists + inline timeline slot | E-VIEW | M | 13,40 | Renderer-driven; zero bespoke TSX; Vitest. |
| CRM27-27 | Favorites, recently-viewed, enhanced ⌘K (records + recents + AI ask) | E-VIEW | S | 22 | Per-user; realtime; tests. |
| CRM27-28 | Bulk actions (multi-select: assign/tag/delete/export/run-workflow) | E-VIEW | M | 22 | RBAC-checked per row; audited; tests. |

---

## Wave 3 — Activities, timeline & collaboration

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-40 | Core `mail.message` (note/comment, rich text, author, threading, mentions) + `ir_attachment` link | E-ACT | M | 21 | CRUD via repo; audited; realtime; `tests/test_mail_message.py`. |
| CRM27-41 | Unified **timeline** view (audit + mail.message + activity + email + calendar + workflow) for `(res_model,res_id)` | E-ACT | L | 40 | Chronological aggregation; tenant-scoped; tests; renders on record page. |
| CRM27-42 | `notification` primitive: in-app (realtime) + email (outbox); mentions/assignments/reminders | E-ACT | M | 40 | Delivery both channels; read state; tests. |
| CRM27-43 | Promote `crm.activity` to tasks/events: reminders, priority, recurrence, participants | E-ACT | M | — | Reminder fires via ir_cron→notification; tests. |
| CRM27-44 | Admin-UI attachment drag-drop upload (finish `ir_attachment`) | E-ACT | M | — | Upload/download; size/type guard; portal parity; tests. |

---

## Wave 4 — Communications

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-50 | Finish template-driven email send (`ir_mail_template`) via SMTP + outbox | E-COMMS | M | — | Render+send via outbox; retries; audited; `tests/test_mail_template_send.py`. |
| CRM27-51 | `modules/comms/`: `email_message`/`email_thread`/`mailbox` objects (promote `crm.email_log`) | E-COMMS | M | 40 | Dual-write migration; timeline integration; tests. |
| CRM27-52 | IMAP/SMTP mailbox connect + periodic sync (Celery) + encrypted tokens (`COMMS_SECRET_KEY`) | E-COMMS | L | 51 | Idempotent sync; match-to-record by email; outbox-retried; tests with mock IMAP. |
| CRM27-53 | Gmail OAuth two-way sync adapter | E-COMMS | XL | 52 | OAuth flow; send+receive; threading; tests with mocked Google API. |
| CRM27-54 | Calendar sync: `comms.calendar`/`calendar_event` + Google + CalDAV adapters | E-COMMS | L | 52 | Events on records; recurrence; tests with mocks. |
| CRM27-55 | Inbox surface (admin UI) + reply/compose with templates | E-COMMS | M | 53 | Renderer-driven; Vitest/Playwright env-gated. |

---

## Wave 5 — Workflow & automation

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-60 | Workflow engine core (`orbiteus_core/workflow/`): Postgres FSM, trigger→condition→actions, outbox-driven, audited | E-FLOW | XL | 01,03 | Actions atomic+retried+dead-lettered; `workflow.run` log; `tests/test_workflow_engine.py`. |
| CRM27-61 | Promote `crm.automation_rule` → `workflow.automation`; migrate rule JSON | E-FLOW | M | 60 | Migration; existing rules run on new engine; tests. |
| CRM27-62 | Action library: create/update record, activity/task, email template, assign, set field, webhook, AI tool, wait | E-FLOW | L | 60 | Each action unit-tested; RBAC-scoped to rule owner; audited. |
| CRM27-63 | Assignment rules + round-robin; lead/deal scoring engine (recompute via outbox) | E-FLOW | M | 60 | Deterministic assignment; score writes; tests. |
| CRM27-64 | Visual workflow builder (admin UI) | E-FLOW | L | 60,62 | Build+save+activate rule from UI; Playwright env-gated. |

---

## Wave 6 — Revenue: products, quotes, forecasting

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-70 | `crm.product` + `crm.price_book` + `crm.price_book_entry` | E-CPQ | M | 20 | CRUD; tenant-scoped; tests. |
| CRM27-71 | `crm.quote` + `crm.quote_line` with rollup totals; numbering via `ir_sequence` | E-CPQ | M | 70 | Totals computed; status flow; tests. |
| CRM27-72 | PDF pipeline (Jinja → PDF) + quote PDF + send/accept tracking | E-CPQ | M | 71,50 | PDF rendered, attached, emailed via outbox; tests (golden PDF/text). |
| CRM27-73 | Forecasting: weighted pipeline, forecast board, slippage, velocity | E-PIPE | M | 22 | Aggregate-backed; `ir_view` board; tests. |
| CRM27-74 | `crm.contract`/`subscription` + MRR/ARR + renewal tracking (later) | E-CPQ | L | 71 | CRUD; renewal cron→notification; tests. |

---

## Wave 7 — Analytics & data ops

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-80 | `analytics.dashboard` + `analytics.widget`; composable dashboard UI (recharts) | E-ANALYTICS | L | 03 | Widgets from aggregate/filter DSL; saved/shared; tests. |
| CRM27-81 | `analytics.report` saved + scheduled (CSV/PDF via outbox + ir_cron) | E-ANALYTICS | M | 72,80 | Scheduled delivery; tests. |
| CRM27-82 | `crm.goal` quotas/targets with actual-vs-target rollups | E-ANALYTICS | M | 80 | Rollup correctness; tests. |
| CRM27-83 | Generic CSV/Excel **import** engine (`ir_import`): mapping, preview, validate, rollback, resumable | E-DATA | M | 20 | 10k-row import test; failure reporting; outbox for large jobs. |
| CRM27-84 | Generic **export** (any view → CSV/Excel) | E-DATA | S | 22 | Respects filter/columns/RBAC; tests. |
| CRM27-85 | Dedup/merge (rule + AI-suggested) for person/organization | E-DATA | M | 83 | Merge preserves relations + timeline; audited; tests. |
| CRM27-86 | Migration importers (Twenty/Pipedrive/HubSpot CSV templates) | E-DATA | M | 83 | Sample dataset imports cleanly; docs. |

---

## Wave 8 — Intelligence (widen AI)

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-90 | Finish embeddings refresh (outbox) + `semantic_search` tool | E-AI | M | — | Retrieval ranks; refresh on write; `tests/test_semantic_search.py`. |
| CRM27-91 | Finish NL → report/dashboard (`/api/ai/dashboard`) + NL → saved view | E-AI | M | 80 | NL produces valid widget/view spec; re-run under RBAC; tests. |
| CRM27-92 | Auto-expose all metadata objects/fields as AI tools | E-AI | M | 12 | Custom object callable by copilot under RBAC; negative tests. |
| CRM27-93 | AI enrichment / summarize / next-best-action / draft email & quote | E-AI | L | 41,53,71 | Each gated, budgeted, audited `actor=ai`; tests. |
| CRM27-94 | AI dedup suggestions feeding CRM27-85 | E-AI | S | 85 | Suggestions auditable; human-confirm; tests. |
| CRM27-95 | Copilot surfaces: record-level + list-level + global | E-AI | M | 26 | RBAC negative tests; Playwright env-gated. |

---

## Wave 9 — Platform, governance & ecosystem

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-100 | API keys (programmatic, scoped per tenant+role, hashed, audited) | E-PLAT | S | — | Auth via key; scope enforced; revoke; tests. |
| CRM27-101 | Field-level RBAC (read/write masks) + UI binding | E-PLAT | M | 02 | Masked fields hidden in API/UI/AI; negative tests. |
| CRM27-102 | Multi-company switch UX (home shell + scope badge) | E-PLAT | S | — | Company filter applied; tests. |
| CRM27-103 | i18n completion: message catalogs; remove Polish leaks | E-PLAT | S | — | EN baseline; locale switch; `check_docs`/lint clean. |
| CRM27-104 | Webhook subscription management UI | E-PLAT | S | — | CRUD per-event; test delivery; tests. |
| CRM27-105 | Portal extensions: quote acceptance + deal rooms + scoped realtime | E-PORTAL | M | 72 | Portal RBAC scope; negative tests. |
| CRM27-106 | GDPR DSAR + retention tooling (extend existing) | E-PLAT | M | — | Export/erase by subject; retention jobs; tests. |
| CRM27-107 | **GraphQL gateway** (core + metadata schemas) over `BaseRepository` | E-PLAT | XL | 12 | Parity subset of REST; RBAC/audit inherited; tests; ADR. |
| CRM27-108 | Apps / SDK / CLI: package a module as installable app; private apps | E-APPS | XL | 12 | Scaffold + install flow; sandboxed; docs; tests. |
| CRM27-109 | Mobile / PWA shell | E-PLAT | L | 26 | Offline-aware list/record; install prompt; tests. |

---

## Wave 10 — Marketing (later)

| ID | Task | Epic | Size | Deps | DoD / Tests |
|---|---|---|---|---|---|
| CRM27-120 | `crm.campaign` + `crm.segment` + `crm.source` | E-MKT | L | 80 | Attribution to deals; tests. |
| CRM27-121 | Web forms / lead capture → prospect inbox | E-MKT | M | 60 | Public form → prospect; spam guard; tests. |
| CRM27-122 | Email sequences / cadences | E-MKT | L | 53,60 | Multi-step nurture; unsubscribe; tests. |

---

## Backlog hygiene rules

1. **No task ships without tests + docs** (engine rule).
2. **Wave gates:** a wave closes only when all its tasks are DONE + its DoD
   slice is reflected in a CRM2027 inventory ledger (mirror of
   [`../34-inventory-and-status.md`](../34-inventory-and-status.md)).
3. **One ADR per new primitive/dependency** before its implementing task starts.
4. **Each task < ~1500 line diff** where possible; split if larger.
5. **Anything off-plan** goes to [`../28-open-questions.md`](../28-open-questions.md),
   not into a task silently.

Sequencing and milestones across waves: [`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md).
