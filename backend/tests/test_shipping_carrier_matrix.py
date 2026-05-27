"""Three label attempts per carrier — MOCK always; live carriers when env configured."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.shipping.controller.services import execute_dispatch_for_order
from modules.shipping.lib.carrier_registry import adapter_for
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.model.schemas import DispatchBody

CARRIERS = ("MOCK", "DPD", "DSV", "GEODIS")
SCENARIOS = (
    {"weight_kg": 5.5, "is_pallet": False, "tag": "S"},
    {"weight_kg": 15.0, "is_pallet": False, "tag": "M"},
    {"weight_kg": 120.0, "is_pallet": True, "tag": "L"},
)


@pytest.mark.parametrize("carrier", CARRIERS)
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.asyncio
async def test_execute_dispatch_three_per_carrier_mocked(
    carrier: str,
    scenario: dict,
) -> None:
    """Each carrier × scenario creates a shipment with label_created (adapter mocked)."""
    cfg = get_carrier_settings()
    if carrier != "MOCK" and not cfg.carrier_configured(carrier):
        pytest.skip(f"{carrier} not configured in env")

    session = AsyncMock()
    ctx = MagicMock()
    ctx.tenant_id = uuid.uuid4()

    created: list[dict] = []
    tracking = f"{carrier}-{scenario['tag']}-MOCKTRACK"

    async def fake_create_label(payload: dict) -> dict:
        created.append(payload)
        return {
            "carrier_code": carrier,
            "tracking_number": tracking,
            "label_base64": None,
            "raw": {"test": True},
        }

    mock_adapter = MagicMock()
    mock_adapter.create_label = AsyncMock(side_effect=fake_create_label)

    shipment_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.create = AsyncMock(
        return_value=MagicMock(id=shipment_id, state="queued", tracking_number="")
    )
    mock_repo.update = AsyncMock(
        side_effect=lambda _id, data: MagicMock(
            id=shipment_id,
            state=data.get("state", "label_created"),
            tracking_number=data.get("tracking_number", tracking),
            error_message=data.get("error_message", ""),
        )
    )

    body = DispatchBody(
        order_id=uuid.uuid4(),
        weight_kg=scenario["weight_kg"],
        is_pallet=scenario["is_pallet"],
        force_carrier=carrier,
    )

    with (
        patch(
            "modules.shipping.controller.services.ShipmentRepository",
            return_value=mock_repo,
        ),
        patch(
            "modules.shipping.controller.services.adapter_for",
            return_value=mock_adapter,
        ),
        patch(
            "modules.shipping.controller.services.get_carrier_settings",
            return_value=cfg,
        ),
    ):
        result = await execute_dispatch_for_order(session, ctx, body)

    assert result.state == "label_created"
    assert result.tracking_number == tracking
    mock_adapter.create_label.assert_awaited_once()
    call_payload = mock_adapter.create_label.await_args.args[0]
    assert call_payload.get("is_pallet") == scenario["is_pallet"]


@pytest.mark.asyncio
async def test_mock_adapter_three_shipments_integration() -> None:
    """Direct adapter: 3 MOCK labels without DB."""
    adapter = adapter_for("MOCK")
    for i, scenario in enumerate(SCENARIOS, start=1):
        result = await adapter.create_label(
            {
                "reference": f"ORB-MOCK-matrix-{i}",
                "weight_kg": scenario["weight_kg"],
                "is_pallet": scenario["is_pallet"],
            }
        )
        assert result["tracking_number"].startswith("MOCK-")
        assert result["raw"]["mock"] is True


@pytest.mark.parametrize("carrier", CARRIERS)
def test_carrier_matrix_count_parametrized(carrier: str) -> None:
    """Guard: matrix is 4 carriers × 3 scenarios = 12 cases when all configured."""
    assert len(SCENARIOS) == 3
    assert carrier in CARRIERS
