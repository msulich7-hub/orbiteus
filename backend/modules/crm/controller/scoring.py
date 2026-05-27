"""Lead / prospect scoring (SPEC-015 v0)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext


def calculate_score(obj, days_in_stage: int | None = None) -> int:
    score = 0
    temp = (getattr(obj, "temperature", "") or "").lower()
    score += {"hot": 40, "warm": 20, "cold": 5}.get(temp, 0)

    utm = (getattr(obj, "utm_source", "") or "").lower()
    score += {"referral": 20, "organic": 15, "ads": 10, "cold_call": 5}.get(utm, 0)

    lifecycle = (getattr(obj, "lifecycle_stage", "") or "").lower()
    score += {"sql": 30, "mql": 15, "prospect": 5}.get(lifecycle, 0)

    if getattr(obj, "assigned_user_id", None):
        score += 5

    if days_in_stage is not None and days_in_stage > 14:
        score -= 15

    return max(0, min(100, score))


async def recalculate_all_scores(session: AsyncSession, ctx: RequestContext) -> int:
    """Batch-recalculate scores for all leads and prospects in the tenant."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        ProspectRepository,
        StageRepository,
    )
    from modules.crm.controller.services import evaluate_lead_rotting

    lead_repo = LeadRepository(session, ctx)
    prospect_repo = ProspectRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)

    now = datetime.now(timezone.utc)
    updated = 0

    stages, _ = await stage_repo.search(limit=500)
    stage_by_id = {s.id: s for s in stages}

    leads, _ = await lead_repo.search(limit=10000)
    for lead in leads:
        stage = stage_by_id.get(lead.stage_id) if lead.stage_id else None
        _, days_in_stage, _ = evaluate_lead_rotting(lead, stage, now)
        score = calculate_score(lead, days_in_stage=days_in_stage)
        await lead_repo.update(
            lead.id,
            {"score": score, "score_updated_at": now},
        )
        updated += 1

    prospects, _ = await prospect_repo.search(limit=10000)
    for prospect in prospects:
        days_in_stage = None
        create_date = getattr(prospect, "create_date", None)
        if create_date is not None:
            days_in_stage = (now - create_date).days
        score = calculate_score(prospect, days_in_stage=days_in_stage)
        await prospect_repo.update(
            prospect.id,
            {"score": score, "score_updated_at": now},
        )
        updated += 1

    return updated
