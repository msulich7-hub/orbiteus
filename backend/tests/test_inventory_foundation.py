"""WMS-T01 — inventory foundation round-trip (warehouse, location, product, quant)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.conftest import register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("wms"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_inventory_crud_round_trip(client) -> None:
    headers = await _auth_headers(client)

    wh_resp = await client.post(
        "/api/inventory/warehouse",
        json={"code": "WH-TEST", "name": "Test warehouse"},
        headers=headers,
    )
    assert wh_resp.status_code in (200, 201), wh_resp.text
    warehouse_id = wh_resp.json()["id"]

    loc_resp = await client.post(
        "/api/inventory/location",
        json={
            "warehouse_id": warehouse_id,
            "code": "BIN-01",
            "name": "Bin 01",
            "location_type": "bin",
            "barcode": "BIN-01",
        },
        headers=headers,
    )
    assert loc_resp.status_code in (200, 201), loc_resp.text
    location_id = loc_resp.json()["id"]

    prod_resp = await client.post(
        "/api/inventory/product",
        json={"sku": "SKU-TEST-001", "name": "Test SKU", "barcode": "5900000000999"},
        headers=headers,
    )
    assert prod_resp.status_code in (200, 201), prod_resp.text
    product_id = prod_resp.json()["id"]

    quant_resp = await client.post(
        "/api/inventory/quant",
        json={
            "product_id": product_id,
            "location_id": location_id,
            "quantity": "25.5",
            "reserved_quantity": "0",
            "incoming_quantity": "0",
        },
        headers=headers,
    )
    assert quant_resp.status_code in (200, 201), quant_resp.text
    assert Decimal(str(quant_resp.json()["quantity"])) == Decimal("25.5")

    list_resp = await client.get("/api/inventory/quant", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()
    records = items if isinstance(items, list) else items.get("items", items.get("data", []))
    assert any(r["id"] == quant_resp.json()["id"] for r in records)
