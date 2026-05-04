# `crm` module — spec (canonical)

> **Superseded by `docs/`.** Authoritative documentation lives in the
> top-level chapters. Pointers below.
>
> **Canonical sources:**
> - `docs/26-canonical-crm.md` — full design & rationale
> - `docs/adr/0008-crm-mvp-rename-person-lead-stage-team.md` — naming
> - `docs/15-ai-layer.md` — `ai.py` declaration
> - `docs/16-ai-recipes.md` — embedding the prompt input

## Purpose

CRM is the engine's *canonical product example* — the smallest realistic
business module that exercises every framework primitive (auto-CRUD,
RBAC, Audit, EventBus, Outbox, Realtime, AI layer, dynamic admin
renderer with list/kanban/calendar views). It is **not** meant to be a
production-grade CRM out of the box.

## Models

| Domain class | Table          | Purpose                                    |
|--------------|----------------|--------------------------------------------|
| `Person`     | `crm_persons`  | Contacts (`kind` enum: customer / vendor / partner / individual) |
| `Lead`       | `crm_leads`    | Sales opportunities tied to a `Person` and a `Stage` |
| `Stage`      | `crm_stages`   | Pipeline columns (Open → Qualified → Won / Lost) |
| `Team`       | `crm_teams`    | Sales teams (membership = list of users)   |

`Person` and `Lead` carry the standard `BaseModel` columns
(`tenant_id`, `created_at`, `updated_at`, `created_by_id`,
`modified_by_id`, `is_deleted`).

## Endpoints

Auto-CRUD (`AutoRouter`) plus curated routes:

- `GET  /api/crm/lead/kanban`     — leads grouped by stage
- `POST /api/crm/lead/{id}/move`  — move lead to another stage; emits
  `crm.lead.moved` and (if won/lost) `crm.lead.closed` to the Outbox
- `GET  /api/crm/stats`            — team-level KPIs

## AI surface

`ai.py` declares an `AIModuleConfig` with:

- `accessible_models = ["crm.person", "crm.lead", "crm.stage", "crm.team"]`
- `callable_actions = ["crm.lead.move", "crm.lead.create", "crm.person.create"]`
- `embed_models = ["crm.person", "crm.lead"]`
- `suggested_prompts = ["Show pipeline for this month", "Top 5 leads by value"]`

The Admin UI dashboard embeds `<PromptInput>` and `<AIDashboard>` from
`admin-ui/src/orbiteus-ui/` — no module-specific code on the frontend.

## Bootstrap

`bootstrap.py` seeds default stages (Open, Qualified, Proposal, Won,
Lost) and a single Sales team on first install.
