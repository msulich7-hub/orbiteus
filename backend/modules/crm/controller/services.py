"""CRM business logic.

Background side effects (won/lost notifications, follow-ups, audit fan-out)
go through the Outbox + Celery worker (ADR-0010, ADR-0013, ADR-0015).
Direct in-process workflow engines are not used in MVP.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


async def move_opportunity_to_stage(
    session: AsyncSession,
    ctx: RequestContext,
    opportunity_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> None:
    """Move an opportunity to a new stage.

    Won/lost transitions emit a `crm.opportunity.closed` outbox event, which
    Celery workers consume to trigger downstream notifications.
    """
    from modules.crm.controller.repositories import OpportunityRepository, StageRepository
    from orbiteus_core.outbox import enqueue

    opp_repo = OpportunityRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)

    opportunity = await opp_repo.get(opportunity_id)  # noqa: F841
    stage = await stage_repo.get(stage_id)

    await opp_repo.update(
        opportunity_id,
        {"stage_id": stage_id, "probability": stage.probability},
    )

    if stage.is_won or stage.is_lost:
        await enqueue(
            session,
            tenant_id=ctx.tenant_id,
            event="crm.opportunity.closed",
            payload={
                "opportunity_id": str(opportunity_id),
                "outcome": "won" if stage.is_won else "lost",
                "stage_id": str(stage_id),
            },
            target_kind="notification",
        )

    logger.info("Opportunity %s moved to stage %s", opportunity_id, stage.name)
