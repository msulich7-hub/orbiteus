"""CRM AIModuleConfig — declarative AI surface (PR 9, canonical example)."""
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
        "Always cite source records as `<model>.<id>` when referring to specific "
        "leads or persons. Honour RBAC; never widen access on behalf of the user."
    ),
    accessible_models=["crm.person", "crm.lead", "crm.stage", "crm.team"],
    callable_actions=[
        "crm.person.create",
        "crm.lead.create",
        "crm.lead.move_stage",
    ],
    embed_models=["crm.person", "crm.lead"],
    suggested_prompts=[
        PromptTemplate(id="hot_leads", label="Hot leads this week"),
        PromptTemplate(id="weekly_summary", label="Weekly team summary"),
        PromptTemplate(id="rotting", label="Leads stuck > 14 days"),
    ],
    dashboard=True,
)

# Register at import time so module bootstrap picks it up automatically.
ai_registry.register("crm", AI)


# ---------------------------------------------------------------------------
# AI tool dispatchers (DoD §8.10) — Python handlers that execute the
# `callable_actions` declared above when the model invokes them.
#
# Every handler:
#   * receives the SAME `session` + `ctx` the chat request runs under
#     (no elevated AI context),
#   * forwards to the canonical service / repository function so RBAC,
#     tenant filter, and audit row apply automatically,
#   * returns a JSON-serialisable dict for the chat layer to surface in
#     `tool_results`.
# ---------------------------------------------------------------------------


async def _crm_lead_move_stage(
    session: AsyncSession,
    ctx: RequestContext,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Move a `crm.lead` to a different `crm.stage`.

    Validates UUID inputs strictly. Re-raising would propagate as
    `ai.dispatcher.handler_failed` from the dispatcher; we let
    UUID parsing errors flow up so the AI sees the failure shape
    on the next turn.
    """
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
