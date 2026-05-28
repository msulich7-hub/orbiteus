# 08 — Roadmap, Milestones & Risk

> How the waves in [`06-task-backlog.md`](./06-task-backlog.md) sequence into
> shippable milestones, what each milestone proves, the risks, and the success
> metrics. Effort is order-of-magnitude for a small senior team (or AI agents +
> reviewers) and is deliberately conservative.

## 1. Phasing

```
Phase A — Foundation        Wave 0,1,2      "Customize anything, no code"
Phase B — The living record Wave 3,4        "Email + timeline in the CRM"
Phase C — Make it work      Wave 5,6        "Automation + revenue"
Phase D — Make it smart     Wave 7,8        "Analytics + AI copilot"
Phase E — Platform & growth Wave 9,10       "API, apps, marketing"
```

## 2. Milestones (each is a demoable, tested release)

### M1 — "Metadata GA" (end of Phase A)
- **Proves:** a tenant builds custom objects, fields (all types), relations, and
  saved views from the UI; everything is in REST/ui-config/audit/realtime/AI with
  zero redeploy. Table view has inline edit, filters, sorts, group-by, bulk
  actions, favorites, recents.
- **Closes epics:** E-META, E-FIELD, most of E-VIEW.
- **Headline:** *"As customizable as Twenty — with mandatory audit and RBAC."*

### M2 — "The CRM is the inbox" (end of Phase B)
- **Proves:** unified per-record timeline; notes/comments/@mentions/tasks/
  reminders/notifications; two-way email (Gmail/IMAP) + calendar (Google/CalDAV)
  sync logged on records; templates + send.
- **Closes epics:** E-ACT, E-COMMS.
- **Headline:** *"Every interaction, on the record, automatically."*

### M3 — "Runs itself, closes deals" (end of Phase C)
- **Proves:** workflow engine (triggers/conditions/actions) with visual builder,
  assignment + scoring; products/price books/quotes with PDF + send/accept;
  forecasting board.
- **Closes epics:** E-FLOW, E-CPQ, E-PIPE.
- **Headline:** *"Automation with outbox-grade reliability; quote to close."*

### M4 — "Decisions & copilot" (end of Phase D)
- **Proves:** composable dashboards, scheduled reports, goals/quotas; import/
  export/dedup; semantic search; NL→report/view; AI enrichment/summarize/
  next-best-action/draft; copilot at record/list/global — all RBAC-bound, audited.
- **Closes epics:** E-ANALYTICS, E-DATA, E-AI.
- **Headline:** *"The copilot is the command line — and it can't break the rules."*

### M5 — "Platform & growth" (end of Phase E)
- **Proves:** API keys, field-level RBAC, multi-company UX, i18n, webhook UI,
  portal extensions, GDPR tooling; GraphQL gateway; apps/SDK/CLI; PWA; marketing
  (campaigns/segments/forms/sequences).
- **Closes epics:** E-PLAT, E-PORTAL, E-APPS, E-MKT.
- **Headline:** *"A platform, not just an app."*

## 3. Indicative timeline

Order-of-magnitude, assuming ~2 senior engineers (or equivalent AI-agent +
reviewer throughput). Parallelizable tracks noted.

| Phase | Waves | Effort | Parallelism |
|---|---|---|---|
| A — Foundation | 0,1,2 | 6–9 wk | views (W2) can trail metadata (W1) |
| B — Living record | 3,4 | 6–10 wk | comms (W4) is its own track; timeline (W3) first |
| C — Work & revenue | 5,6 | 6–9 wk | workflow (W5) ∥ revenue (W6) |
| D — Smart | 7,8 | 6–9 wk | analytics (W7) ∥ AI (W8) |
| E — Platform | 9,10 | 8–14 wk | many independent items; GraphQL + apps are XL |

**Total:** roughly **7–12 months** to M5 depending on team size and how
aggressively XL items (Gmail sync, workflow, GraphQL, apps) are pursued. M1–M3
(a genuinely competitive, self-hostable, AI-native CRM) is achievable in the
first **4–6 months**.

## 4. Critical path

```
ADRs (CRM27-01)
  → field registry + filter DSL (02,03)
    → metadata engine (10→11→12→13→14)      [the moat — gates most UI work]
      → views (22→24/26)  → timeline (40→41) → comms (50→51→52→53)
                                            → workflow (60→62→64)
      → CPQ (70→71→72) → analytics (80→81) → AI (90→91→92→93)
                                            → platform/GraphQL (107) / apps (108)
```

The **metadata engine is the long pole**: prioritize CRM27-10..14, then fan out.

## 5. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Runtime DDL causes locks/drift in multi-tenant Postgres | Med | High | JSONB-first default; materialization is background + `pg_try_advisory_lock` + idempotent; per-tenant guard rails; ADR-0019. |
| 2 | Email/calendar sync complexity (OAuth, IMAP quirks, threading, dedup) | High | High | Phase: IMAP → Gmail → calendar; idempotent + outbox-retried; mock-based tests; treat as its own track. |
| 3 | Workflow engine scope creep | Med | Med | Thin Postgres FSM, not Temporal (ADR-0023); feature-flag; action library grows incrementally. |
| 4 | AI cost / safety | Med | High | Budget guard + redaction exist; extend to new surfaces; RBAC negative tests for every AI path. |
| 5 | Engine purity erosion (someone bypasses BaseRepository/audit) | Med | High | Every task names its primitive + forbids bypass; CI gate; code review on framework-layer changes (2 reviewers). |
| 6 | Custom-object performance at scale | Med | Med | Expression/GIN indexes for JSONB filters; materialize hot fields/objects; perf budget in [`09-non-functional.md`](./09-non-functional.md). |
| 7 | GraphQL becomes a parallel data path | Low | High | ADR-0025 mandates resolution through BaseRepository; no direct DB access. |
| 8 | Scope/expectations ("best CRM") outrun capacity | High | Med | Milestone-based marketing; M1–M3 is the credible "competitive" line; M4–M5 is the "ahead" line. |

## 6. Success metrics (tracked per milestone)

- **Adoption:** time-to-first-pipeline < 10 min; % tenants using a custom object.
- **AI:** % AI writes audited (target 100%); AI-RBAC negative tests passing (100%).
- **Reliability:** webhook/automation delivery success rate; outbox dead-letter
  rate; sync lag (email/calendar).
- **Performance:** p95 list/read < 200 ms at 5–10k DAU (single host).
- **Quality:** CI green every merge; coverage ≥ engine threshold; zero
  cross-tenant leaks (negative tests).
- **Parity:** feature-matrix coverage vs Twenty (target: ≥ parity by M2, ahead on
  audit/RBAC/AI/portal throughout).

## 7. Governance & cadence

- One wave = one milestone slice; close it only when its DoD slice is reflected
  in a CRM2027 inventory ledger (mirroring [`../34-inventory-and-status.md`](../34-inventory-and-status.md)).
- ADRs precede their implementing wave.
- Demo follows main: each merged wave is rebuilt on the demo host.
- Re-baseline this roadmap at each milestone close.
