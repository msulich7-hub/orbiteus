"""Pydantic schemas for inventory module."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    address_json: dict[str, Any] = Field(default_factory=dict)
    create_date: datetime | None = None
    write_date: datetime | None = None


class WarehouseWrite(BaseModel):
    code: str
    name: str = ""
    address_json: dict[str, Any] = Field(default_factory=dict)


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    warehouse_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    code: str
    name: str = ""
    location_type: str = "bin"
    is_pickable: bool = True
    is_receivable: bool = True
    max_weight_kg: float | None = None
    barcode: str = ""
    create_date: datetime | None = None
    write_date: datetime | None = None


class LocationWrite(BaseModel):
    warehouse_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    code: str
    name: str = ""
    location_type: str = "bin"
    is_pickable: bool = True
    is_receivable: bool = True
    max_weight_kg: float | None = None
    barcode: str = ""


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    barcode: str = ""
    uom: str = "pcs"
    weight_kg: float = 0.0
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    create_date: datetime | None = None
    write_date: datetime | None = None


class ProductWrite(BaseModel):
    sku: str
    name: str = ""
    barcode: str = ""
    uom: str = "pcs"
    weight_kg: float = 0.0
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False


class QuantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    lot_id: uuid.UUID | None = None
    quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    incoming_quantity: Decimal = Decimal("0")
    create_date: datetime | None = None
    write_date: datetime | None = None


class QuantWrite(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    incoming_quantity: Decimal = Decimal("0")
