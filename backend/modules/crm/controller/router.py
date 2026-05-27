"""CRM custom endpoints — kanban, move, convert, rotting, activities."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth

from modules.crm.model.schemas import EmailLogWrite, LeadMoveRequest, ProspectConvertRequest

router = APIRouter(tags=["crm"])


@router.get("/leads/forecast")
async def leads_forecast(
    pipeline_id: uuid.UUID | None = Query(None),
    months_ahead: int = Query(6, ge=1, le=24),
    assigned_user_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Weighted revenue forecast grouped by expected close month."""
    from modules.crm.controller.forecast import build_leads_forecast

    return await build_leads_forecast(
        session,
        ctx,
        pipeline_id=pipeline_id,
        months_ahead=months_ahead,
        assigned_user_id=assigned_user_id,
    )


@router.get("/leads/kanban")
async def leads_kanban(
    pipeline_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Group leads by stage for kanban — optional pipeline filter."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        PipelineRepository,
        StageRepository,
    )
    from modules.crm.controller.services import (
        batch_resolve_lead_display_names,
        evaluate_lead_rotting,
    )

    pipeline_repo = PipelineRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    if pipeline_id is None:
        pipelines, _ = await pipeline_repo.search(limit=50)
        default = next((p for p in pipelines if p.is_default), None)
        if default:
            pipeline_id = default.id

    stages, _ = await stage_repo.search(limit=200)
    if pipeline_id:
        stages = [s for s in stages if s.pipeline_id == pipeline_id]

    leads, _ = await lead_repo.search(limit=5000)
    if pipeline_id:
        leads = [l for l in leads if l.pipeline_id == pipeline_id]

    person_names, org_names, user_names = await batch_resolve_lead_display_names(
        session, ctx, leads
    )

    by_stage: dict[str, list] = {}
    for lead in leads:
        if lead.stage_id is None:
            continue
        by_stage.setdefault(str(lead.stage_id), []).append(lead)

    columns = []
    total_revenue = 0.0
    now = datetime.now(timezone.utc)

    for stage in sorted(stages, key=lambda s: s.sequence):
        bucket = by_stage.get(str(stage.id), [])
        revenue = sum(l.expected_revenue for l in bucket)
        total_revenue += revenue

        stage_leads = []
        for lead in bucket:
            is_rotting, days_in_stage, rotting_reason = evaluate_lead_rotting(
                lead, stage, now
            )

            stage_leads.append({
                "id": str(lead.id),
                "name": lead.name,
                "expected_revenue": lead.expected_revenue,
                "probability": lead.probability,
                "person_id": str(lead.person_id) if lead.person_id else None,
                "organization_id": str(lead.organization_id) if lead.organization_id else None,
                "person_name": person_names.get(lead.person_id) if lead.person_id else None,
                "organization_name": (
                    org_names.get(lead.organization_id) if lead.organization_id else None
                ),
                "assigned_user_id": str(lead.assigned_user_id) if lead.assigned_user_id else None,
                "assigned_user_name": (
                    user_names.get(lead.assigned_user_id) if lead.assigned_user_id else None
                ),
                "expected_close_date": (
                    lead.expected_close_date.isoformat() if lead.expected_close_date else None
                ),
                "is_rotting": is_rotting,
                "days_in_stage": days_in_stage,
                "rotting_reason": rotting_reason,
                "score": lead.score or 0,
            })

        columns.append({
            "stage_id": str(stage.id),
            "stage_name": stage.name,
            "sequence": stage.sequence,
            "probability": stage.probability,
            "is_won": stage.is_won,
            "is_lost": stage.is_lost,
            "rotting_days": stage.rotting_days,
            "count": len(bucket),
            "expected_revenue": revenue,
            "leads": stage_leads,
        })

    return {
        "pipeline_id": str(pipeline_id) if pipeline_id else None,
        "columns": columns,
        "total_leads": sum(c["count"] for c in columns),
        "total_expected_revenue": total_revenue,
    }


