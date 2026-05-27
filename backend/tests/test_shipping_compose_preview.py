"""Compose preview and AUTO eligibility (SHP-T00)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.shipping.controller.compose_preview import (
    build_suggested_plan,
    preview_handling_units_from_payload,
    should_auto_dispatch,
)
from modules.shipping.controller.compose_preview import KioskAutoConfig
from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook
from modules.shipping.model.schemas import PreviewHandlingUnit, SuggestedPlan

FIXTURES = Path(__file__).parent / "fixtures"


def _payload_from_fixture() -> object:
    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    return build_logistics_payload_from_ifs_webhook(raw)


def test_preview_three_handling_units_from_cf_fixture() -> None:
    payload = _payload_from_fixture()
    units = preview_handling_units_from_payload(payload)
    assert len(units) >= 2
    assert units[0].id == "hu-0"


def test_should_auto_dispatch_single_hu() -> None:
    units = [
        PreviewHandlingUnit(
            id="hu-0",
            type="parcel",
            pack_type="PACZKASTD",
            qty=1,
            weight_kg=5.0,
        )
    ]
    plan = build_suggested_plan(units, recommended_carrier="MOCK")
    cfg = KioskAutoConfig(auto_enabled=True, auto_max_hu=1, auto_max_weight_kg=31)
    with patch(
        "modules.shipping.controller.compose_preview.get_carrier_settings"
    ) as mock_cfg:
        mock_cfg.return_value.carrier_configured.return_value = True
        assert should_auto_dispatch(
            units=units,
            suggested_plan=plan,
            recommended_carrier="MOCK",
            queue_state="queued",
            auto_cfg=cfg,
            blocking_errors=[],
        )


def test_should_not_auto_dispatch_multiple_hu() -> None:
    units = [
        PreviewHandlingUnit(id=f"hu-{i}", type="parcel", pack_type="PACZKASTD", qty=1, weight_kg=5)
        for i in range(3)
    ]
    plan = build_suggested_plan(units, recommended_carrier="MOCK")
    cfg = KioskAutoConfig(auto_enabled=True, auto_max_hu=1)
    with patch(
        "modules.shipping.controller.compose_preview.get_carrier_settings"
    ) as mock_cfg:
        mock_cfg.return_value.carrier_configured.return_value = True
        assert not should_auto_dispatch(
            units=units,
            suggested_plan=plan,
            recommended_carrier="MOCK",
            queue_state="queued",
            auto_cfg=cfg,
            blocking_errors=[],
        )


@pytest.mark.asyncio
async def test_get_compose_preview_kiosk_mode_for_multi_hu() -> None:
    from modules.shipping.controller.compose_preview import get_compose_preview

    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()

    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    payload = build_logistics_payload_from_ifs_webhook(raw)
    row = MagicMock()
    row.id = uuid.uuid4()
    row.ifs_shipment_id = "900123"
    row.state = "queued"
    row.payload_json = json.dumps(payload.model_dump(mode="json"), default=str)
    row.dispatch_id = None

    queue_repo = MagicMock()
    queue_repo.get_by_ifs_shipment_id = AsyncMock(return_value=row)
    dispatch_repo = MagicMock()
    dispatch_repo.get_for_ifs_shipment = AsyncMock(return_value=None)

    with (
        patch(
            "modules.shipping.controller.compose_preview.IfsQueueRepository",
            return_value=queue_repo,
        ),
        patch(
            "modules.shipping.controller.compose_preview.DispatchRepository",
            return_value=dispatch_repo,
        ),
        patch(
            "modules.shipping.controller.compose_preview.load_kiosk_auto_config",
            new_callable=AsyncMock,
            return_value=__import__(
                "modules.shipping.controller.compose_preview", fromlist=["KioskAutoConfig"]
            ).KioskAutoConfig(),
        ),
        patch(
            "modules.shipping.controller.compose_preview.get_carrier_settings"
        ) as mock_settings,
    ):
        mock_settings.return_value.carrier_configured.return_value = True
        preview = await get_compose_preview(session, ctx, "900123")

    assert preview.suggested_mode == "kiosk"
    assert len(preview.handling_units) >= 2
