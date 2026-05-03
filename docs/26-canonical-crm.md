# 26 — Canonical CRM (MVP)

The CRM module is the **canonical product example** shipped with the engine.
It exists to prove the framework end-to-end and to give clients a working
baseline to extend.

## Models

### `crm.person`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | base |
| `tenant_id`, `company_id` | UUID | base |
| `name` | str | required |
| `email` | str | optional, unique per tenant |
| `phone` | str | optional |
| `mobile` | str | optional |
| `kind` | enum: `lead` \| `customer` \| `contact` | default `contact` |
| `assigned_user_id` | UUID FK → users | sales owner |
| `assigned_team_id` | UUID FK → crm.team | optional |
| `tags` | list[str] | JSONB |
| `source` | enum: `website` \| `referral` \| `cold_call` \| `event` | optional |
| `vat`, `website`, `street`, `city`, `country_code` | str | optional |
| `is_company` | bool | distinguishes company vs individual |

### `crm.lead`

| Field | Type | Notes |
|---|---|---|
| `name` | str | required |
| `person_id` | UUID FK → crm.person | required |
| `stage_id` | UUID FK → crm.stage | required |
| `assigned_user_id` | UUID FK → users | optional |
| `assigned_team_id` | UUID FK → crm.team | optional |
| `expected_revenue` | numeric(14,2) | tenant currency |
| `probability` | numeric(5,2) | 0..100 |
| `expected_close_date` | date | for calendar view |
| `description` | text | |

### `crm.stage`

| Field | Type | Notes |
|---|---|---|
| `name` | str | required |
| `sequence` | int | sort order |
| `probability` | numeric(5,2) | default for leads in this stage |
| `is_won`, `is_lost` | bool | terminal flags |
| `fold_in_kanban` | bool | folded by default |

### `crm.team`

| Field | Type | Notes |
|---|---|---|
| `name` | str | required |
| `leader_user_id` | UUID FK → users | optional |
| `member_user_ids` | list[UUID] | JSONB |
| `description` | text | |

## Views

| View | Model | Demonstrates |
|---|---|---|
| `list` | `crm.person`, `crm.lead`, `crm.team` | columns, badge, monetary, many2one widgets |
| `kanban` | `crm.lead` (group by `stage_id`) | drag-drop, optimistic update |
| `calendar` | `crm.lead` (date_start = `expected_close_date`) | calendar view stub completion |
| `form` | all | groups, statusbar (`crm.lead.stage`), readonly fields |

## Actions (`actions.py`)

- `crm.person.create`
- `crm.lead.create`
- `crm.lead.move_stage`
- `crm.lead.assign_team`
- `crm.lead.mark_won`
- `crm.lead.mark_lost`

## AI demo (`ai.py`)

```python
AI = AIModuleConfig(
    enabled=True,
    system_prompt="You are the CRM assistant for {{ tenant.name }}.",
    accessible_models=["crm.person", "crm.lead", "crm.stage", "crm.team"],
    callable_actions=[
        "crm.person.create",
        "crm.lead.create",
        "crm.lead.move_stage",
        "crm.lead.assign_team",
    ],
    embed_models=["crm.person", "crm.lead"],
    suggested_prompts=[
        PromptTemplate(id="hot_leads", label="Hot leads this week"),
        PromptTemplate(id="weekly_summary", label="Weekly team summary"),
        PromptTemplate(id="rotting", label="Leads stuck > 14 days"),
    ],
    dashboard=True,
)
```

Dashboard examples:

- "Pipeline value by stage"
- "Won vs lost this quarter"
- "Top 5 reps by closed revenue"

## Bootstrap (`bootstrap.py`)

```python
async def on_install(session, ctx) -> None:
    await ensure_default_stages(session, ctx)        # New, Qualified, Proposal, Won, Lost
    await ensure_default_team(session, ctx)          # "Sales"
```

`backend/api.py` lifespan no longer seeds CRM. The seeds run when the module
is registered for a tenant, not at engine boot.

## Migration from previous CRM

Earlier versions used `crm.customer` + `crm.opportunity` + `crm.pipeline`.
Migration steps:

1. Add new tables (`crm_persons`, `crm_leads`, `crm_stages`, `crm_teams`).
2. Backfill from old tables (one Person per Customer, one Lead per Opportunity).
3. Switch reads/writes to new tables (dual-write briefly).
4. Drop old tables in next minor release.

Migration guide: `docs/migrations/0.1-to-0.2.md` (to be created when migration
runs).

## Tests

- Per-model auto-CRUD
- Kanban move endpoint
- Calendar query (date_start within range)
- AI tool call moves a lead's stage and audits with `actor=ai`
- Realtime: drag in browser A is reflected in browser B
