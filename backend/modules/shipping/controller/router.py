"""Shipping custom API — simulate routing, dispatch labels (async via outbox), kiosk."""

from __future__ import annotations

import base64
import json
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth

from modules.shipping.controller.compose_preview import get_compose_preview
from modules.shipping.controller.ifs_webhook_router import router as ifs_webhook_router
from modules.shipping.controller.kiosk_services import (
    add_waybill_slot,
    assign_unit,
    delete_waybill_slot,
    dispatch_plan,
    dispatch_status,
    get_workspace,
    list_ifs_inbox,
    patch_dispatch,
    save_compose_plan,
    start_dispatch_from_queue,
    submit_all_waybills,
    submit_waybill,
)
from modules.shipping.controller.services import (
    dispatch_for_order,
    dispatch_from_ifs_queue,
    list_ifs_queue,
    simulate_routing,
)
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.model.schemas import (
    AssignUnitBody,
    CarrierStatusResponse,
    ComposePlanBody,
    ComposePlanResponse,
    ComposePreviewResponse,
    DispatchAcceptedResponse,
    DispatchBody,
    DispatchPatchBody,
    DispatchPlanBody,
    DispatchPlanResponse,
    DispatchStatusResponse,
    DispatchWorkspaceRead,
    IfsInboxResponse,
    IfsQueueDispatchBody,
    IfsQueueRowRead,
    SimulateBody,
    StartDispatchResponse,
    SubmitAllResponse,
    WaybillRead,
    WaybillSubmitBody,
    WaybillSubmitResponse,
)

router = APIRouter(tags=["shipping"])
kiosk_router = APIRouter(tags=["shipping-kiosk"])
router.include_router(ifs_webhook_router, prefix="/ifs")
router.include_router(kiosk_router)


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


@kiosk_router.get("/ifs/inbox", response_model=IfsInboxResponse)
async def ifs_inbox(
    state: str | None = "queued",
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> IfsInboxResponse:
    return await list_ifs_inbox(session, ctx, state=state, limit=limit)


@router.get("/ifs/queue", response_model=list[IfsQueueRowRead])
async def ifs_queue_list(
    state: str | None = "queued",
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> list[IfsQueueRowRead]:
    rows = await list_ifs_queue(session, ctx, state=state, limit=limit)
    return [IfsQueueRowRead.model_validate(r) for r in rows]


@kiosk_router.get(
    "/ifs/queue/{ifs_shipment_id}/compose-preview",
    response_model=ComposePreviewResponse,
)
async def ifs_compose_preview(
    ifs_shipment_id: str,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> ComposePreviewResponse:
    return await get_compose_preview(session, ctx, ifs_shipment_id)


@kiosk_router.put(
    "/ifs/queue/{ifs_shipment_id}/compose-plan",
    response_model=ComposePlanResponse,
)
async def ifs_compose_plan(
    ifs_shipment_id: str,
    body: ComposePlanBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> ComposePlanResponse:
    result = await save_compose_plan(session, ctx, ifs_shipment_id, body)
    await session.commit()
    return result


@kiosk_router.post(
    "/ifs/queue/{ifs_shipment_id}/dispatch-plan",
    response_model=DispatchPlanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ifs_dispatch_plan(
    ifs_shipment_id: str,
    body: DispatchPlanBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchPlanResponse:
    result = await dispatch_plan(session, ctx, ifs_shipment_id, body)
    await session.commit()
    return result


@kiosk_router.get(
    "/ifs/queue/{ifs_shipment_id}/dispatch-status",
    response_model=DispatchStatusResponse,
)
async def ifs_dispatch_status(
    ifs_shipment_id: str,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchStatusResponse:
    return await dispatch_status(session, ctx, ifs_shipment_id)


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


@kiosk_router.post(
    "/dispatch/from-queue/{queue_id}",
    response_model=StartDispatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def dispatch_from_queue(
    queue_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> StartDispatchResponse:
    result = await start_dispatch_from_queue(session, ctx, queue_id)
    await session.commit()
    return result


@kiosk_router.get(
    "/dispatch/{dispatch_id}/workspace",
    response_model=DispatchWorkspaceRead,
)
async def dispatch_workspace(
    dispatch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchWorkspaceRead:
    return await get_workspace(session, ctx, dispatch_id)


@kiosk_router.patch(
    "/dispatch/{dispatch_id}",
    response_model=DispatchWorkspaceRead,
)
async def dispatch_patch(
    dispatch_id: uuid.UUID,
    body: DispatchPatchBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> DispatchWorkspaceRead:
    result = await patch_dispatch(session, ctx, dispatch_id, body)
    await session.commit()
    return result


@kiosk_router.post(
    "/dispatch/{dispatch_id}/waybills",
    response_model=WaybillRead,
    status_code=status.HTTP_201_CREATED,
)
async def dispatch_add_waybill(
    dispatch_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> WaybillRead:
    wb = await add_waybill_slot(session, ctx, dispatch_id)
    await session.commit()
    return WaybillRead.model_validate(wb)


@kiosk_router.delete(
    "/dispatch/{dispatch_id}/waybills/{sequence}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dispatch_delete_waybill(
    dispatch_id: uuid.UUID,
    sequence: int,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> Response:
    await delete_waybill_slot(session, ctx, dispatch_id, sequence)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@kiosk_router.put("/dispatch/{dispatch_id}/assign-unit")
async def dispatch_assign_unit(
    dispatch_id: uuid.UUID,
    body: AssignUnitBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    result = await assign_unit(session, ctx, dispatch_id, body)
    await session.commit()
    return result


@kiosk_router.post(
    "/waybill/{waybill_id}/submit",
    response_model=WaybillSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def waybill_submit(
    waybill_id: uuid.UUID,
    body: WaybillSubmitBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> WaybillSubmitResponse:
    result = await submit_waybill(session, ctx, waybill_id, order_id=body.order_id)
    await session.commit()
    return result


@kiosk_router.post(
    "/dispatch/{dispatch_id}/submit-all",
    response_model=SubmitAllResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_submit_all(
    dispatch_id: uuid.UUID,
    body: WaybillSubmitBody,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> SubmitAllResponse:
    result = await submit_all_waybills(
        session, ctx, dispatch_id, order_id=body.order_id
    )
    await session.commit()
    return result


@kiosk_router.get("/waybill/{waybill_id}/label")
async def waybill_label(
    waybill_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> Response:
    from modules.shipping.controller.repositories import WaybillRepository

    wb_repo = WaybillRepository(session, ctx)
    wb = await wb_repo.get(waybill_id)
    if wb.state != "label_created":
        return Response(status_code=status.HTTP_409_CONFLICT)
    data = json.loads(wb.label_payload_json or "{}")
    label_b64 = data.get("label_base64")
    if not label_b64:
        return Response(content=json.dumps(data), media_type="application/json")
    try:
        pdf_bytes = base64.b64decode(label_b64)
    except Exception:
        return Response(content=json.dumps(data), media_type="application/json")
    return Response(content=pdf_bytes, media_type="application/pdf")
