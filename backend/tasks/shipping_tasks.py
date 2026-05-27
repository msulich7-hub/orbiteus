"""Celery handlers for shipping outbox rows (carrier label creation)."""

from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.shipping_tasks.dispatch_shipping_label")
def dispatch_shipping_label() -> None:
    logger.warning("dispatch_shipping_label called without payload — use outbox drainer")


async def dispatch_shipping_label_async(
    *,
    event: str,
    payload: dict,
    target_ref: str | None = None,
) -> None:
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    from modules.shipping.controller.services import (
        execute_dispatch_for_order,
        execute_dispatch_for_waybill,
        execute_dispatch_from_ifs_queue,
        finalize_dispatch_queue_state,
    )

    tenant_raw = payload.get("tenant_id")
    if not tenant_raw:
        raise ValueError("shipping outbox payload missing tenant_id")

    tenant_id = uuid.UUID(str(tenant_raw))
    ctx = RequestContext(actor="system", tenant_id=tenant_id, is_superadmin=True)

    async with AsyncSessionFactory() as session:
        if payload.get("waybill_id"):
            wb = await execute_dispatch_for_waybill(
                session,
                ctx,
                waybill_id=uuid.UUID(str(payload["waybill_id"])),
                order_id=uuid.UUID(str(payload["order_id"])),
                carrier_code=payload.get("carrier_code"),
                ifs_payload=payload.get("ifs_payload"),
                packages=payload.get("packages"),
                weight_kg=float(payload.get("weight_kg") or 0),
                is_pallet_flag=payload.get("is_pallet"),
                forward_agent_id=payload.get("forward_agent_id") or "",
            )
            if payload.get("dispatch_id") and payload.get("ifs_shipment_id"):
                await finalize_dispatch_queue_state(
                    session,
                    ctx,
                    uuid.UUID(str(payload["dispatch_id"])),
                    str(payload["ifs_shipment_id"]),
                )
            logger.info(
                "shipping.waybill.dispatched",
                extra={"waybill_id": str(wb.id), "state": wb.state, "target_ref": target_ref},
            )
        elif payload.get("ifs_shipment_id") and not payload.get("dispatch_body"):
            await execute_dispatch_from_ifs_queue(
                session,
                ctx,
                str(payload["ifs_shipment_id"]),
                order_id=uuid.UUID(str(payload["order_id"])),
                force_carrier=payload.get("force_carrier"),
            )
        elif payload.get("dispatch_body"):
            from modules.shipping.model.schemas import DispatchBody

            body = DispatchBody.model_validate(payload["dispatch_body"])
            await execute_dispatch_for_order(session, ctx, body)
        else:
            raise ValueError(f"Unknown shipping outbox payload for event={event}")

        await session.commit()

    logger.info(
        "shipping.label.dispatched",
        extra={
            "event": event,
            "ifs_shipment_id": payload.get("ifs_shipment_id"),
            "waybill_id": payload.get("waybill_id"),
            "target_ref": target_ref,
        },
    )
