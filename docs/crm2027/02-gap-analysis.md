# 02 — Gap Analysis: Keep / Add / Refactor

> The capability matrix that drives the backlog. Each row states the current
> Orbiteus status, the Twenty reference, the decision, and a T-shirt size.
> Effort sizes: **S** (≤1 wk), **M** (1–2 wk), **L** (2–4 wk), **XL** (4+ wk),
> for one senior engineer (or an AI agent + reviewer) per row.

Legend for **Current**: DONE / PARTIAL / STUB / MISSING (same scale as
[`../34-inventory-and-status.md`](../34-inventory-and-status.md)).

## 1. Platform & engine primitives

| Capability | Current (Orbiteus) | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| Multi-tenancy isolation | DONE (tenant_id + tests) | schema-per-tenant | **Keep** | — | — |
| RBAC (5 levels) | DONE | roles + field perms | **Keep**; add field-level RBAC | M | E-PLAT |
| Mandatory audit | DONE | lighter | **Keep** (advantage) | — | — |
| EventBus + outbox + Celery | DONE | BullMQ | **Keep** | — | — |
| Realtime SSE + pub/sub | DONE | subscriptions | **Keep**; add per-record presence | S | E-VIEW |
| **Runtime metadata builder (custom objects)** | STUB (ir_model/ir_model_field exist, no runtime DDL/UI) | DONE (the moat) | **Add (core primitive)** | XL | E-META |
| **Custom fields at runtime (UI)** | STUB (custom_fields JSONB + is_custom flag) | DONE | **Add** | L | E-META |
| Rich field-type system | PARTIAL (text/number/bool/email/select/many2one/monetary/tags) | DONE (email[]/phone[]/links/address/full-name/rating/rich-text/actor/relation) | **Add** | L | E-FIELD |
| REST auto-CRUD + OpenAPI | DONE | yes | **Keep** | — | — |
| **GraphQL API** | MISSING | DONE | **Add later (ADR + wave)** | XL | E-PLAT |
| Webhooks (signed, retried) | DONE | yes | **Keep**; add per-event subscriptions UI | S | E-PLAT |
| **API keys (programmatic)** | MISSING (JWT/cookie only) | DONE | **Add** | S | E-PLAT |
| **CSV/Excel import** | MISSING | DONE | **Add** | M | E-DATA |
| **Export (CSV/Excel)** | PARTIAL (per-model single-shot) | DONE | **Add (generic)** | S | E-DATA |
| **Dedup / merge** | MISSING | partial | **Add** | M | E-DATA |
| Field-level RBAC | MISSING (model + record-rule) | DONE | **Add** | M | E-PLAT |
| Multi-company switch UX | PARTIAL (endpoint exists) | n/a | **Add** | S | E-PLAT |
| **Apps / SDK / CLI** | MISSING (code modules only) | DONE (`create-twenty-app`) | **Add later** | XL | E-APPS |
| i18n (message catalogs) | PARTIAL (some Polish leaks) | DONE (Lingui) | **Finish** | S | E-PLAT |
| Self-host one-command | DONE | DONE | **Keep** | — | — |
| Mobile / PWA | MISSING | partial | **Add later** | L | E-PLAT |

## 2. Records, views & navigation

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| Table (list) view | DONE | DONE | **Keep**; add inline edit, column resize/reorder, pin | M | E-VIEW |
| Kanban view | DONE (drag, optimistic) | DONE | **Keep**; group-by any select/relation | S | E-VIEW |
| Calendar view | PARTIAL | DONE | **Finish** | S | E-VIEW |
| Graph/aggregate view | PARTIAL | n/a | **Finish** | S | E-VIEW |
| **Record detail page** (rich, side panel) | PARTIAL (form) | DONE | **Add** (record page layout) | M | E-VIEW |
| **Saved views** (per object, shared) | PARTIAL (`crm.queue`) | DONE | **Promote to core + UI** | M | E-VIEW |
| **Filters / advanced filter builder** | PARTIAL (query operators) | DONE | **Add UI** | M | E-VIEW |
| **Sorts (multi-column)** | PARTIAL | DONE | **Add UI** | S | E-VIEW |
| **Group by** | PARTIAL (kanban) | DONE | **Add to table** | S | E-VIEW |
| **Favorites / pins** | MISSING | DONE | **Add** | S | E-VIEW |
| **Recently viewed** | MISSING | DONE | **Add** | S | E-VIEW |
| **Global search (cmd menu)** | DONE (⌘K) | DONE | **Keep**; add record search + recents | S | E-VIEW |
| **Bulk actions** (multi-select) | MISSING | DONE | **Add** | M | E-VIEW |
| Gallery/board view | MISSING | DONE | **Add later** | S | E-VIEW |

## 3. Pipeline & revenue

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| Pipelines / stages | DONE | DONE | **Keep** | — | E-PIPE |
| Deals (Lead) + lifecycle + UTM + score | DONE | partial | **Keep** (advantage) | — | E-PIPE |
| Rotting + stage history | DONE | partial | **Keep** | — | E-PIPE |
| Prospect inbox → convert | DONE | n/a | **Keep** | — | E-PIPE |
| **Forecasting** (weighted, time-phased) | MISSING | partial | **Add** | M | E-PIPE |
| **Goals / quotas / targets** | MISSING | n/a | **Add** | M | E-ANALYTICS |
| **Products / catalog** | MISSING (inventory.product exists, separate) | partial | **Add CRM product/pricebook** | M | E-CPQ |
| **Quotes / proposals / CPQ** | MISSING | n/a | **Add** | L | E-CPQ |
| **Contracts / subscriptions** | MISSING | n/a | **Add later** | L | E-CPQ |
| **Line items** | MISSING | n/a | **Add** | M | E-CPQ |

