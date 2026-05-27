"""CRM business logic (SPEC-001..005).

Side effects go through Outbox + Celery (ADR-0010, ADR-0013, ADR-0015).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


def normalize_lifecycle_stage(stage: str) -> str:
    """Validate and normalize lifecycle stage (SPEC-008)."""
    from modules.crm.model.domain import LIFECYCLE_STAGES

    normalized = stage.strip().lower()
    if normalized not in LIFECYCLE_STAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid lifecycle stage",
                "allowed": list(LIFECYCLE_STAGES),
                "received": stage,
            },
        )
    return normalized


def _utm_fields_from_prospect(prospect) -> dict[str, str]:
    return {
        "utm_source": prospect.utm_source or "",
        "utm_medium": prospect.utm_medium or "",
        "utm_campaign": prospect.utm_campaign or "",
        "utm_content": prospect.utm_content or "",
        "utm_term": prospect.utm_term or "",
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_lead_field_empty(lead, field_name: str) -> bool:
    """True when a blueprint-required lead field has no usable value."""
    if not hasattr(lead, field_name):
        return True
    value = getattr(lead, field_name)
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def missing_required_exit_fields(lead, from_stage) -> list[str]:
    """Fields required on crm.stage before leaving it (stage exit blueprint)."""
    required = getattr(from_stage, "required_fields_json", None) or []
    missing: list[str] = []
    for field_name in required:
        if not isinstance(field_name, str) or not field_name.strip():
            continue
        if _is_lead_field_empty(lead, field_name.strip()):
            missing.append(field_name.strip())
    return missing


def evaluate_lead_rotting(
    lead,
    stage,
    now: datetime | None = None,
) -> tuple[bool, int | None, str | None]:
    """Smart rotting: stage threshold + activity inactivity gate.

    is_rotting = (days_in_stage > rotting_days)
        AND (last_activity_at is null OR days_since_activity > min(7, rotting_days))
    """
    if now is None:
        now = _utcnow()
    if not lead.stage_id or not lead.stage_entered_at or stage is None:
        return False, None, None
    if stage.rotting_days is None or stage.is_won or stage.is_lost:
        return False, None, None

    days_in_stage = (now - lead.stage_entered_at).days
    if days_in_stage <= stage.rotting_days:
        return False, days_in_stage, None

    activity_threshold = min(7, stage.rotting_days)
    if lead.last_activity_at is None:
        return True, days_in_stage, "no_activity_in_stage"

    days_since_activity = (now - lead.last_activity_at).days
    if days_since_activity > activity_threshold:
        return True, days_in_stage, f"inactive_{days_since_activity}_days"

    return False, days_in_stage, None


async def batch_resolve_lead_display_names(
    session: AsyncSession,
    ctx: RequestContext,
    leads,
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    """Batch lookup person, organization, and user names for lead rows."""
    from modules.base.controller.repositories import UserRepository
    from modules.crm.controller.repositories import OrganizationRepository, PersonRepository

    person_ids = {l.person_id for l in leads if l.person_id}
    org_ids = {l.organization_id for l in leads if l.organization_id}
    user_ids = {l.assigned_user_id for l in leads if l.assigned_user_id}

    person_names: dict[uuid.UUID, str] = {}
    org_names: dict[uuid.UUID, str] = {}
    user_names: dict[uuid.UUID, str] = {}

    if person_ids:
        repo = PersonRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(person_ids))],
            limit=max(len(person_ids), 1),
        )
        person_names = {p.id: p.name for p in rows}

    if org_ids:
        repo = OrganizationRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(org_ids))],
            limit=max(len(org_ids), 1),
        )
        org_names = {o.id: o.name for o in rows}

    if user_ids:
        repo = UserRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(user_ids))],
            limit=max(len(user_ids), 1),
        )
        user_names = {u.id: u.name or u.email for u in rows}

    return person_names, org_names, user_names


async def move_lead_to_stage(
    session: AsyncSession,
    ctx: RequestContext,
    lead_id: uuid.UUID,
    stage_id: uuid.UUID,
    *,
    lost_reason: str = "",
) -> None:
    """Move a lead to a new stage with history + rotting timestamps."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        StageHistoryRepository,
        StageRepository,
    )
    from orbiteus_core.outbox import enqueue

    lead_repo = LeadRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)
    history_repo = StageHistoryRepository(session, ctx)

    lead = await lead_repo.get(lead_id)
    stage = await stage_repo.get(stage_id)

    if lead.pipeline_id and stage.pipeline_id and lead.pipeline_id != stage.pipeline_id:
        raise HTTPException(
            status_code=400,
            detail="Stage belongs to a different pipeline than the lead",
        )

    from_stage_id = lead.stage_id
    if from_stage_id and from_stage_id != stage_id:
        from_stage = await stage_repo.get(from_stage_id)
        missing = missing_required_exit_fields(lead, from_stage)
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "missing_required_fields",
                    "message": (
                        f"Fill required fields before leaving {from_stage.name!r}"
                    ),
                    "from_stage_id": str(from_stage_id),
                    "from_stage_name": from_stage.name,
                    "missing_fields": missing,
                },
            )

    now = _utcnow()

    update_fields: dict = {
        "stage_id": stage_id,
        "probability": stage.probability,
        "pipeline_id": stage.pipeline_id or lead.pipeline_id,
        "stage_entered_at": now,
    }
    if stage.is_lost and lost_reason.strip():
        update_fields["lost_reason"] = lost_reason.strip()

    await lead_repo.update(lead_id, update_fields)

    lead = await lead_repo.get(lead_id)
    _, days_in_stage, _ = evaluate_lead_rotting(lead, stage, now)
    from modules.crm.controller.scoring import calculate_score

    await lead_repo.update(
        lead_id,
        {
            "score": calculate_score(lead, days_in_stage=days_in_stage),
            "score_updated_at": now,
        },
    )

    await history_repo.create({
        "lead_id": lead_id,
        "from_stage_id": from_stage_id,
        "to_stage_id": stage_id,
        "changed_by_id": ctx.user_id,
        "changed_at": now,
    })

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="crm.lead.stage_changed",
        payload={
            "lead_id": str(lead_id),
            "from_stage_id": str(from_stage_id) if from_stage_id else None,
            "to_stage_id": str(stage_id),
        },
        target_kind="notification",
    )

    from modules.crm.controller.automation import evaluate_lead_stage_changed

    await evaluate_lead_stage_changed(
        session,
        ctx,
        lead=lead,
        lead_id=lead_id,
        from_stage_id=from_stage_id,
        to_stage=stage,
    )

    if stage.is_won or stage.is_lost:
        await enqueue(
            session,
            tenant_id=ctx.tenant_id,
            event="crm.lead.closed",
            payload={
                "lead_id": str(lead_id),
                "outcome": "won" if stage.is_won else "lost",
                "stage_id": str(stage_id),
            },
            target_kind="notification",
        )

    logger.info("crm.lead.moved", extra={"lead_id": str(lead_id), "stage": stage.name})


