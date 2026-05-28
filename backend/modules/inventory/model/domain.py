"""Inventory (WMS) domain models — WMS-001..003."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from orbiteus_core.base_domain import BaseModel

LOCATION_TYPES = (
    "warehouse",
    "zone",
    "aisle",
    "rack",
    "bin",
    "dock",
    "staging",
)


@dataclass
class Warehouse(BaseModel):
    """Physical warehouse / site (WMS-001)."""

    code: str = ""
    name: str = ""
    address_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class Location(BaseModel):
    """Bin / zone in a location tree (WMS-001)."""

    warehouse_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    code: str = ""
    name: str = ""
    location_type: str = "bin"
    is_pickable: bool = True
    is_receivable: bool = True
    max_weight_kg: float | None = None
    barcode: str = ""


@dataclass
class Product(BaseModel):
    """SKU master (WMS-002)."""

    sku: str = ""
    name: str = ""
    barcode: str = ""
    uom: str = "pcs"
    weight_kg: float = 0.0
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False


@dataclass
class Quant(BaseModel):
    """On-hand balance per product + location (WMS-003)."""

    product_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    lot_id: uuid.UUID | None = None
    quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    incoming_quantity: Decimal = Decimal("0")