## 4. Activities & collaboration

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| Activities (call/meeting/task/note) | DONE | DONE | **Keep**; unify into timeline | S | E-ACT |
| **Timeline / chatter** (per-record feed) | MISSING | DONE | **Add (core primitive)** | L | E-ACT |
| **Notes** (rich text) | PARTIAL (`Activity.notes` text) | DONE | **Add rich-text note object** | M | E-ACT |
| **Tasks** (assignable, due, reminders) | PARTIAL (`Activity`) | DONE | **Promote + reminders** | M | E-ACT |
| **Mentions (@user)** | MISSING | DONE | **Add** | S | E-ACT |
| **Comments** | PARTIAL (portal comments) | DONE | **Promote to core** | S | E-ACT |
| **Attachments inline (drag-drop)** | STUB (ir_attachment + portal) | DONE | **Finish (admin UI)** | M | E-ACT |
| **Notifications** (in-app + email) | MISSING | DONE | **Add** | M | E-ACT |

## 5. Communications

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| **Email send (SMTP)** | PARTIAL (transport exists, no templates) | DONE | **Finish + templates** | M | E-COMMS |
| **Two-way email sync (Gmail)** | MISSING | DONE | **Add** | XL | E-COMMS |
| **IMAP/SMTP mailbox sync** | MISSING | DONE | **Add** | L | E-COMMS |
| **Email-in-CRM (logged on records)** | STUB (`EmailLog`) | DONE | **Add** | M | E-COMMS |
| **Calendar sync (Google/CalDAV)** | MISSING | DONE | **Add** | L | E-COMMS |
| **Email templates** | STUB (`ir_mail_template`) | DONE | **Finish** | S | E-COMMS |
| **Sequences / cadences** | MISSING | n/a | **Add later** | L | E-COMMS |
| **Shared inbox** | MISSING | partial | **Add later** | L | E-COMMS |

## 6. Automation & intelligence

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| **Generic workflow engine** | MISSING (ADR-0015 deferred) | DONE (early) | **Add (new ADR, Postgres FSM)** | XL | E-FLOW |
| Automation rules (trigger/cond/action) | PARTIAL (`crm.automation_rule`) | DONE | **Promote + expand actions** | M | E-FLOW |
| **Assignment rules / round-robin** | MISSING | partial | **Add** | M | E-FLOW |
| **Lead/deal scoring** | PARTIAL (`score` field, manual) | partial | **Add scoring engine** | M | E-FLOW |
| **SLAs / escalations** | MISSING | n/a | **Add later** | M | E-FLOW |
| AI copilot (chat + tools) | DONE | DONE (newer) | **Keep + widen** | M | E-AI |
| AI embeddings / semantic search | PARTIAL (pgvector, retrieval not wired) | partial | **Finish** | M | E-AI |
| **AI NL → report/dashboard** | PARTIAL (`/api/ai/dashboard` scaffold) | n/a | **Finish** | M | E-AI |
| **AI enrichment / summarize / next-best-action** | MISSING | partial | **Add** | L | E-AI |
| **AI dedup suggestions** | MISSING | n/a | **Add** | S | E-AI |

## 7. Analytics & marketing

| Capability | Current | Twenty | Decision | Size | Epic |
|---|---|---|---|---|---|
| Aggregate endpoint | DONE | n/a | **Keep** | — | E-ANALYTICS |
| **Dashboards (composable)** | PARTIAL (AIDashboard) | partial | **Add** | L | E-ANALYTICS |
| **Reports (saved, scheduled)** | MISSING | partial | **Add** | M | E-ANALYTICS |
| **Forecasting board** | MISSING | partial | **Add** | M | E-ANALYTICS |
| **Campaigns / segments** | PARTIAL (UTM on lead) | n/a | **Add later** | L | E-MKT |
| **Web forms / lead capture** | MISSING | n/a | **Add later** | M | E-MKT |
| **PDF reports / quote PDFs** | MISSING (deferred) | n/a | **Add** | M | E-ANALYTICS |

## 8. Summary of new work, by size

| Size | Count | Examples |
|---|---|---|
| **XL** | 5 | metadata engine, GraphQL, email sync, workflow engine, apps/SDK |
| **L** | ~11 | custom-field UI, field types, timeline, IMAP sync, calendar sync, dashboards, CPQ, AI enrichment, sequences, mobile/PWA, contracts |
| **M** | ~20 | record page, saved views, filters, import, products, quotes, scoring, reports, etc. |
| **S** | ~15 | favorites, recents, bulk actions, API keys, templates, mentions, comments, calendar/graph finish, etc. |

The backlog in [`06-task-backlog.md`](./06-task-backlog.md) sequences these into
waves. The architecture that makes the XL items tractable is in
[`03-architecture-strategy.md`](./03-architecture-strategy.md).
