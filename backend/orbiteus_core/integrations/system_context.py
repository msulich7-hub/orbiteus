"""System RequestContext for inbound integrations (webhooks, cron)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

IFS_TENANT_SLUG_KEY = "shipping.ifs_tenant_slug"


async def _resolve_ifs_tenant_id(session: AsyncSession, bootstrap: RequestContext) -> uuid.UUID:
    """Resolve tenant for IFS ingest from ir_config_param or first active tenant."""
    from modules.base.controller.repositories import IrConfigParamRepository, TenantRepository

    cfg_repo = IrConfigParamRepository(session, bootstrap)
    rows, total = await cfg_repo.search([("key", "=", IFS_TENANT_SLUG_KEY)], limit=1)
    if total > 0 and (rows[0].value or "").strip():
        slug = rows[0].value.strip()
        tenant_repo = TenantRepository(session, bootstrap)
        tenants, t_total = await tenant_repo.search(
            [("slug", "=", slug), ("is_active", "=", True)],
            limit=1,
        )
        if t_total > 0 and tenants:
            return tenants[0].id

    tenant_repo = TenantRepository(session, bootstrap)
    tenants, t_total = await tenant_repo.search([("is_active", "=", True)], limit=1, order_by="create_date")
    if t_total < 1 or not tenants:
        raise RuntimeError("IFS ingest requires at least one active tenant (bootstrap default tenant)")
    return tenants[0].id


async def system_tenant_context(
    session: AsyncSession,
    *,
    request_id: str | None = None,
) -> RequestContext:
    """Build actor=system context bound to configured or bootstrap tenant."""
    bootstrap = RequestContext(actor="system", is_superadmin=True, request_id=request_id)
    tenant_id = await _resolve_ifs_tenant_id(session, bootstrap)
    return RequestContext(
        actor="system",
        is_superadmin=True,
        tenant_id=tenant_id,
        request_id=request_id,
    )
