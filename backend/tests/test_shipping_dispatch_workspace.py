"""Dispatch workspace from IFS queue (SHP-T02)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.shipping.controller.kiosk_services import get_workspace, start_dispatch_from_queue
from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_start_dispatch_creates_units_and_waybill() -> None:
    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()

    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    payload = build_logistics_payload_from_ifs_webhook(raw)
    queue_id = uuid.uuid4()
    dispatch_id = uuid.uuid4()

    row = MagicMock()
    row.id = queue_id
    row.ifs_shipment_id = "900123"
    row.dispatch_id = None
    row.objstate = "Released"
    row.state = "claimed"
    row.payload_json = json.dumps(payload.model_dump(mode="json"), default=str)

    dispatch = MagicMock()
    dispatch.id = dispatch_id
    dispatch.ifs_shipment_id = "900123"
    dispatch.ifs_queue_id = queue_id
    dispatch.state = "composing"
    dispatch.pickup_site_code = "BAZ"
    dispatch.recommended_carrier_code = "GEODIS"
    dispatch.destination_json = "{}"
    dispatch.sender_json = "{}"
    dispatch.metadata_json = "{}"
    dispatch.waybill_count = 1

    units = [
        MagicMock(
            id=uuid.uuid4(),
            dispatch_id=dispatch_id,
            pack_type="PAL_A",
            unit_type="pallet",
            qty=1,
            weight_kg=120.0,
            length_cm=120,
            width_cm=80,
            height_cm=150,
            waybill_id=None,
            sequence=0,
        ),
        MagicMock(
            id=uuid.uuid4(),
            dispatch_id=dispatch_id,
            pack_type="PACZKASTD",
            unit_type="parcel",
            qty=2,
            weight_kg=5.0,
            length_cm=30,
            width_cm=20,
            height_cm=10,
            waybill_id=None,
            sequence=1,
        ),
    ]
    waybill = MagicMock(
        id=uuid.uuid4(),
        dispatch_id=dispatch_id,
        sequence=1,
        carrier_code="GEODIS",
        state="draft",
        tracking_number="",
    )

    queue_repo = MagicMock()
    queue_repo.get = AsyncMock(return_value=row)
    queue_repo.link_dispatch = AsyncMock(return_value=row)

    dispatch_repo = MagicMock()
    dispatch_repo.create = AsyncMock(return_value=dispatch)
    dispatch_repo.get = AsyncMock(return_value=dispatch)

    hu_repo = MagicMock()
    hu_repo.create = AsyncMock(side_effect=[*units, *units])
    hu_repo.list_for_dispatch = AsyncMock(return_value=units)

    wb_repo = MagicMock()
    wb_repo.create = AsyncMock(return_value=waybill)
    wb_repo.list_for_dispatch = AsyncMock(return_value=[waybill])

    with (
        patch(
            "modules.shipping.controller.kiosk_services.IfsQueueRepository",
            return_value=queue_repo,
        ),
        patch(
            "modules.shipping.controller.kiosk_services.DispatchRepository",
            return_value=dispatch_repo,
        ),
        patch(
            "modules.shipping.controller.kiosk_services.HandlingUnitRepository",
            return_value=hu_repo,
        ),
        patch(
            "modules.shipping.controller.kiosk_services.WaybillRepository",
            return_value=wb_repo,
        ),
    ):
        result = await start_dispatch_from_queue(session, ctx, queue_id)
        workspace = await get_workspace(session, ctx, dispatch_id)

    assert result.dispatch_id == dispatch_id
    assert len(workspace.units) == 2
    assert len(workspace.waybills) == 1
    assert workspace.waybills[0].sequence == 1
    hu_repo.create.assert_awaited()
    assert hu_repo.create.await_count >= 2
