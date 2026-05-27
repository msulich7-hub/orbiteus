"""Shipping module bootstrap — IFS tenant config param seed."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

IFS_TENANT_SLUG_KEY = "shipping.ifs_tenant_slug"


async def on_install(session: AsyncSession, ctx: RequestContext) -> None:
    """Seed global config for IFS ingest tenant resolution."""
    from modules.base.controller.repositories import IrConfigParamRepository

    repo = IrConfigParamRepository(session, ctx)
    rows, total = await repo.search([("key", "=", IFS_TENANT_SLUG_KEY)], limit=1)
    if total < 1:
        await repo.create(
            {
                "key": IFS_TENANT_SLUG_KEY,
                "value": "",
                "description": (
                    "Tenant slug for Oracle IFS webhook ingest (empty = first active tenant)"
                ),
            }
        )
        logger.info("shipping.bootstrap: seeded %s", IFS_TENANT_SLUG_KEY)
    else:
        logger.info("shipping.bootstrap: %s already present", IFS_TENANT_SLUG_KEY)
