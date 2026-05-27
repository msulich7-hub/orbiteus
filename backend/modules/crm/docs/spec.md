# Module: crm — Pipedrive-class extensions

> **Layer:** product  
> **depends_on:** [base, auth]  
> **Status:** in development (v0.4.0 — SPEC-001..008)  
> **Specs (Testorbiteka):** SPEC-001..008 in `Testorbiteka/docs/specs/`

## Purpose

Extend canonical CRM into a **Pipedrive-competitive** foundation:

| Spec | Feature |
|------|---------|
| 001 | `crm.organization` + contact link |
| 002 | `crm.pipeline` multi-pipeline |
| 003 | `crm.prospect` inbox → convert to deal |
| 004 | `crm.activity` execution layer |
| 005 | rotting + `crm.stage_history` |
| 008 | lifecycle stages + UTM attribution on prospect/lead |

## Models

See `model/domain.py` — 9 domain entities.

## Custom endpoints

| Method | Path |
|--------|------|
| GET | `/api/crm/leads/kanban?pipeline_id=` |
| POST | `/api/crm/lead/{id}/move` |
| PATCH | `/api/crm/lead/{id}/lifecycle?stage=` |
| POST | `/api/crm/prospect/{id}/convert` |
| GET | `/api/crm/leads/rotting` |
| GET | `/api/crm/lead/{id}/stage-history` |
| GET | `/api/crm/activities/today` |
| POST | `/api/crm/activity/{id}/done` |
| GET | `/api/crm/stats` |

## Events (outbox)

- `crm.lead.stage_changed`
- `crm.lead.closed`
- `crm.prospect.converted`
- `crm.lead.lifecycle_changed`

## Lifecycle stages

`subscriber` → `lead` → `mql` → `sql` → `opportunity` → `customer`

On prospect convert: UTM fields copy to lead; `lifecycle_stage` set to `sql`.

## Migration

- `g7b2c3d4e008_crm_pipedrive_extensions.py`
- `h8d4e5f6a009_crm_lifecycle_attribution.py`
