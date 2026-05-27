"""Shipping custom API — simulate routing, dispatch labels (async via outbox)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth

from modules.shipping.controller.ifs_webhook_router import router as ifs_webhook_router
from modules.shipping.controller.services import (
    dispatch_for_order,
    dispatch_from_ifs_queue,
    list_ifs_queue,
    simulate_routing,
)
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.model.schemas import (
    CarrierStatusResponse,
    DispatchAcceptedResponse,
    DispatchBody,
    IfsQueueDispatchBody,
    IfsQueueRowRead,
    SimulateBody,
)

router = APIRouter(tags=["shipping"])
router.include_router(ifs_webhook_router, prefix="/ifs")


@router.get("/carriers/status", response_model=CarrierStatusResponse)
async def carriers_status(
    ctx: RequestContext = Depends(require_auth),
) -> CarrierStatusResponse:
    cfg = get_carrier_settings()
    return CarrierStatusResponse(
        configured_carriers=cfg.configured_carriers(),
        routing_defaults={
            "LOGISTICS_PALLET_CARRIER": cfg.logistics_pallet_carrier,
            "LOGISTICS_HEAVY_KG": cfg.logistics_heavy_kg,
            "LOGISTICS_LIGHT_MAX_KG": cfg.logistics_light_max_kg,
            "LOGISTICS_RESPECT_IFS_AGENT": cfg.logistics_respect_ifs_agent,
        },
    )


@router.post("/simulate")
async def simulate(
    body: SimulateBody,
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    return await simulate_routing(body)


@router.post(
    "/dispatch",
    response_model=DispatchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch(
    body: DispatchBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchAcceptedResponse:
    result = await dispatch_for_order(session, ctx, body)
    await session.commit()
    return DispatchAcceptedResponse(**result)


@router.get("/ifs/queue", response_model=list[IfsQueueRowRead])
async def ifs_queue_list(
    state: str | None = "queued",
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> list[IfsQueueRowRead]:
    rows = await list_ifs_queue(session, ctx, state=state, limit=limit)
    return [IfsQueueRowRead.model_validate(r) for r in rows]


@router.post(
    "/ifs/queue/{ifs_shipment_id}/dispatch",
    response_model=DispatchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ifs_queue_dispatch(
    ifs_shipment_id: str,
    body: IfsQueueDispatchBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchAcceptedResponse:
    result = await dispatch_from_ifs_queue(session, ctx, ifs_shipment_id, body)
    await session.commit()
    return DispatchAcceptedResponse(**result)