async def convert_prospect_to_lead(
    session: AsyncSession,
    ctx: RequestContext,
    prospect_id: uuid.UUID,
    *,
    pipeline_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    expected_revenue: float = 0.0,
) -> uuid.UUID:
    """Convert pre-pipeline prospect into pipeline deal (Lead)."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        PipelineRepository,
        ProspectRepository,
        StageRepository,
    )
    from orbiteus_core.outbox import enqueue

    prospect_repo = ProspectRepository(session, ctx)
    pipeline_repo = PipelineRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    prospect = await prospect_repo.get(prospect_id)
    if prospect.is_converted:
        raise HTTPException(status_code=409, detail="Prospect already converted")

    if pipeline_id is None:
        pipelines, _ = await pipeline_repo.search(limit=50)
        default = next((p for p in pipelines if p.is_default), None)
        if default is None and pipelines:
            default = pipelines[0]
        if default is None:
            raise HTTPException(status_code=400, detail="No pipeline configured")
        pipeline_id = default.id

    if stage_id is None:
        stages, _ = await stage_repo.search(limit=200)
        pipeline_stages = [
            s for s in stages
            if s.pipeline_id == pipeline_id and not s.is_won and not s.is_lost
        ]
        pipeline_stages.sort(key=lambda s: s.sequence)
        if not pipeline_stages:
            raise HTTPException(status_code=400, detail="No stages for pipeline")
        stage_id = pipeline_stages[0].id

    stage = await stage_repo.get(stage_id)
    now = _utcnow()

    lead = await lead_repo.create({
        "name": prospect.name,
        "person_id": prospect.person_id,
        "organization_id": prospect.organization_id,
        "pipeline_id": pipeline_id,
        "stage_id": stage_id,
        "assigned_user_id": prospect.assigned_user_id or ctx.user_id,
        "expected_revenue": expected_revenue,
        "probability": stage.probability,
        "stage_entered_at": now,
        "lifecycle_stage": "sql",
        **_utm_fields_from_prospect(prospect),
    })

    await prospect_repo.update(prospect_id, {
        "is_converted": True,
        "converted_lead_id": lead.id,
    })

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="crm.prospect.converted",
        payload={
            "prospect_id": str(prospect_id),
            "lead_id": str(lead.id),
        },
        target_kind="notification",
    )

    return lead.id


async def set_lead_lifecycle_stage(
    session: AsyncSession,
    ctx: RequestContext,
    lead_id: uuid.UUID,
    stage: str,
) -> str:
    """Update lead lifecycle stage with validation (SPEC-008)."""
    from modules.crm.controller.repositories import LeadRepository
    from orbiteus_core.outbox import enqueue

    normalized = normalize_lifecycle_stage(stage)
    lead_repo = LeadRepository(session, ctx)
    await lead_repo.get(lead_id)
    await lead_repo.update(lead_id, {"lifecycle_stage": normalized})

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="crm.lead.lifecycle_changed",
        payload={
            "lead_id": str(lead_id),
            "lifecycle_stage": normalized,
        },
        target_kind="notification",
    )

    logger.info(
        "crm.lead.lifecycle_changed",
        extra={"lead_id": str(lead_id), "lifecycle_stage": normalized},
    )
    return normalized


async def mark_activity_done(
    session: AsyncSession,
    ctx: RequestContext,
    activity_id: uuid.UUID,
    outcome: str = "",
) -> None:
    """Complete an activity and refresh parent lead last_activity_at."""
    from modules.crm.controller.repositories import ActivityRepository, LeadRepository

    activity_repo = ActivityRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    activity = await activity_repo.get(activity_id)
    now = _utcnow()

    await activity_repo.update(activity_id, {
        "done": True,
        "done_at": now,
        "outcome": outcome,
    })

    if activity.res_model == "crm.lead" and activity.res_id:
        await lead_repo.update(activity.res_id, {"last_activity_at": now})


async def get_rotting_leads(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID | None = None,
) -> list[dict]:
    """Leads exceeding stage.rotting_days in current stage."""
    from modules.crm.controller.repositories import LeadRepository, StageRepository

    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    stages, _ = await stage_repo.search(limit=500)
    stage_by_id = {s.id: s for s in stages}

    leads, _ = await lead_repo.search(limit=5000)
    now = _utcnow()
    rotting: list[dict] = []

    for lead in leads:
        if pipeline_id and lead.pipeline_id != pipeline_id:
            continue
        if not lead.stage_id or not lead.stage_entered_at:
            continue
        stage = stage_by_id.get(lead.stage_id)
        if not stage or stage.rotting_days is None:
            continue
        if stage.is_won or stage.is_lost:
            continue

        is_rotting, days_in_stage, rotting_reason = evaluate_lead_rotting(lead, stage, now)
        if not is_rotting:
            continue

        rotting.append({
            "lead_id": str(lead.id),
            "name": lead.name,
            "stage_name": stage.name,
            "days_in_stage": days_in_stage,
            "rotting_days": stage.rotting_days,
            "expected_revenue": lead.expected_revenue,
            "is_rotting": True,
            "rotting_reason": rotting_reason,
        })

    return rotting


async def run_queue(
    session: AsyncSession,
    ctx: RequestContext,
    queue_id: uuid.UUID,
) -> dict:
    """Execute a saved queue filter against crm.lead (SPEC-007 v1)."""
    from fastapi import HTTPException

    from modules.crm.controller.queue_filter import (
        lead_is_rotting,
        matches_domain,
        sort_leads,
    )
    from modules.crm.controller.repositories import (
        LeadRepository,
        QueueRepository,
        StageRepository,
    )

    queue_repo = QueueRepository(session, ctx)
    queue = await queue_repo.get(queue_id)

    if queue.model_name != "crm.lead":
        raise HTTPException(
            status_code=400,
            detail=f"Queue model {queue.model_name!r} is not supported in v1",
        )

    if not queue.is_shared and queue.user_id and ctx.user_id and queue.user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="Queue is private to another user")

    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    stages, _ = await stage_repo.search(limit=500)
    stage_by_id = {s.id: s for s in stages}

    leads, _ = await lead_repo.search(limit=5000)
    now = _utcnow()
    domain = queue.domain_json or {}
    matched: list[dict] = []

    for lead in leads:
        if not matches_domain(
            lead,
            domain,
            ctx=ctx,
            stage_by_id=stage_by_id,
            now=now,
        ):
            continue

        stage = stage_by_id.get(lead.stage_id) if lead.stage_id else None
        is_rotting = lead_is_rotting(lead, stage, now)
        days_in_stage = None
        if lead.stage_entered_at and stage and not stage.is_won and not stage.is_lost:
            days_in_stage = (now - lead.stage_entered_at).days

        matched.append({
            "id": str(lead.id),
            "name": lead.name,
            "stage_id": str(lead.stage_id) if lead.stage_id else None,
            "assigned_user_id": str(lead.assigned_user_id) if lead.assigned_user_id else None,
            "expected_revenue": lead.expected_revenue,
            "probability": lead.probability,
            "expected_close_date": (
                lead.expected_close_date.isoformat() if lead.expected_close_date else None
            ),
            "last_activity_at": (
                lead.last_activity_at.isoformat() if lead.last_activity_at else None
            ),
            "is_rotting": is_rotting,
            "days_in_stage": days_in_stage,
        })

    matched = sort_leads(matched, queue.sort_json or {})

    return {
        "queue_id": str(queue.id),
        "queue_name": queue.name,
        "model_name": queue.model_name,
        "count": len(matched),
        "leads": matched,
    }
