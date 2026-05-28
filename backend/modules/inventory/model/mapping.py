"""Inventory SQLAlchemy mapping — WMS-001..003."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping

from modules.inventory.controller.repositories import (
    LocationRepository,
    ProductRepository,
    QuantRepository,
    WarehouseRepository,
)
from modules.inventory.model import schemas
from modules.inventory.model.domain import Location, Product, Quant, Warehouse

warehouses_table: Table | None = None
locations_table: Table | None = None
products_table: Table | None = None
quants_table: Table | None = None


def _build_warehouses_table() -> Table:
    return Table(
        "inventory_warehouses",
        metadata,
        *make_base_columns(),
        Column("code", String(32), nullable=False),
        Column("name", String(255), nullable=False, server_default=""),
        Column("address_json", JSONB, nullable=False, server_default="{}"),
        UniqueConstraint("tenant_id", "code", name="uq_inventory_warehouses_tenant_code"),
    )


def _build_locations_table() -> Table:
    return Table(
        "inventory_locations",
        metadata,
        *make_base_columns(),
        Column(
            "warehouse_id",
            UUID(as_uuid=True),
            ForeignKey("inventory_warehouses.id"),
            nullable=False,
            index=True,
        ),
        Column(
            "parent_id",
            UUID(as_uuid=True),
            ForeignKey("inventory_locations.id"),
            nullable=True,
            index=True,
        ),
        Column("code", String(64), nullable=False),
        Column("name", String(255), nullable=False, server_default=""),
        Column("location_type", String(32), nullable=False, server_default="bin"),
        Column("is_pickable", Boolean, server_default="true", nullable=False),
        Column("is_receivable", Boolean, server_default="true", nullable=False),
        Column("max_weight_kg", Float, nullable=True),
        Column("barcode", String(128), nullable=False, server_default=""),
        UniqueConstraint(
            "warehouse_id",
            "code",
            name="uq_inventory_locations_warehouse_code",
        ),
        UniqueConstraint(
            "warehouse_id",
            "barcode",
            name="uq_inventory_locations_warehouse_barcode",
        ),
    )


def _build_products_table() -> Table:
    return Table(
        "inventory_products",
        metadata,
        *make_base_columns(),
        Column("sku", String(64), nullable=False),
        Column("name", String(255), nullable=False, server_default=""),
        Column("barcode", String(128), nullable=False, server_default=""),
        Column("uom", String(16), nullable=False, server_default="pcs"),
        Column("weight_kg", Float, server_default="0", nullable=False),
        Column("is_lot_tracked", Boolean, server_default="false", nullable=False),
        Column("is_serial_tracked", Boolean, server_default="false", nullable=False),
        UniqueConstraint("tenant_id", "sku", name="uq_inventory_products_tenant_sku"),
    )


def _build_quants_table() -> Table:
    return Table(
        "inventory_quants",
        metadata,
        *make_base_columns(),
        Column(
            "product_id",
            UUID(as_uuid=True),
            ForeignKey("inventory_products.id"),
            nullable=False,
            index=True,
        ),
        Column(
            "location_id",
            UUID(as_uuid=True),
            ForeignKey("inventory_locations.id"),
            nullable=False,
            index=True,
        ),
        Column("lot_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("quantity", Numeric(16, 4), server_default="0", nullable=False),
        Column("reserved_quantity", Numeric(16, 4), server_default="0", nullable=False),
        Column("incoming_quantity", Numeric(16, 4), server_default="0", nullable=False),
        UniqueConstraint(
            "tenant_id",
            "product_id",
            "location_id",
            "lot_id",
            name="uq_inventory_quants_tenant_product_location_lot",
        ),
    )


def setup() -> None:
    global warehouses_table, locations_table, products_table, quants_table
    warehouses_table = _build_warehouses_table()
    locations_table = _build_locations_table()
    products_table = _build_products_table()
    quants_table = _build_quants_table()

    register_mapping(Warehouse, warehouses_table)
    register_mapping(Location, locations_table)
    register_mapping(Product, products_table)
    register_mapping(Quant, quants_table)

    register_model(
        "inventory.warehouse",
        Warehouse,
        WarehouseRepository,
        warehouses_table,
        schemas.WarehouseRead,
        schemas.WarehouseWrite,
    )
    register_model(
        "inventory.location",
        Location,
        LocationRepository,
        locations_table,
        schemas.LocationRead,
        schemas.LocationWrite,
    )
    register_model(
        "inventory.product",
        Product,
        ProductRepository,
        products_table,
        schemas.ProductRead,
        schemas.ProductWrite,
    )
    register_model(
        "inventory.quant",
        Quant,
        QuantRepository,
        quants_table,
        schemas.QuantRead,
        schemas.QuantWrite,
    )
