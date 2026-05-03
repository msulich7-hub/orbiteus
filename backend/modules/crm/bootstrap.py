"""CRM module bootstrap — runs on first install per tenant.

Seeds default stages and a default team. Replaces the legacy
`_seed_crm_defaults` in `backend/api.py` (PR 9 / ADR-0008).

Called by `ModuleRegistry` after `_register_routes()` finishes.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


_DEFAULT_STAGES = [
    {"name": "New",        "sequence": 10, "probability": 5.0,   "is_won": False, "is_lost": False},
    {"name": "Qualified",  "sequence": 20, "probability": 30.0,  "is_won": False, "is_lost": False},
    {"name": "Proposal",   "sequence": 30, "probability": 55.0,  "is_won": False, "is_lost": False},
    {"name": "Negotiation","sequence": 40, "probability": 75.0,  "is_won": False, "is_lost": False},
    {"name": "Won",        "sequence": 90, "probability": 100.0, "is_won": True,  "is_lost": False},
    {"name": "Lost",       "sequence": 100,"probability": 0.0,   "is_won": False, "is_lost": True},
]

_DEFAULT_TEAM_NAME = "Sales"


async def on_install(session: AsyncSession, ctx: RequestContext) -> None:
    """Seed defaults the first time CRM runs for a tenant.

    Idempotent: re-running is a no-op when seeds already exist.
    """
    from modules.crm.controller.repositories import StageRepository, TeamRepository

    stage_repo = StageRepository(session, ctx)
    team_repo = TeamRepository(session, ctx)

    existing_stages, total_stages = await stage_repo.search(limit=1)
    if total_stages == 0:
        for s in _DEFAULT_STAGES:
            await stage_repo.create(s)

    existing_teams, total_teams = await team_repo.search(limit=1)
    if total_teams == 0:
        await team_repo.create({"name": _DEFAULT_TEAM_NAME, "description": "Default sales team"})

    await session.commit()
    logger.info("crm.bootstrap.seeded", extra={"tenant_id": str(ctx.tenant_id)})
