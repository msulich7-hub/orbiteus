"""Inventory custom API — location tree (WMS-T02)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.exceptions import AccessDenied, NotFound, ValidationError
from orbiteus_core.security.middleware import require_auth

from modules.inventory.controller.location_services import get_location_tree
from modules.inventory.controller.repositories import LocationRepository
from modules.inventory.model.schemas import LocationRead, LocationWrite

router = APIRouter(tags=["inventory"])


@router.get("/locations/tree")
async def locations_tree(
    warehouse_id: uuid.UUID = Query(..., description="Warehouse UUID"),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Nested location tree for a warehouse (zone → aisle → bin)."""
    try:
        return await get_location_tree(session, ctx, warehouse_id)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post(
    "/locations",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create location (bin/zone) with barcode validation",
)
async def create_location(
    body: LocationWrite,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> LocationRead:
    """Spec alias for POST /locations — same rules as auto-CRUD /location."""
    repo = LocationRepository(session, ctx)
    try:
        obj = await repo.create(body.model_dump(exclude_unset=True))
        return LocationRead.model_validate(obj, from_attributes=True)
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
