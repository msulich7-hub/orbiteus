# 00 — Vision & Positioning

> What CRM 2027 is, who it serves, and the bets that let it claim "best on the
> market". Read [`README.md`](./README.md) first.

## 1. Vision statement

> **CRM 2027 is the first CRM where the data model, the workflows, and the AI are
> the same fabric.** A user shapes their pipeline, objects, and automations at
> runtime; the API, the views, the audit trail, and the AI copilot reshape
> themselves automatically — with multi-tenant, audited, RBAC-enforced
> guarantees underneath every byte.

We are not building "a CRM with an AI feature". We are building a CRM whose
*substrate* is AI-ready: every object is a tool, every workflow is auditable,
every change is an event, and the assistant operates with exactly the same
permissions as the human it works for.

## 2. Who it is for

| Segment | Pain today | What CRM 2027 gives them |
|---|---|---|
| **SMB sales teams** | Rent-a-seat CRMs force a vendor's median pipeline. | Build your pipeline, objects, and stages in minutes; no code. |
| **RevOps / operators** | Data scattered across CRM + spreadsheets + tools. | One coherent surface: deals, products, quotes, contracts, activities, email. |
| **Technical teams / agencies** | Want to version and extend the CRM like code. | Code-first modules + a CLI/SDK + an apps ecosystem on top of metadata. |
| **AI-forward orgs** | Bolt-on copilots can't safely touch CRM data. | A copilot that reads/writes through the same RBAC + audit as people. |
| **Regulated / EU orgs** | SaaS data residency + GDPR friction. | Self-hostable, audited, GDPR tooling (DSAR, retention) built in. |

## 3. Positioning against the field

- **vs Twenty (open reference):** match its runtime-metadata superpower; beat it
  on audit, RBAC depth, AI-native tool dispatch, outbox-grade reliability, and a
  partner portal. (Full comparison: [`01-orbiteus-vs-twenty.md`](./01-orbiteus-vs-twenty.md).)
- **vs Pipedrive:** already at parity on pipelines/stages/rotting/activities;
  surpass on customization, automation, and AI.
- **vs HubSpot:** narrower on marketing breadth at launch, but radically more
  customizable, self-hostable, and cheaper to own; close the marketing gap in
  later waves (campaigns, sequences, forms).
- **vs Salesforce:** the "open, AI-native, you-own-the-data" alternative —
  enterprise-grade primitives without the enterprise tax or lock-in.

## 4. The three strategic bets

1. **Metadata as a first-class engine primitive.** End users create custom
   objects, fields, relations, and views at runtime. This is Twenty's moat; we
   adopt it as a hybrid (see [`03-architecture-strategy.md`](./03-architecture-strategy.md))
   without losing code-first modules.
2. **The copilot is the new command line.** Natural-language create/update/move/
   report across every object, every workflow — governed by RBAC and fully
   audited. This is where Orbiteus's AI layer already leads and we widen the lead.
3. **Reliability as a feature.** Mandatory audit, atomic outbox, dead-letter
   retries, realtime fan-out, and provable multi-tenant isolation are table
   stakes for trust. We market them as such.

## 5. What "best on the market" must be true to claim

A scoreboard we hold ourselves to (targets defended in
[`09-non-functional.md`](./09-non-functional.md)):

- **Time-to-first-pipeline:** a new tenant configures objects + pipeline + first
  deal in **under 10 minutes**, no code.
- **Customization without deploy:** add an object/field/view and it appears in
  the API, the UI, the audit log, and the copilot **with zero redeploy**.
- **AI safety:** 100% of AI writes audited with `actor=ai`; **zero** AI path that
  bypasses RBAC (proven by negative tests).
- **Reliability:** webhook/automation delivery is at-least-once with bounded
  retries + dead-letter; **no** synchronous third-party calls in request path.
- **Trust:** provable cross-tenant isolation (negative tests), GDPR DSAR +
  retention tooling, self-host in one command.
- **Performance:** p95 list/read < 200 ms at 5–10k DAU on a single host
  (k8r path documented).

## 6. Product pillars (the table of contents of the product)

These pillars organize the whole feature encyclopedia in
[`05-feature-epics.md`](./05-feature-epics.md):

1. **Model** — objects, fields, relations, metadata builder, custom fields.
2. **Records & Views** — table, kanban, calendar, timeline, gallery, record page,
   saved views, filters, sorts, grouping, favorites, recents.
3. **Pipeline & Revenue** — pipelines, stages, deals, forecasting, products,
   price books, quotes/CPQ, contracts/subscriptions.
4. **Activities & Collaboration** — tasks, calls, meetings, notes, timeline/
   chatter, mentions, attachments.
5. **Communications** — two-way email sync (Gmail/IMAP), calendar sync
   (Google/CalDAV), templates, sequences, inbox.
6. **Automation** — workflow engine (triggers/conditions/actions), playbooks,
   scoring, assignment, SLAs.
7. **Intelligence (AI)** — copilot, NL reporting, enrichment, dedup/merge,
   next-best-action, semantic search.
8. **Analytics** — dashboards, reports, forecasting, goals/quotas.
9. **Marketing (later waves)** — campaigns, segments, web forms, lead capture.
10. **Platform** — API (REST now, GraphQL later), webhooks, API keys, apps/SDK,
    import/export, roles & permissions, audit, portal, mobile/PWA.

## 7. Non-goals (for the first program horizon)

- A full marketing-automation suite rivaling HubSpot at launch (phased later).
- Native mobile apps (PWA first; native is a later evaluation).
- An accounting/ERP suite — Orbiteus can host those as separate modules, but
  CRM 2027 integrates rather than absorbs them.
- Replacing the engine's boring-tech stack with trendier alternatives.
