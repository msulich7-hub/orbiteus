"""Shipping business logic — carrier calls only from Celery outbox worker."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.integrations.system_context import system_tenant_context
from orbiteus_core.outbox import enqueue

from modules.shipping.controller.repositories import IfsQueueRepository, ShipmentRepository
from modules.shipping.lib.carrier_registry import adapter_for, normalize_carrier_code
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.lib.ifs_inbound_adapter import get_ifs_inbound_port
from modules.shipping.lib.ifs_inbound_mapper import (
    payload_to_dispatch_packages,
    payload_to_ifs_dispatch_dict,
)
from modules.shipping.lib.ifs_logistics_types import IfsLogisticsPayload
from modules.shipping.lib.ifs_packaging import is_pallet
from modules.shipping.lib.routing import resolve_carrier_for_shipment
from modules.shipping.model.domain import Shipment
from modules.shipping.model.schemas import DispatchBody, IfsQueueDispatchBody, SimulateBody

SHIPPING_LABEL_TARGET = "shipping_label"
EVENT_LABEL_DISPATCH = "shipping.label.dispatch_requested"


async def simulate_routing(body: SimulateBody) -> dict:
    code = resolve_carrier_for_shipment(
        forward_agent_id=body.forward_agent_id or None,
        weight_kg=body.weight_kg,
        is_locker=body.is_locker,
        is_pallet=body.is_pallet,
    )
    cfg = get_carrier_settings()
    return {
        "recommended_carrier": code,
        "configured": cfg.carrier_configured(code),
    }


async def enqueue_label_dispatch(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    payload: dict[str, Any],
    target_ref: str | None = None,
) -> uuid.UUID:
    """Persist outbox row in the same transaction as queue/shipment updates."""
    return await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event=EVENT_LABEL_DISPATCH,
        payload=payload,
        target_kind=SHIPPING_LABEL_TARGET,
        target_ref=target_ref,
    )


async def execute_dispatch_for_order(
    session: AsyncSession,
    ctx: RequestContext,
    body: DispatchBody,
) -> Shipment:
    """Create shipment + label — called only from Celery worker."""
    repo = ShipmentRepository(session, ctx)
    carrier = (
        normalize_carrier_code(body.force_carrier)
        if body.force_carrier
        else resolve_carrier_for_shipment(
            forward_agent_id=body.forward_agent_id or None,
            weight_kg=body.weight_kg,
            is_locker=body.is_locker,
            is_pallet=body.is_pallet,
        )
    )

    shipment = await repo.create(
        {
            "order_id": body.order_id,
            "carrier_code": carrier,
            "state": "queued",
            "weight_kg": body.weight_kg,
            "is_pallet": body.is_pallet,
            "is_locker": body.is_locker,
            "forward_agent_id": body.forward_agent_id,
            "reference": str(body.order_id),
        }
    )

    cfg = get_carrier_settings()
    if not cfg.carrier_configured(carrier):
        return await repo.update(
            shipment.id,
            {
                "state": "failed",
                "error_message": f"Carrier {carrier} not configured in env (see .env.shipping.example)",
            },
        )

    try:
        adapter = adapter_for(carrier)
        dispatch_payload: dict = {
            "order_id": str(body.order_id),
            "weight_kg": body.weight_kg,
            "reference": str(body.order_id),
            "is_pallet": body.is_pallet,
            "is_locker": body.is_locker,
        }
        if body.recipient:
            dispatch_payload["recipient"] = body.recipient.model_dump()
        if body.parcels:
            dispatch_payload["parcels"] = [p.model_dump() for p in body.parcels]
        if body.ifs_payload and body.packages:
            dispatch_payload["ifs_payload"] = body.ifs_payload
            dispatch_payload["packages"] = body.packages

        result = await adapter.create_label(dispatch_payload)
        return await repo.update(
            shipment.id,
            {
                "state": "label_created",
                "tracking_number": result.get("tracking_number") or "",
                "label_payload_json": json.dumps(result),
            },
        )
    except NotImplementedError as exc:
        return await repo.update(
            shipment.id,
            {"state": "failed", "error_message": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001
        return await repo.update(
            shipment.id,
            {"state": "failed", "error_message": str(exc)},
        )


async def dispatch_for_order(
    session: AsyncSession,
    ctx: RequestContext,
    body: DispatchBody,
) -> dict[str, Any]:
    """Queue label creation via outbox (HTTP handler — no sync carrier HTTP)."""
    outbox_id = await enqueue_label_dispatch(
        session,
        ctx,
        payload={
            "tenant_id": str(ctx.tenant_id),
            "dispatch_body": body.model_dump(mode="json"),
            "source": "api",
        },
    )
    return {"outbox_id": str(outbox_id), "state": "processing", "ok": True}


def _parse_queue_payload(payload_json: str) -> IfsLogisticsPayload:
    data = json.loads(payload_json or "{}")
    return IfsLogisticsPayload.model_validate(data)


async def ingest_ifs_webhook(
    session: AsyncSession,
    raw: dict,
    *,
    ifs_sid: str,
    request_id: str | None = None,
):
    """Ingest Oracle webhook — actor=system, tenant from config, audited upsert."""
    ctx = await system_tenant_context(session, request_id=request_id)
    event = get_ifs_inbound_port().parse_webhook(raw, ifs_sid=ifs_sid)
    repo = IfsQueueRepository(session, ctx)
    row = await repo.upsert_from_event(
        ifs_shipment_id=event.shipment_id,
        ifs_sid=event.ifs_sid,
        objstate=event.objstate,
        payload=event.logistics_payload,
    )

    cfg = get_carrier_settings()
    if cfg.ifs_auto_dispatch and raw.get("order_id"):
        await enqueue_label_dispatch(
            session,
            ctx,
            payload={
                "tenant_id": str(ctx.tenant_id),
                "ifs_shipment_id": event.shipment_id,
                "order_id": str(raw["order_id"]),
                "source": "auto",
            },
            target_ref=event.shipment_id,
        )
        await repo.mark_state(event.shipment_id, state="processing")

    return row


async def list_ifs_queue(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    state: str | None = "queued",
    limit: int = 50,
) -> list[dict]:
    domain: list[tuple[str, str, object]] = []
    if state:
        domain.append(("state", "=", state))
    repo = IfsQueueRepository(session, ctx)
    rows, _ = await repo.search(domain, limit=limit, order_by="write_date", order_dir="desc")
    out: list[dict] = []
    for row in rows:
        try:
            payload = _parse_queue_payload(row.payload_json)
        except Exception:
            payload = None
        out.append(
            {
                "id": row.id,
                "ifs_shipment_id": row.ifs_shipment_id,
                "ifs_sid": row.ifs_sid,
                "objstate": row.objstate,
                "state": row.state,
                "payload_json": row.payload_json,
                "error_message": row.error_message,
                "order_no": payload.order_no if payload else None,
                "forward_agent_id": payload.forward_agent_id if payload else None,
                "total_weight_kg": payload.total_weight_kg if payload else None,
                "line_count": len(payload.lines) if payload else 0,
                "created_at": row.create_date,
                "updated_at": row.write_date,
            }
        )
    return out


async def execute_dispatch_from_ifs_queue(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
    *,
    order_id: uuid.UUID,
    force_carrier: str | None = None,
) -> Shipment:
    """Worker-only: create label from queued IFS payload."""
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    if row.state == "dispatched":
        raise ValueError(f"IFS queue {ifs_shipment_id} already dispatched")

    payload = _parse_queue_payload(row.payload_json)
    packages = payload_to_dispatch_packages(payload)
    ifs_payload = payload_to_ifs_dispatch_dict(payload)

    first_pack = payload.lines[0].pack_type if payload.lines else None
    dispatch_body = DispatchBody(
        order_id=order_id,
        weight_kg=float(payload.total_weight_kg or 0),
        is_pallet=is_pallet(first_pack) if first_pack else False,
        forward_agent_id=payload.forward_agent_id or "",
        force_carrier=force_carrier,
        ifs_payload=ifs_payload,
        packages=packages,
    )

    shipment = await execute_dispatch_for_order(session, ctx, dispatch_body)
    if shipment.state == "label_created":
        await queue_repo.mark_state(ifs_shipment_id, state="dispatched")
    elif shipment.state == "failed":
        await queue_repo.mark_state(
            ifs_shipment_id,
            state="failed",
            error_message=shipment.error_message or "dispatch failed",
        )
    return shipment


async def dispatch_from_ifs_queue(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
    body: IfsQueueDispatchBody,
) -> dict[str, Any]:
    """HTTP: enqueue async label dispatch (no carrier HTTP in request)."""
    queue_repo = IfsQueueRepository(session, ctx)
    await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    await queue_repo.mark_state(ifs_shipment_id, state="processing")

    outbox_id = await enqueue_label_dispatch(
        session,
        ctx,
        payload={
            "tenant_id": str(ctx.tenant_id),
            "ifs_shipment_id": ifs_shipment_id,
            "order_id": str(body.order_id),
            "force_carrier": body.force_carrier,
            "source": "manual",
        },
        target_ref=ifs_shipment_id,
    )
    return {
        "ok": True,
        "outbox_id": str(outbox_id),
        "state": "processing",
        "ifs_shipment_id": ifs_shipment_id,
    }
