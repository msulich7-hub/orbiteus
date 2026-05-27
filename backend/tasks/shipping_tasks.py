"""Celery handlers for shipping outbox rows (carrier label creation)."""

from __future__ import annotations

import asyncio
import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.shipping_tasks.dispatch_shipping_label")
def dispatch_shipping_label() -> None:
    """Legacy sync entry — prefer outbox drainer calling dispatch_shipping_label_async."""
    logger.warning("dispatch_shipping_label called without payload — use outbox drainer")


async def dispatch_shipping_label_async(
    *,
    event: str,
    payload: dict,
    target_ref: str | None = None,
) -> None:
    """Execute carrier label creation from an outbox row (idempotent)."""
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    from modules.shipping.controller.services import (
        execute_dispatch_for_order,
        execute_dispatch_from_ifs_queue,
    )

    tenant_raw = payload.get("tenant_id")
    if not tenant_raw:
        raise ValueError("shipping outbox payload missing tenant_id")

    tenant_id = uuid.UUID(str(tenant_raw))
    ctx = RequestContext(actor="system", tenant_id=tenant_id, is_superadmin=True)

    async with AsyncSessionFactory() as session:
        ifs_shipment_id = payload.get("ifs_shipment_id")
        if ifs_shipment_id:
            await execute_dispatch_from_ifs_queue(
                session,
                ctx,
                str(ifs_shipment_id),
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
            "target_ref": target_ref,
        },
    )
