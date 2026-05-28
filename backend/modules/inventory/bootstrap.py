"""Inventory module bootstrap — demo warehouse tree for dev tenants."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

_DEMO_WAREHOUSE_CODE = "BAZ"
_DEMO_BIN_CODE = "BAZ-STAGE-01"
_DEMO_SKU = "SKU-DEMO-001"


async def bootstrap(session: AsyncSession, ctx: RequestContext) -> None:
    """Idempotent demo data: one warehouse, staging bin, SKU, 100 pcs on-hand."""
    from modules.inventory.controller.repositories import (
        LocationRepository,
        ProductRepository,
        QuantRepository,
        WarehouseRepository,
    )

    wh_repo = WarehouseRepository(session, ctx)
    loc_repo = LocationRepository(session, ctx)
    prod_repo = ProductRepository(session, ctx)
    quant_repo = QuantRepository(session, ctx)

    rows, total = await wh_repo.search(domain=[("code", "=", _DEMO_WAREHOUSE_CODE)], limit=1)
    if total > 0:
        return

    warehouse = await wh_repo.create(
        {
            "code": _DEMO_WAREHOUSE_CODE,
            "name": "Baza główna (demo WMS)",
            "address_json": {"city": "Demo", "country": "PL"},
        }
    )
    location = await loc_repo.create(
        {
            "warehouse_id": warehouse.id,
            "code": _DEMO_BIN_CODE,
            "name": "Staging przyjęć",
            "location_type": "staging",
            "is_pickable": False,
            "is_receivable": True,
            "barcode": _DEMO_BIN_CODE,
        }
    )
    product = await prod_repo.create(
        {
            "sku": _DEMO_SKU,
            "name": "Produkt demonstracyjny WMS",
            "barcode": "5900000000001",
            "uom": "pcs",
            "weight_kg": 1.0,
        }
    )
    await quant_repo.create(
        {
            "product_id": product.id,
            "location_id": location.id,
            "quantity": Decimal("100"),
            "reserved_quantity": Decimal("0"),
            "incoming_quantity": Decimal("0"),
        }
    )
    logger.info(
        "inventory bootstrap: warehouse=%s bin=%s sku=%s qty=100",
        _DEMO_WAREHOUSE_CODE,
        _DEMO_BIN_CODE,
        _DEMO_SKU,
    )
