"""CRM custom endpoints — canonical (PR 9): kanban over Lead.stage_id."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth

router = APIRouter(tags=["crm"])


@router.get("/leads/kanban")
async def leads_kanban(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Group leads by stage for the kanban view."""
    from modules.crm.controller.repositories import LeadRepository, StageRepository

    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    stages, _ = await stage_repo.search(limit=200)
    leads, _ = await lead_repo.search(limit=5000)

    by_stage: dict[str, list] = {}
    for lead in leads:
        if lead.stage_id is None:
            continue
        by_stage.setdefault(str(lead.stage_id), []).append(lead)

    columns = []
    total_revenue = 0.0
    for stage in sorted(stages, key=lambda s: s.sequence):
        bucket = by_stage.get(str(stage.id), [])
        revenue = sum(l.expected_revenue for l in bucket)
        total_revenue += revenue
        columns.append({
            "stage_id": str(stage.id),
            "stage_name": stage.name,
            "sequence": stage.sequence,
            "probability": stage.probability,
            "is_won": stage.is_won,
            "is_lost": stage.is_lost,
            "fold_in_kanban": stage.fold_in_kanban,
            "count": len(bucket),
            "expected_revenue": revenue,
            "leads": [
                {
                    "id": str(l.id),
                    "name": l.name,
                    "expected_revenue": l.expected_revenue,
                    "probability": l.probability,
                    "person_id": str(l.person_id) if l.person_id else None,
                    "assigned_user_id": str(l.assigned_user_id) if l.assigned_user_id else None,
                    "assigned_team_id": str(l.assigned_team_id) if l.assigned_team_id else None,
                }
                for l in bucket
            ],
        })

    return {
        "columns": columns,
        "total_leads": sum(c["count"] for c in columns),
        "total_expected_revenue": total_revenue,
    }


@router.post("/lead/{lead_id}/move")
async def move_lead(
    lead_id: uuid.UUID,
    stage_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Move a lead to a different stage."""
    from modules.crm.controller.services import move_lead_to_stage

    await move_lead_to_stage(session, ctx, lead_id, stage_id)
    return {"message": "Lead moved", "lead_id": str(lead_id), "stage_id": str(stage_id)}


@router.get("/stats")
async def crm_stats(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Dashboard statistics for CRM."""
    from modules.crm.controller.repositories import LeadRepository, PersonRepository

    person_repo = PersonRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    _, total_persons = await person_repo.search(limit=1)
    leads, total_leads = await lead_repo.search(limit=2000)

    won = [l for l in leads if l.probability == 100.0]
    pipeline_value = sum(l.expected_revenue for l in leads)

    return {
        "total_persons": total_persons,
        "total_leads": total_leads,
        "won_leads": len(won),
        "pipeline_value": pipeline_value,
        "won_revenue": sum(l.expected_revenue for l in won),
    }
