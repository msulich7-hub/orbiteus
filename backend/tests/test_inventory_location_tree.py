"""WMS-T02 — location tree API and per-warehouse barcode uniqueness."""

from __future__ import annotations

import pytest

from tests.conftest import register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("wms-tree"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _find_node(nodes: list[dict], code: str) -> dict | None:
    for node in nodes:
        if node.get("code") == code:
            return node
        child = _find_node(node.get("children") or [], code)
        if child is not None:
            return child
    return None


@pytest.mark.asyncio
async def test_location_tree_three_levels_and_barcode_unique(client) -> None:
    headers = await _auth_headers(client)

    wh_resp = await client.post(
        "/api/inventory/warehouse",
        json={"code": "WH-TREE", "name": "Tree warehouse"},
        headers=headers,
    )
    assert wh_resp.status_code in (200, 201), wh_resp.text
    warehouse_id = wh_resp.json()["id"]

    zone_resp = await client.post(
        "/api/inventory/locations",
        json={
            "warehouse_id": warehouse_id,
            "code": "ZONE-A",
            "name": "Zone A",
            "location_type": "zone",
            "barcode": "BC-ZONE-A",
        },
        headers=headers,
    )
    assert zone_resp.status_code in (200, 201), zone_resp.text
    zone_id = zone_resp.json()["id"]

    aisle_resp = await client.post(
        "/api/inventory/locations",
        json={
            "warehouse_id": warehouse_id,
            "parent_id": zone_id,
            "code": "AISLE-01",
            "name": "Aisle 01",
            "location_type": "aisle",
            "barcode": "BC-AISLE-01",
        },
        headers=headers,
    )
    assert aisle_resp.status_code in (200, 201), aisle_resp.text
    aisle_id = aisle_resp.json()["id"]

    bin_resp = await client.post(
        "/api/inventory/locations",
        json={
            "warehouse_id": warehouse_id,
            "parent_id": aisle_id,
            "code": "BIN-03",
            "name": "Bin 03",
            "location_type": "bin",
            "barcode": "BC-BIN-03",
        },
        headers=headers,
    )
    assert bin_resp.status_code in (200, 201), bin_resp.text

    dup_resp = await client.post(
        "/api/inventory/locations",
        json={
            "warehouse_id": warehouse_id,
            "code": "BIN-DUP",
            "name": "Duplicate barcode",
            "location_type": "bin",
            "barcode": "BC-BIN-03",
        },
        headers=headers,
    )
    assert dup_resp.status_code == 409, dup_resp.text

    tree_resp = await client.get(
        f"/api/inventory/locations/tree?warehouse_id={warehouse_id}",
        headers=headers,
    )
    assert tree_resp.status_code == 200, tree_resp.text
    payload = tree_resp.json()
    assert payload["warehouse_id"] == warehouse_id
    nodes = payload["nodes"]
    assert len(nodes) >= 1

    zone = _find_node(nodes, "ZONE-A")
    assert zone is not None
    assert zone["location_type"] == "zone"
    aisle = _find_node(zone["children"], "AISLE-01")
    assert aisle is not None
    assert aisle["location_type"] == "aisle"
    bin_node = _find_node(aisle["children"], "BIN-03")
    assert bin_node is not None
    assert bin_node["location_type"] == "bin"
    assert bin_node["barcode"] == "BC-BIN-03"
