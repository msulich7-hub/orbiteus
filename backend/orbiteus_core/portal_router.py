"""Public portal endpoints (PR 12).

`/api/portal/exchange?token=<jwt>` validates a share-link token and
returns a minimal payload describing the shared resource. The portal-ui
front-end consumes the response and renders the resource read-only by
default.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from orbiteus_core.db import get_session
from orbiteus_core.sharing import decode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.get("/exchange")
async def exchange(
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Validate a share-link token and return a minimal resource payload."""
    try:
        payload = decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Resolve the resource against the engine's registered models.
    from orbiteus_core.auto_router import _model_registry  # type: ignore[attr-defined]

    entry = _model_registry.get(payload.resource_model)
    if entry is None:
        raise HTTPException(status_code=404, detail="resource model not registered")

    table = entry["table"]
    row = (
        await session.execute(
            select(table).where(table.c.id == payload.resource_id)
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="resource not found")

    if row.get("tenant_id") and str(row["tenant_id"]) != str(payload.tenant_id):
        raise HTTPException(status_code=403, detail="cross-tenant share rejected")

    safe_payload: dict = {}
    for key, value in row.items():
        if key in {"id", "tenant_id", "company_id", "create_date", "write_date"}:
            continue
        # Stringify uuids/datetimes so the JSON encoder is happy.
        safe_payload[key] = str(value) if hasattr(value, "isoformat") or hasattr(value, "hex") else value

    return {
        "resource_model": payload.resource_model,
        "resource_id": str(payload.resource_id),
        "permissions": payload.permissions,
        "payload": safe_payload,
    }
