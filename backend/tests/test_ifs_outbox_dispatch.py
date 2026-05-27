"""Outbox enqueue for shipping label dispatch (no live carrier HTTP)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.shipping.controller.services import (
    EVENT_LABEL_DISPATCH,
    SHIPPING_LABEL_TARGET,
    dispatch_for_order,
    dispatch_from_ifs_queue,
    enqueue_label_dispatch,
)
from modules.shipping.model.schemas import DispatchBody, IfsQueueDispatchBody


@pytest.mark.asyncio
async def test_enqueue_label_dispatch_calls_outbox() -> None:
    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()

    with patch("modules.shipping.controller.services.enqueue", new_callable=AsyncMock) as mock_enqueue:
        mock_enqueue.return_value = uuid.uuid4()
        outbox_id = await enqueue_label_dispatch(
            session,
            ctx,
            payload={"tenant_id": str(ctx.tenant_id), "ifs_shipment_id": "900123"},
            target_ref="900123",
        )

    mock_enqueue.assert_awaited_once()
    call_kwargs = mock_enqueue.await_args.kwargs
    assert call_kwargs["event"] == EVENT_LABEL_DISPATCH
    assert call_kwargs["target_kind"] == SHIPPING_LABEL_TARGET
    assert call_kwargs["target_ref"] == "900123"
    assert outbox_id is not None


@pytest.mark.asyncio
async def test_dispatch_for_order_returns_202_shape() -> None:
    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()
    body = DispatchBody(order_id=uuid.uuid4(), weight_kg=10.0)

    with patch(
        "modules.shipping.controller.services.enqueue_label_dispatch",
        new_callable=AsyncMock,
    ) as mock_enqueue:
        mock_enqueue.return_value = uuid.uuid4()
        result = await dispatch_for_order(session, ctx, body)

    assert result["ok"] is True
    assert result["state"] == "processing"
    assert "outbox_id" in result
    mock_enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_from_ifs_queue_returns_processing() -> None:
    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()
    body = IfsQueueDispatchBody(order_id=uuid.uuid4())

    queue_repo = MagicMock()
    queue_repo.get_by_ifs_shipment_id = AsyncMock()
    queue_repo.mark_state = AsyncMock()

    with (
        patch(
            "modules.shipping.controller.services.IfsQueueRepository",
            return_value=queue_repo,
        ),
        patch(
            "modules.shipping.controller.services.enqueue_label_dispatch",
            new_callable=AsyncMock,
        ) as mock_enqueue,
    ):
        mock_enqueue.return_value = uuid.uuid4()
        result = await dispatch_from_ifs_queue(session, ctx, "900123", body)

    assert result["state"] == "processing"
    assert result["ifs_shipment_id"] == "900123"
    queue_repo.mark_state.assert_awaited_with("900123", state="processing")
