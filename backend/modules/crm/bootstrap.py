"""CRM module bootstrap — pipeline, stages, team, automation (SPEC-001..006)."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


_DEFAULT_PIPELINE = {
    "name": "Sales",
    "sequence": 10,
    "is_default": True,
    "color": "#228be6",
}

_DEFAULT_STAGES = [
    {"name": "New",         "sequence": 10, "probability": 5.0,   "is_won": False, "is_lost": False, "rotting_days": 7},
    {"name": "Qualified",   "sequence": 20, "probability": 30.0,  "is_won": False, "is_lost": False, "rotting_days": 14},
    {
        "name": "Proposal",
        "sequence": 30,
        "probability": 55.0,
        "is_won": False,
        "is_lost": False,
        "rotting_days": 21,
        "required_fields_json": ["expected_close_date"],
    },
    {"name": "Negotiation", "sequence": 40, "probability": 75.0,  "is_won": False, "is_lost": False, "rotting_days": 14},
    {"name": "Won",         "sequence": 90, "probability": 100.0, "is_won": True,  "is_lost": False, "rotting_days": None},
    {"name": "Lost",        "sequence": 100,"probability": 0.0,   "is_won": False, "is_lost": True,  "rotting_days": None},
]

_DEFAULT_TEAM_NAME = "Sales"

_DEFAULT_QUEUES = [
    {
        "name": "My rotting",
        "model_name": "crm.lead",
        "domain_json": {"assigned_user_id": "current_user", "is_rotting": True},
        "sort_json": {"field": "expected_revenue", "order": "desc"},
        "is_shared": True,
        "sequence": 10,
    },
    {
        "name": "Closing this month",
        "model_name": "crm.lead",
        "domain_json": {"expected_close_date__month": "current"},
        "sort_json": {"field": "expected_close_date", "order": "asc"},
        "is_shared": True,
        "sequence": 20,
    },
    {
        "name": "No activity 7d",
        "model_name": "crm.lead",
        "domain_json": {"last_activity_at__inactive_days__gte": 7},
        "sort_json": {"field": "last_activity_at", "order": "asc"},
        "is_shared": True,
        "sequence": 30,
    },
]

_DEMO_AUTOMATION_RULE = {
    "name": "Follow up when moved to Proposal",
    "trigger_event": "crm.lead.stage_changed",
    "condition_json": {"to_stage_name": "Proposal"},
    "action_type": "create_activity",
    "action_json": {
        "subject": "Follow up on proposal",
        "activity_type": "task",
    },
    "active": True,
}


async def on_install(session: AsyncSession, ctx: RequestContext) -> None:
    """Seed defaults the first time CRM runs for a tenant."""
    from modules.base.controller.repositories import TenantRepository
    from modules.crm.controller.repositories import (
        AutomationRuleRepository,
        PipelineRepository,
        QueueRepository,
        StageRepository,
        TeamRepository,
    )

    tenant_repo = TenantRepository(session, ctx)
    tenants, _ = await tenant_repo.search(limit=1)
    if not tenants:
        logger.warning("crm.bootstrap.skipped_no_tenant")
        return

    tenant_ctx = RequestContext(
        is_superadmin=True,
        tenant_id=tenants[0].id,
        user_id=ctx.user_id,
    )

    pipeline_repo = PipelineRepository(session, tenant_ctx)
    stage_repo = StageRepository(session, tenant_ctx)
    team_repo = TeamRepository(session, tenant_ctx)
    automation_repo = AutomationRuleRepository(session, tenant_ctx)
    queue_repo = QueueRepository(session, tenant_ctx)

    _, total_pipelines = await pipeline_repo.search(limit=1)
    pipeline_id = None

    if total_pipelines == 0:
        pipeline = await pipeline_repo.create(_DEFAULT_PIPELINE)
        pipeline_id = pipeline.id
    else:
        pipelines, _ = await pipeline_repo.search(limit=10)
        default = next((p for p in pipelines if p.is_default), pipelines[0])
        pipeline_id = default.id

    existing_stages, total_stages = await stage_repo.search(limit=1)
    if total_stages == 0:
        for s in _DEFAULT_STAGES:
            await stage_repo.create({**s, "pipeline_id": pipeline_id})
    else:
        # Backfill pipeline_id on orphan stages from pre-SPEC migration.
        stages, _ = await stage_repo.search(limit=500)
        for stage in stages:
            if stage.pipeline_id is None and pipeline_id:
                await stage_repo.update(stage.id, {"pipeline_id": pipeline_id})
            if stage.name == "Proposal" and not (stage.required_fields_json or []):
                await stage_repo.update(
                    stage.id,
                    {"required_fields_json": ["expected_close_date"]},
                )

    _, total_teams = await team_repo.search(limit=1)
    if total_teams == 0:
        await team_repo.create({"name": _DEFAULT_TEAM_NAME, "description": "Default sales team"})

    existing_rules, _ = await automation_repo.search(limit=500)
    rule_names = {r.name for r in existing_rules}
    if _DEMO_AUTOMATION_RULE["name"] not in rule_names:
        stages, _ = await stage_repo.search(limit=500)
        if any(s.name == "Proposal" for s in stages):
            await automation_repo.create(_DEMO_AUTOMATION_RULE)

    existing_queues, _ = await queue_repo.search(limit=500)
    queue_names = {q.name for q in existing_queues}
    for q in _DEFAULT_QUEUES:
        if q["name"] not in queue_names:
            await queue_repo.create(q)

    await session.commit()
    logger.info("crm.bootstrap.seeded", extra={"tenant_id": str(tenant_ctx.tenant_id)})