@router.patch("/lead/{lead_id}/lifecycle")
async def patch_lead_lifecycle(
    lead_id: uuid.UUID,
    stage: str = Query(..., description="subscriber|lead|mql|sql|opportunity|customer"),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Set lead lifecycle stage (HubSpot-style MQL/SQL funnel)."""
    from modules.crm.controller.services import set_lead_lifecycle_stage

    lifecycle_stage = await set_lead_lifecycle_stage(session, ctx, lead_id, stage)
    await session.commit()
    return {
        "message": "Lifecycle updated",
        "lead_id": str(lead_id),
        "lifecycle_stage": lifecycle_stage,
    }


@router.post("/lead/{lead_id}/move")
async def move_lead(
    lead_id: uuid.UUID,
    stage_id: uuid.UUID,
    lost_reason: str | None = Query(None),
    body: LeadMoveRequest | None = None,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Move a lead to a different stage."""
    from modules.crm.controller.services import move_lead_to_stage

    reason = lost_reason if lost_reason is not None else (body.lost_reason if body else "")
    await move_lead_to_stage(session, ctx, lead_id, stage_id, lost_reason=reason)
    await session.commit()
    return {"message": "Lead moved", "lead_id": str(lead_id), "stage_id": str(stage_id)}


@router.post("/leads/recalculate-scores")
async def recalculate_lead_scores(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Batch-recalculate lead and prospect scores for the current tenant (admin only)."""
    if not ctx.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin required")

    from modules.crm.controller.scoring import recalculate_all_scores

    updated = await recalculate_all_scores(session, ctx)
    await session.commit()
    return {"updated": updated}


@router.post("/prospect/{prospect_id}/convert")
async def convert_prospect(
    prospect_id: uuid.UUID,
    body: ProspectConvertRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Convert prospect inbox item to pipeline deal."""
    from modules.crm.controller.services import convert_prospect_to_lead

    lead_id = await convert_prospect_to_lead(
        session,
        ctx,
        prospect_id,
        pipeline_id=body.pipeline_id,
        stage_id=body.stage_id,
        expected_revenue=body.expected_revenue,
    )
    await session.commit()
    return {"message": "Prospect converted", "lead_id": str(lead_id)}


@router.get("/leads/rotting")
async def rotting_leads(
    pipeline_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Stale deals exceeding rotting threshold per stage."""
    from modules.crm.controller.services import get_rotting_leads

    items = await get_rotting_leads(session, ctx, pipeline_id)
    return {"count": len(items), "leads": items}


@router.get("/lead/{lead_id}/stage-history")
async def lead_stage_history(
    lead_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Stage transition audit for a lead."""
    from modules.crm.controller.repositories import LeadRepository, StageHistoryRepository

    lead_repo = LeadRepository(session, ctx)
    await lead_repo.get(lead_id)

    repo = StageHistoryRepository(session, ctx)
    rows, _ = await repo.search(
        domain=[("lead_id", "=", str(lead_id))],
        limit=200,
        order_by="changed_at",
        order_dir="asc",
    )

    return {
        "lead_id": str(lead_id),
        "count": len(rows),
        "history": [
            {
                "id": str(h.id),
                "from_stage_id": str(h.from_stage_id) if h.from_stage_id else None,
                "to_stage_id": str(h.to_stage_id),
                "changed_by_id": str(h.changed_by_id) if h.changed_by_id else None,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
            }
            for h in rows
        ],
    }


@router.get("/lead/{lead_id}/timeline")
async def lead_timeline(
    lead_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Chronological merge of stage history and activities for a lead."""
    from modules.crm.controller.repositories import (
        ActivityRepository,
        LeadRepository,
        StageHistoryRepository,
    )

    lead_repo = LeadRepository(session, ctx)
    await lead_repo.get(lead_id)

    history_repo = StageHistoryRepository(session, ctx)
    activity_repo = ActivityRepository(session, ctx)

    history_rows, _ = await history_repo.search(
        domain=[("lead_id", "=", str(lead_id))],
        limit=500,
    )
    activities, _ = await activity_repo.search(
        domain=[
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", str(lead_id)),
        ],
        limit=500,
    )

    timeline: list[dict] = []
    min_dt = datetime.min.replace(tzinfo=timezone.utc)

    for h in history_rows:
        timeline.append({
            "type": "stage_change",
            "timestamp": h.changed_at.isoformat() if h.changed_at else None,
            "sort_at": h.changed_at or min_dt,
            "id": str(h.id),
            "from_stage_id": str(h.from_stage_id) if h.from_stage_id else None,
            "to_stage_id": str(h.to_stage_id),
            "changed_by_id": str(h.changed_by_id) if h.changed_by_id else None,
        })

    for act in activities:
        sort_at = act.done_at or act.due_date or act.create_date or min_dt
        timeline.append({
            "type": "activity",
            "timestamp": sort_at.isoformat() if sort_at != min_dt else None,
            "sort_at": sort_at,
            "id": str(act.id),
            "subject": act.subject,
            "activity_type": act.activity_type,
            "done": act.done,
            "due_date": act.due_date.isoformat() if act.due_date else None,
            "done_at": act.done_at.isoformat() if act.done_at else None,
            "outcome": act.outcome or "",
        })

    timeline.sort(key=lambda item: item.pop("sort_at", min_dt))

    return {
        "lead_id": str(lead_id),
        "count": len(timeline),
        "timeline": timeline,
    }


def _serialize_email_log(row) -> dict:
    return {
        "id": str(row.id),
        "lead_id": str(row.lead_id) if row.lead_id else None,
        "prospect_id": str(row.prospect_id) if row.prospect_id else None,
        "direction": row.direction,
        "from_address": row.from_address,
        "to_address": row.to_address,
        "cc": row.cc,
        "subject": row.subject,
        "body": row.body,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "created_by_id": str(row.created_by_id) if row.created_by_id else None,
        "create_date": row.create_date.isoformat() if row.create_date else None,
    }


async def _create_email_log(
    session: AsyncSession,
    ctx: RequestContext,
    body: EmailLogWrite,
    *,
    lead_id: uuid.UUID | None = None,
    prospect_id: uuid.UUID | None = None,
) -> dict:
    from modules.crm.controller.repositories import (
        EmailLogRepository,
        LeadRepository,
        ProspectRepository,
    )
    from orbiteus_core.outbox import enqueue

    if lead_id is not None:
        lead_repo = LeadRepository(session, ctx)
        await lead_repo.get(lead_id)
    if prospect_id is not None:
        prospect_repo = ProspectRepository(session, ctx)
        await prospect_repo.get(prospect_id)

    sent_at = body.sent_at or datetime.now(timezone.utc)
    email_repo = EmailLogRepository(session, ctx)
    row = await email_repo.create({
        "lead_id": lead_id,
        "prospect_id": prospect_id,
        "direction": body.direction,
        "from_address": body.from_address,
        "to_address": body.to_address,
        "cc": body.cc,
        "subject": body.subject,
        "body": body.body,
        "sent_at": sent_at,
    })

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="crm.email.logged",
        payload={
            "email_log_id": str(row.id),
            "lead_id": str(lead_id) if lead_id else None,
            "prospect_id": str(prospect_id) if prospect_id else None,
            "direction": row.direction,
            "from_address": row.from_address,
            "to_address": row.to_address,
            "subject": row.subject,
        },
        target_kind="notification",
    )

    await session.commit()
    return {"id": str(row.id), "created": True}


async def _list_email_logs(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    lead_id: uuid.UUID | None = None,
    prospect_id: uuid.UUID | None = None,
) -> dict:
    from modules.crm.controller.repositories import (
        EmailLogRepository,
        LeadRepository,
        ProspectRepository,
    )

    if lead_id is not None:
        lead_repo = LeadRepository(session, ctx)
        await lead_repo.get(lead_id)
        domain = [("lead_id", "=", str(lead_id))]
        resource_key = "lead_id"
        resource_id = lead_id
    else:
        assert prospect_id is not None
        prospect_repo = ProspectRepository(session, ctx)
        await prospect_repo.get(prospect_id)
        domain = [("prospect_id", "=", str(prospect_id))]
        resource_key = "prospect_id"
        resource_id = prospect_id

    email_repo = EmailLogRepository(session, ctx)
    rows, total = await email_repo.search(
        domain=domain,
        limit=50,
        order_by="sent_at",
        order_dir="desc",
    )
    return {
        resource_key: str(resource_id),
        "count": total,
        "emails": [_serialize_email_log(row) for row in rows],
    }


@router.post("/lead/{lead_id}/email")
async def log_lead_email(
    lead_id: uuid.UUID,
    body: EmailLogWrite,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Log an email against a deal (stub — no SMTP)."""
    return await _create_email_log(session, ctx, body, lead_id=lead_id)


@router.get("/lead/{lead_id}/emails")
async def list_lead_emails(
    lead_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """List recent emails logged for a deal."""
    return await _list_email_logs(session, ctx, lead_id=lead_id)


@router.post("/prospect/{prospect_id}/email")
async def log_prospect_email(
    prospect_id: uuid.UUID,
    body: EmailLogWrite,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Log an email against a prospect (stub — no SMTP)."""
    return await _create_email_log(session, ctx, body, prospect_id=prospect_id)


@router.get("/prospect/{prospect_id}/emails")
async def list_prospect_emails(
    prospect_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """List recent emails logged for a prospect."""
    return await _list_email_logs(session, ctx, prospect_id=prospect_id)


@router.get("/activities/today")
async def activities_today(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Today's activity queue for current user."""
    from modules.crm.controller.repositories import ActivityRepository

    repo = ActivityRepository(session, ctx)
    activities, _ = await repo.search(limit=500)
    today = date.today()

    queue = []
    for act in activities:
        if act.done:
            continue
        if act.assigned_user_id and ctx.user_id and act.assigned_user_id != ctx.user_id:
            continue
        if act.due_date and act.due_date.date() <= today:
            queue.append({
                "id": str(act.id),
                "subject": act.subject,
                "activity_type": act.activity_type,
                "due_date": act.due_date.isoformat() if act.due_date else None,
                "res_model": act.res_model,
                "res_id": str(act.res_id) if act.res_id else None,
            })

    queue.sort(key=lambda x: x["due_date"] or "")
    return {"count": len(queue), "activities": queue}


@router.post("/activity/{activity_id}/done")
async def activity_done(
    activity_id: uuid.UUID,
    outcome: str = "",
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Mark activity complete."""
    from modules.crm.controller.services import mark_activity_done

    await mark_activity_done(session, ctx, activity_id, outcome)
    await session.commit()
    return {"message": "Activity completed", "activity_id": str(activity_id)}


@router.get("/queue/{queue_id}/run")
async def run_work_queue(
    queue_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Run a saved work queue and return matching leads."""
    from modules.crm.controller.services import run_queue

    result = await run_queue(session, ctx, queue_id)
    return result


@router.get("/lead/export.csv")
async def export_leads_csv_endpoint(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> StreamingResponse:
    """Export leads as CSV (SPEC-012)."""
    from modules.crm.controller.csv_io import export_leads_csv

    content = await export_leads_csv(session, ctx)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


@router.get("/prospect/export.csv")
async def export_prospects_csv_endpoint(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> StreamingResponse:
    """Export prospects as CSV (SPEC-012)."""
    from modules.crm.controller.csv_io import export_prospects_csv

    content = await export_prospects_csv(session, ctx)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="prospects.csv"'},
    )


@router.post("/prospect/import")
async def import_prospects_csv_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Import prospects from CSV upload (SPEC-012)."""
    from modules.crm.controller.csv_io import import_prospects_csv

    file_bytes = await file.read()
    result = await import_prospects_csv(session, ctx, file_bytes)
    await session.commit()
    return result


@router.get("/stats")
async def crm_stats(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Dashboard statistics."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        OrganizationRepository,
        PersonRepository,
        ProspectRepository,
    )
    from modules.crm.controller.services import get_rotting_leads

    person_repo = PersonRepository(session, ctx)
    org_repo = OrganizationRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)
    prospect_repo = ProspectRepository(session, ctx)

    _, total_persons = await person_repo.search(limit=1)
    _, total_orgs = await org_repo.search(limit=1)
    leads, total_leads = await lead_repo.search(limit=2000)
    prospects, _ = await prospect_repo.search(limit=2000)
    open_prospects = sum(1 for p in prospects if not p.is_converted)

    won = [l for l in leads if l.probability == 100.0]
    pipeline_value = sum(l.expected_revenue for l in leads)
    rotting = await get_rotting_leads(session, ctx)

    return {
        "total_persons": total_persons,
        "total_organizations": total_orgs,
        "total_leads": total_leads,
        "open_prospects": open_prospects,
        "rotting_leads": len(rotting),
        "won_leads": len(won),
        "pipeline_value": pipeline_value,
        "won_revenue": sum(l.expected_revenue for l in won),
    }
