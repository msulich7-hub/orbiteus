"""Location tree and barcode validation (WMS-T02 / WMS-001)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import NotFound, ValidationError

from modules.inventory.controller.repositories import LocationRepository, WarehouseRepository
from modules.inventory.model.domain import Location


async def assert_barcode_unique_in_warehouse(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    warehouse_id: uuid.UUID,
    barcode: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Barcode must be unique per warehouse when non-empty."""
    normalized = (barcode or "").strip()
    if not normalized:
        return

    repo = LocationRepository(session, ctx)
    domain: list[tuple[str, str, Any]] = [
        ("warehouse_id", "=", warehouse_id),
        ("barcode", "=", normalized),
    ]
    rows, _ = await repo.search(domain=domain, limit=5)
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        raise ValidationError(
            f"Barcode '{normalized}' already exists in this warehouse"
        )


async def assert_parent_in_warehouse(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    warehouse_id: uuid.UUID,
    parent_id: uuid.UUID | None,
) -> None:
    if parent_id is None:
        return
    repo = LocationRepository(session, ctx)
    try:
        parent = await repo.get(parent_id)
    except NotFound as exc:
        raise ValidationError("parent_id not found") from exc
    if parent.warehouse_id != warehouse_id:
        raise ValidationError("parent_id must belong to the same warehouse")


def build_location_tree(
    locations: list[Location],
    *,
    warehouse_id: uuid.UUID,
) -> dict[str, Any]:
    """Build nested JSON tree (roots = parent_id is null)."""
    nodes: dict[uuid.UUID, dict[str, Any]] = {}
    for loc in locations:
        if loc.warehouse_id != warehouse_id:
            continue
        nodes[loc.id] = {
            "id": loc.id,
            "warehouse_id": loc.warehouse_id,
            "parent_id": loc.parent_id,
            "code": loc.code,
            "name": loc.name,
            "location_type": loc.location_type,
            "barcode": loc.barcode,
            "is_pickable": loc.is_pickable,
            "is_receivable": loc.is_receivable,
            "max_weight_kg": loc.max_weight_kg,
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for loc in locations:
        if loc.warehouse_id != warehouse_id or loc.id not in nodes:
            continue
        node = nodes[loc.id]
        if loc.parent_id is None:
            roots.append(node)
            continue
        parent = nodes.get(loc.parent_id)
        if parent is None:
            roots.append(node)
        else:
            parent["children"].append(node)

    def sort_children(node: dict[str, Any]) -> None:
        node["children"].sort(key=lambda n: (n.get("code") or "").lower())
        for child in node["children"]:
            sort_children(child)

    roots.sort(key=lambda n: (n.get("code") or "").lower())
    for root in roots:
        sort_children(root)

    return {"warehouse_id": warehouse_id, "nodes": roots}


async def get_location_tree(
    session: AsyncSession,
    ctx: RequestContext,
    warehouse_id: uuid.UUID,
) -> dict[str, Any]:
    wh_repo = WarehouseRepository(session, ctx)
    await wh_repo.get(warehouse_id)

    loc_repo = LocationRepository(session, ctx)
    locations, _ = await loc_repo.search(
        domain=[("warehouse_id", "=", warehouse_id)],
        limit=5000,
        order_by="code",
    )
    return build_location_tree(list(locations), warehouse_id=warehouse_id)
