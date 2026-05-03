"""CRM business logic (canonical: Person/Lead/Stage/Team).

Background side effects (won/lost notifications, follow-ups, audit fan-out)
go through the Outbox + Celery worker (ADR-0010, ADR-0013, ADR-0015).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


async def move_lead_to_stage(
    session: AsyncSession,
    ctx: RequestContext,
    lead_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> None:
    """Move a lead to a new stage.

    Won/lost transitions emit a `crm.lead.closed` outbox event for downstream
    Celery handlers (notifications, KPI rollups, AI summarization).
    """
    from modules.crm.controller.repositories import LeadRepository, StageRepository
    from orbiteus_core.outbox import enqueue

    lead_repo = LeadRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)

    lead = await lead_repo.get(lead_id)  # noqa: F841
    stage = await stage_repo.get(stage_id)

    await lead_repo.update(
        lead_id,
        {"stage_id": stage_id, "probability": stage.probability},
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
