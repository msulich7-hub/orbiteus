"""CRM AIModuleConfig — Pipedrive-class assistant surface."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.config import AIModuleConfig, PromptTemplate, ai_registry
from orbiteus_core.ai.dispatcher import register_handler
from orbiteus_core.context import RequestContext

AI = AIModuleConfig(
    enabled=True,
    system_prompt=(
        "You are the CRM assistant for {{ tenant.name }}. "
        "Deals live in pipelines (crm.lead); pre-pipeline items are crm.prospect. "
        "Cite records as `<model>.<id>`. Honour RBAC."
    ),
    accessible_models=[
        "crm.organization",
        "crm.pipeline",
        "crm.person",
        "crm.lead",
        "crm.prospect",
        "crm.stage",
        "crm.team",
        "crm.activity",
    ],
    callable_actions=[
        "crm.person.create",
        "crm.lead.create",
        "crm.lead.move_stage",
        "crm.prospect.create",
    ],
    embed_models=["crm.person", "crm.lead", "crm.organization", "crm.prospect"],
    suggested_prompts=[
        PromptTemplate(id="hot_leads", label="Hot deals this week"),
        PromptTemplate(id="weekly_summary", label="Weekly team summary"),
        PromptTemplate(id="rotting", label="Deals stuck beyond rotting threshold"),
        PromptTemplate(id="prospect_inbox", label="Open prospects in inbox"),
    ],
    dashboard=True,
)

ai_registry.register("crm", AI)


async def _crm_lead_move_stage(
    session: AsyncSession,
    ctx: RequestContext,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    from modules.crm.controller.services import move_lead_to_stage

    lead_id = uuid.UUID(str(arguments["id"]))
    stage_id = uuid.UUID(str(arguments["stage_id"]))

    await move_lead_to_stage(session, ctx, lead_id, stage_id)
    await session.commit()

    return {
        "lead_id": str(lead_id),
        "stage_id": str(stage_id),
        "message": "Lead moved",
    }


register_handler("crm.lead.move_stage", _crm_lead_move_stage)
