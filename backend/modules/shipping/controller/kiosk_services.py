"""Dispatch kiosk workspace — no carrier HTTP (outbox only)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import NotFound

from modules.shipping.controller.compose_preview import (
    build_suggested_plan,
    payload_from_queue_row,
    preview_handling_units_from_payload,
)
from modules.shipping.controller.repositories import (
    DispatchRepository,
    HandlingUnitRepository,
    IfsQueueRepository,
    WaybillRepository,
)
from modules.shipping.controller.services import (
    EVENT_LABEL_DISPATCH,
    SHIPPING_LABEL_TARGET,
    enqueue_label_dispatch,
    list_ifs_queue,
)
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.lib.ifs_dispatch_profiles import resolve_ifs_dispatch_profile
from modules.shipping.lib.ifs_inbound_mapper import (
    payload_to_dispatch_packages,
    payload_to_ifs_dispatch_dict,
)
from modules.shipping.lib.ifs_logistics_types import IfsLogisticsPayload
from modules.shipping.lib.ifs_packaging import is_pallet
from modules.shipping.lib.routing import resolve_carrier_for_shipment
from modules.shipping.model.domain import Dispatch, HandlingUnit, Waybill
from modules.shipping.model.schemas import (
    AssignUnitBody,
    CarrierStatusResponse,
    ComposePlanBody,
    ComposePlanResponse,
    DispatchPatchBody,
    DispatchPlanBody,
    DispatchPlanResponse,
    DispatchStatusResponse,
    DispatchStatusWaybill,
    DispatchWorkspaceDispatch,
    DispatchWorkspaceQueue,
    DispatchWorkspaceRead,
    DispatchWorkspaceUnit,
    DispatchWorkspaceWaybill,
    IfsInboxCounts,
    IfsInboxResponse,
    IfsQueueRowRead,
    StartDispatchResponse,
    SubmitAllResponse,
    WaybillJobResponse,
    WaybillSubmitResponse,
)

MAX_WAYBILLS = 5


def _carrier_status() -> CarrierStatusResponse:
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


def _recommended_carrier(payload: IfsLogisticsPayload, units: list) -> str:
    first_pack = payload.lines[0].pack_type if payload.lines else None
    pallet_flag = is_pallet(first_pack) if first_pack else any(
        getattr(u, "unit_type", getattr(u, "type", "")) == "pallet" for u in units
    )
    total = float(payload.total_weight_kg or 0)
    if not total and units:
        total = sum(
            (getattr(u, "weight_kg", 0) or 0) * max(1, getattr(u, "qty", 1)) for u in units
        )
    return resolve_carrier_for_shipment(
        forward_agent_id=payload.forward_agent_id or None,
        weight_kg=total,
        is_pallet=pallet_flag,
    )


async def _persist_handling_units(
    hu_repo: HandlingUnitRepository,
    dispatch_id: uuid.UUID,
    payload: IfsLogisticsPayload,
) -> list[HandlingUnit]:
    preview = preview_handling_units_from_payload(payload)
    created: list[HandlingUnit] = []
    for seq, pu in enumerate(preview):
        row = await hu_repo.create(
            {
                "dispatch_id": dispatch_id,
                "pack_type": pu.pack_type,
                "unit_type": pu.type,
                "qty": pu.qty,
                "weight_kg": pu.weight_kg,
                "length_cm": pu.length_cm,
                "width_cm": pu.width_cm,
                "height_cm": pu.height_cm,
                "sequence": seq,
            }
        )
        created.append(row)
    return created


async def start_dispatch_from_queue(
    session: AsyncSession,
    ctx: RequestContext,
    queue_id: uuid.UUID,
) -> StartDispatchResponse:
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get(queue_id)
    if row.dispatch_id:
        return StartDispatchResponse(dispatch_id=row.dispatch_id)

    payload = payload_from_queue_row(row)
    profile = resolve_ifs_dispatch_profile(payload.contract)
    recommended = _recommended_carrier(payload, preview_handling_units_from_payload(payload))

    dispatch_repo = DispatchRepository(session, ctx)
    dest = payload.destination
    dispatch = await dispatch_repo.create(
        {
            "ifs_queue_id": row.id,
            "ifs_shipment_id": row.ifs_shipment_id,
            "state": "composing",
            "pickup_site_code": profile.site_code if profile else "",
            "recommended_carrier_code": recommended,
            "destination_json": json.dumps(dest.model_dump() if dest else {}),
            "sender_json": json.dumps(
                payload.sender.model_dump() if payload.sender else {}
            ),
            "metadata_json": "{}",
            "waybill_count": 1,
        }
    )

    hu_repo = HandlingUnitRepository(session, ctx)
    await _persist_handling_units(hu_repo, dispatch.id, payload)

    wb_repo = WaybillRepository(session, ctx)
    await wb_repo.create(
        {
            "dispatch_id": dispatch.id,
            "sequence": 1,
            "carrier_code": recommended,
            "state": "draft",
        }
    )

    await queue_repo.link_dispatch(row.ifs_shipment_id, dispatch.id, state="claimed")
    return StartDispatchResponse(dispatch_id=dispatch.id)


async def get_workspace(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
) -> DispatchWorkspaceRead:
    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get(dispatch_id)
    queue_row = None
    if dispatch.ifs_queue_id:
        queue_repo = IfsQueueRepository(session, ctx)
        try:
            queue_row = await queue_repo.get(dispatch.ifs_queue_id)
        except NotFound:
            queue_row = None

    hu_repo = HandlingUnitRepository(session, ctx)
    units = await hu_repo.list_for_dispatch(dispatch_id)
    wb_repo = WaybillRepository(session, ctx)
    waybills = await wb_repo.list_for_dispatch(dispatch_id)

    unit_ids_by_waybill: dict[uuid.UUID, list[uuid.UUID]] = {}
    for u in units:
        if u.waybill_id:
            unit_ids_by_waybill.setdefault(u.waybill_id, []).append(u.id)

    return DispatchWorkspaceRead(
        dispatch=DispatchWorkspaceDispatch(
            id=dispatch.id,
            state=dispatch.state,
            ifs_shipment_id=dispatch.ifs_shipment_id,
            pickup_site_code=dispatch.pickup_site_code,
            recommended_carrier_code=dispatch.recommended_carrier_code,
            waybill_count=dispatch.waybill_count,
            destination_json=dispatch.destination_json,
            sender_json=dispatch.sender_json,
            metadata_json=dispatch.metadata_json,
        ),
        queue=(
            DispatchWorkspaceQueue(
                id=queue_row.id,
                objstate=queue_row.objstate,
                payload_json=queue_row.payload_json,
                state=queue_row.state,
            )
            if queue_row
            else None
        ),
        units=[
            DispatchWorkspaceUnit(
                id=u.id,
                pack_type=u.pack_type,
                unit_type=u.unit_type,
                qty=u.qty,
                weight_kg=u.weight_kg,
                length_cm=u.length_cm,
                width_cm=u.width_cm,
                height_cm=u.height_cm,
                waybill_id=u.waybill_id,
                sequence=u.sequence,
            )
            for u in units
        ],
        waybills=[
            DispatchWorkspaceWaybill(
                id=w.id,
                sequence=w.sequence,
                carrier_code=w.carrier_code,
                state=w.state,
                tracking_number=w.tracking_number,
                unit_ids=unit_ids_by_waybill.get(w.id, []),
            )
            for w in waybills
        ],
        carriers=_carrier_status(),
    )


async def assign_unit(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
    body: AssignUnitBody,
) -> dict[str, bool]:
    hu_repo = HandlingUnitRepository(session, ctx)
    unit = await hu_repo.get(body.unit_id)
    if unit.dispatch_id != dispatch_id:
        raise ValueError("Unit does not belong to this dispatch")
    if body.waybill_id:
        wb_repo = WaybillRepository(session, ctx)
        wb = await wb_repo.get(body.waybill_id)
        if wb.dispatch_id != dispatch_id:
            raise ValueError("Waybill does not belong to this dispatch")
    await hu_repo.update(body.unit_id, {"waybill_id": body.waybill_id})
    return {"ok": True}


async def patch_dispatch(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
    body: DispatchPatchBody,
) -> DispatchWorkspaceRead:
    dispatch_repo = DispatchRepository(session, ctx)
    patch: dict[str, Any] = {}
    if body.state is not None:
        patch["state"] = body.state
    if body.waybill_count is not None:
        patch["waybill_count"] = body.waybill_count
    if patch:
        await dispatch_repo.update(dispatch_id, patch)
    return await get_workspace(session, ctx, dispatch_id)


async def add_waybill_slot(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
    *,
    carrier_code: str | None = None,
) -> Waybill:
    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get(dispatch_id)
    wb_repo = WaybillRepository(session, ctx)
    existing = await wb_repo.list_for_dispatch(dispatch_id)
    if len(existing) >= MAX_WAYBILLS:
        raise ValueError(f"Maximum {MAX_WAYBILLS} waybill slots per dispatch")
    seq = max((w.sequence for w in existing), default=0) + 1
    carrier = carrier_code or dispatch.recommended_carrier_code
    wb = await wb_repo.create(
        {
            "dispatch_id": dispatch_id,
            "sequence": seq,
            "carrier_code": carrier,
            "state": "draft",
        }
    )
    await dispatch_repo.update(dispatch_id, {"waybill_count": len(existing) + 1})
    return wb


async def delete_waybill_slot(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
    sequence: int,
) -> None:
    wb_repo = WaybillRepository(session, ctx)
    wb = await wb_repo.get_by_dispatch_sequence(dispatch_id, sequence)
    if wb is None:
        raise NotFound("shipping.waybill", f"{dispatch_id}:{sequence}")
    if wb.state != "draft":
        raise ValueError("Only draft waybills can be removed")
    hu_repo = HandlingUnitRepository(session, ctx)
    units = await hu_repo.list_for_dispatch(dispatch_id)
    for u in units:
        if u.waybill_id == wb.id:
            await hu_repo.update(u.id, {"waybill_id": None})
    await wb_repo.delete(wb.id)


async def save_compose_plan(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
    body: ComposePlanBody,
) -> ComposePlanResponse:
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get_for_ifs_shipment(ifs_shipment_id)
    if dispatch is None:
        started = await start_dispatch_from_queue(session, ctx, row.id)
        dispatch = await dispatch_repo.get(started.dispatch_id)

    meta = json.loads(dispatch.metadata_json or "{}")
    revision = int(meta.get("compose_revision", 0)) + 1
    meta["compose_revision"] = revision
    meta["compose_plan"] = body.model_dump(mode="json")
    if body.order_id:
        meta["order_id"] = str(body.order_id)

    await dispatch_repo.update(
        dispatch.id,
        {"metadata_json": json.dumps(meta), "state": "composing"},
    )
    return ComposePlanResponse(saved=True, revision=revision, dispatch_id=dispatch.id)


def _resolve_hu_ids_to_units(
    units: list[HandlingUnit],
    hu_ids: list[str],
) -> list[HandlingUnit]:
    by_id = {str(u.id): u for u in units}
    by_seq = {f"hu-{u.sequence}": u for u in units}
    resolved: list[HandlingUnit] = []
    for hid in hu_ids:
        u = by_id.get(hid) or by_seq.get(hid)
        if u:
            resolved.append(u)
    return resolved


async def _enqueue_waybill_submit(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    waybill: Waybill,
    dispatch: Dispatch,
    order_id: uuid.UUID,
    queue_row,
) -> uuid.UUID:
    hu_repo = HandlingUnitRepository(session, ctx)
    units = await hu_repo.list_for_dispatch(dispatch.id)
    assigned = [u for u in units if u.waybill_id == waybill.id]
    if not assigned:
        raise ValueError(f"Waybill {waybill.sequence} has no assigned handling units")

    payload = payload_from_queue_row(queue_row) if queue_row else None
    ifs_payload = payload_to_ifs_dispatch_dict(payload) if payload else {}
    packages = []
    for i, u in enumerate(assigned):
        packages.append(
            {
                "pack_type": u.pack_type,
                "quantity": u.qty,
                "weight_kg": u.weight_kg,
                "length_cm": u.length_cm,
                "width_cm": u.width_cm,
                "height_cm": u.height_cm,
                "source_line_index": i,
            }
        )

    pallet_flags = [is_pallet(u.pack_type) for u in assigned]
    is_pallet_shipment = all(pallet_flags) and any(pallet_flags)

    wb_repo = WaybillRepository(session, ctx)
    await wb_repo.update(waybill.id, {"state": "queued"})

    target_ref = f"{dispatch.ifs_shipment_id}:{waybill.sequence}"
    outbox_id = await enqueue_label_dispatch(
        session,
        ctx,
        payload={
            "tenant_id": str(ctx.tenant_id),
            "waybill_id": str(waybill.id),
            "dispatch_id": str(dispatch.id),
            "ifs_shipment_id": dispatch.ifs_shipment_id,
            "order_id": str(order_id),
            "carrier_code": waybill.carrier_code,
            "ifs_payload": ifs_payload,
            "packages": packages,
            "weight_kg": sum((u.weight_kg or 0) * u.qty for u in assigned),
            "is_pallet": is_pallet_shipment,
            "forward_agent_id": (payload.forward_agent_id if payload else "") or "",
            "source": "kiosk",
        },
        target_ref=target_ref,
    )
    return outbox_id


async def submit_waybill(
    session: AsyncSession,
    ctx: RequestContext,
    waybill_id: uuid.UUID,
    *,
    order_id: uuid.UUID,
) -> WaybillSubmitResponse:
    wb_repo = WaybillRepository(session, ctx)
    waybill = await wb_repo.get(waybill_id)
    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get(waybill.dispatch_id)
    queue_repo = IfsQueueRepository(session, ctx)
    queue_row = await queue_repo.get_by_ifs_shipment_id(dispatch.ifs_shipment_id)
    await queue_repo.mark_state(dispatch.ifs_shipment_id, state="in_dispatch")
    outbox_id = await _enqueue_waybill_submit(
        session,
        ctx,
        waybill=waybill,
        dispatch=dispatch,
        order_id=order_id,
        queue_row=queue_row,
    )
    return WaybillSubmitResponse(
        ok=True,
        outbox_id=str(outbox_id),
        state="processing",
        waybill_id=waybill.id,
    )


async def submit_all_waybills(
    session: AsyncSession,
    ctx: RequestContext,
    dispatch_id: uuid.UUID,
    *,
    order_id: uuid.UUID,
) -> SubmitAllResponse:
    wb_repo = WaybillRepository(session, ctx)
    waybills = await wb_repo.list_for_dispatch(dispatch_id)
    outbox_ids: list[str] = []
    for wb in waybills:
        if wb.state not in ("draft", "failed"):
            continue
        result = await submit_waybill(session, ctx, wb.id, order_id=order_id)
        outbox_ids.append(result.outbox_id)
    dispatch_repo = DispatchRepository(session, ctx)
    await dispatch_repo.update(dispatch_id, {"state": "submitting"})
    return SubmitAllResponse(ok=True, outbox_ids=outbox_ids, state="processing")


async def dispatch_plan(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
    body: DispatchPlanBody,
) -> DispatchPlanResponse:
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    started = await start_dispatch_from_queue(session, ctx, row.id)
    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get(started.dispatch_id)
    payload = payload_from_queue_row(row)

    hu_repo = HandlingUnitRepository(session, ctx)
    units = await hu_repo.list_for_dispatch(dispatch.id)
    wb_repo = WaybillRepository(session, ctx)

    batch_id = uuid.uuid4()
    jobs: list[WaybillJobResponse] = []

    for index, slot in enumerate(body.waybills):
        seq = index + 1
        existing = await wb_repo.get_by_dispatch_sequence(dispatch.id, seq)
        if existing:
            wb = await wb_repo.update(
                existing.id,
                {"carrier_code": slot.carrier_code, "state": "draft"},
            )
        else:
            wb = await wb_repo.create(
                {
                    "dispatch_id": dispatch.id,
                    "sequence": seq,
                    "carrier_code": slot.carrier_code,
                    "state": "draft",
                }
            )
        resolved = _resolve_hu_ids_to_units(units, slot.hu_ids)
        for u in resolved:
            await hu_repo.update(u.id, {"waybill_id": wb.id})

        outbox_id = await _enqueue_waybill_submit(
            session,
            ctx,
            waybill=wb,
            dispatch=dispatch,
            order_id=body.order_id,
            queue_row=row,
        )
        jobs.append(
            WaybillJobResponse(
                index=index,
                outbox_id=str(outbox_id),
                waybill_id=wb.id,
                state="processing",
            )
        )

    await queue_repo.mark_state(ifs_shipment_id, state="in_dispatch")
    await dispatch_repo.update(dispatch.id, {"state": "submitting", "waybill_count": len(body.waybills)})

    return DispatchPlanResponse(
        ok=True,
        outbox_batch_id=str(batch_id),
        waybill_jobs=jobs,
        ifs_shipment_id=ifs_shipment_id,
    )


async def dispatch_status(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
) -> DispatchStatusResponse:
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    dispatch_state: str | None = None
    waybill_status: list[DispatchStatusWaybill] = []

    if row.dispatch_id:
        dispatch_repo = DispatchRepository(session, ctx)
        dispatch = await dispatch_repo.get(row.dispatch_id)
        dispatch_state = dispatch.state
        wb_repo = WaybillRepository(session, ctx)
        for wb in await wb_repo.list_for_dispatch(dispatch.id):
            waybill_status.append(
                DispatchStatusWaybill(
                    index=wb.sequence - 1,
                    waybill_id=wb.id,
                    state=wb.state,
                    tracking_number=wb.tracking_number or None,
                    error_message=wb.error_message or None,
                )
            )

    return DispatchStatusResponse(
        ifs_shipment_id=ifs_shipment_id,
        queue_state=row.state,
        dispatch_state=dispatch_state,
        waybills=waybill_status,
    )


async def list_ifs_inbox(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    state: str | None = "queued",
    limit: int = 50,
) -> IfsInboxResponse:
    items_raw = await list_ifs_queue(session, ctx, state=state, limit=limit)
    items = [IfsQueueRowRead.model_validate(r) for r in items_raw]

    queue_repo = IfsQueueRepository(session, ctx)
    counts = IfsInboxCounts()
    for st, field in (
        ("queued", "queued"),
        ("claimed", "claimed"),
        ("in_dispatch", "in_dispatch"),
        ("completed", "completed"),
        ("failed", "failed"),
    ):
        _, total = await queue_repo.search([("state", "=", st)], limit=1)
        setattr(counts, field, total)

    return IfsInboxResponse(items=items, counts=counts)
