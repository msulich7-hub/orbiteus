# CRM 2027 — Master Program Encyclopedia

> **Codename:** CRM 2027 — "the best CRM on the market", built on the Orbiteus engine.
>
> This folder is the **single source of truth** for the program that turns the
> Orbiteus engine + its canonical CRM module into a full, best-in-class CRM
> product, comparable to (and in key areas ahead of) the open-source reference
> [Twenty](https://twenty.com).
>
> **Status:** SPEC v1 (planning only — no production code on this branch).
> **Branch:** `claude/orbiteus-crm2027-spec`.
> **Owner:** product owner (msulich7). Keep this folder updated each wave close.

---

## 0. How to read this encyclopedia

This is a **specification and task backlog**, not implementation. It is written
to be executed by AI agents and senior engineers working inside the Orbiteus
contracts. Read in order; later chapters depend on earlier ones.

Before reading anything here, an AI agent must first read the engine contract:
[`../pre-prompt.md`](../pre-prompt.md) and [`../README.md`](../README.md). This
program never breaks the engine's hard rules — it **extends** the engine.

| # | Chapter | What it answers |
|---|---------|-----------------|
| 00 | [`00-vision-and-positioning.md`](./00-vision-and-positioning.md) | What we are building, for whom, and why it can be the best. |
| 01 | [`01-orbiteus-vs-twenty.md`](./01-orbiteus-vs-twenty.md) | Feature-by-feature comparison + feasibility verdict. |
| 02 | [`02-gap-analysis.md`](./02-gap-analysis.md) | Capability matrix: keep / add / refactor, with effort sizing. |
| 03 | [`03-architecture-strategy.md`](./03-architecture-strategy.md) | The hybrid metadata engine; how Twenty's superpowers graft onto Orbiteus. |
| 04 | [`04-data-model.md`](./04-data-model.md) | Full CRM 2027 object catalog, field-type system, relations. |
| 05 | [`05-feature-epics.md`](./05-feature-epics.md) | The feature encyclopedia — every epic, grouped by domain. |
| 06 | [`06-task-backlog.md`](./06-task-backlog.md) | Waves and numbered tasks, each with DoD + tests + ADR refs. |
| 07 | [`07-adr-index.md`](./07-adr-index.md) | New architectural decisions this program requires. |
| 08 | [`08-roadmap-and-milestones.md`](./08-roadmap-and-milestones.md) | Phasing, sequencing, risk register, success metrics. |
| 09 | [`09-non-functional.md`](./09-non-functional.md) | Performance, security, compliance, scale, i18n, a11y targets. |

---

## 1. The one-paragraph thesis

Orbiteus is already a production-grade, AI-native modular monolith: mandatory
audit, five-level RBAC, multi-tenancy, EventBus + Postgres outbox, Celery
workers, SSE realtime, BYOK AI with a tool dispatcher that obeys the same RBAC
as humans, and a zero-TSX dynamic admin renderer. Its CRM module is already
**Pipedrive-class** (Organization / Person / Pipeline / Stage / Lead / Prospect
/ Activity / Team / lifecycle + UTM + scoring). Twenty's decisive advantage is
**runtime metadata** — end users build their own objects, fields, and views with
no code, and the API regenerates itself. The CRM 2027 program keeps every
Orbiteus strength and grafts on the metadata superpower, then layers the
remaining best-in-class CRM surfaces (timeline/chatter, two-way email & calendar
sync, a real workflow engine, quotes/products/CPQ, marketing, reporting, an apps
ecosystem, and an AI copilot that is genuinely native rather than bolted on).
The verdict, defended in chapter 01: **yes — Orbiteus can be improved to match
and surpass Twenty, and it is the better foundation for an AI-first CRM.**

---

## 2. Guiding principles (non-negotiable)

1. **Extend, never fork the engine.** Every CRM 2027 capability lands as a
   module or a *new core primitive* added through the registry — never by
   bypassing `BaseRepository`, RBAC, audit, or the outbox.
2. **AI-native, not AI-attached.** Every object, field, view, and workflow is
   reachable by the AI tool dispatcher under the caller's RBAC. Copilot is a
   first-class surface, not a chat box in a corner.
3. **Metadata-first for the product surface, code-first for the engine.** Users
   shape their CRM at runtime; engineers/agents extend the platform in code.
4. **Boring tech filter still applies.** New runtime dependencies require an ADR
   (see [`07-adr-index.md`](./07-adr-index.md)).
5. **Every task ships tests + docs.** No wave closes with red CI or drifted docs.
6. **Honest ledger.** Progress is tracked the Orbiteus way — see
   [`../34-inventory-and-status.md`](../34-inventory-and-status.md) for the
   format this program mirrors.

---

## 3. Scope of this branch

This branch delivers **documentation only**: the chapters above. It contains the
plan that subsequent implementation branches execute, wave by wave, as defined in
[`06-task-backlog.md`](./06-task-backlog.md). No engine or module code changes
ship here.
