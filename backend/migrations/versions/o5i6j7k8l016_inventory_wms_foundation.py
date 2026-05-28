"""Inventory WMS foundation tables (warehouse, location, product, quant).

Revision ID: o5i6j7k8l016
Revises: n4h5i6j7k015
Create Date: 2026-05-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o5i6j7k8l016"
down_revision: Union[str, None] = "n4h5i6j7k015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116842)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116842)")


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("custom_fields", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("modified_by_id", sa.UUID(), nullable=True),
    ]


def upgrade() -> None:
    _advisory_lock()
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)

        if not insp.has_table("inventory_warehouses"):
            op.create_table(
                "inventory_warehouses",
                *_base_columns(),
                sa.Column("code", sa.String(length=32), nullable=False),
                sa.Column("name", sa.String(length=255), server_default="", nullable=False),
                sa.Column("address_json", sa.JSON(), server_default="{}", nullable=False),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_warehouses")),
                sa.UniqueConstraint(
                    "tenant_id",
                    "code",
                    name=op.f("uq_inventory_warehouses_tenant_code"),
                ),
            )
            op.create_index(
                op.f("ix_inventory_warehouses_tenant_id"),
                "inventory_warehouses",
                ["tenant_id"],
            )

        if not insp.has_table("inventory_locations"):
            op.create_table(
                "inventory_locations",
                *_base_columns(),
                sa.Column("warehouse_id", sa.UUID(), nullable=False),
                sa.Column("parent_id", sa.UUID(), nullable=True),
                sa.Column("code", sa.String(length=64), nullable=False),
                sa.Column("name", sa.String(length=255), server_default="", nullable=False),
                sa.Column("location_type", sa.String(length=32), server_default="bin", nullable=False),
                sa.Column("is_pickable", sa.Boolean(), server_default="true", nullable=False),
                sa.Column("is_receivable", sa.Boolean(), server_default="true", nullable=False),
                sa.Column("max_weight_kg", sa.Float(), nullable=True),
                sa.Column("barcode", sa.String(length=128), server_default="", nullable=False),
                sa.ForeignKeyConstraint(
                    ["warehouse_id"],
                    ["inventory_warehouses.id"],
                    name=op.f("fk_inventory_locations_warehouse_id"),
                ),
                sa.ForeignKeyConstraint(
                    ["parent_id"],
                    ["inventory_locations.id"],
                    name=op.f("fk_inventory_locations_parent_id"),
                ),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_locations")),
                sa.UniqueConstraint(
                    "warehouse_id",
                    "code",
                    name=op.f("uq_inventory_locations_warehouse_code"),
                ),
                sa.UniqueConstraint(
                    "warehouse_id",
                    "barcode",
                    name=op.f("uq_inventory_locations_warehouse_barcode"),
                ),
            )
            op.create_index(
                op.f("ix_inventory_locations_tenant_id"),
                "inventory_locations",
                ["tenant_id"],
            )
            op.create_index(
                op.f("ix_inventory_locations_warehouse_id"),
                "inventory_locations",
                ["warehouse_id"],
            )

        if not insp.has_table("inventory_products"):
            op.create_table(
                "inventory_products",
                *_base_columns(),
                sa.Column("sku", sa.String(length=64), nullable=False),
                sa.Column("name", sa.String(length=255), server_default="", nullable=False),
                sa.Column("barcode", sa.String(length=128), server_default="", nullable=False),
                sa.Column("uom", sa.String(length=16), server_default="pcs", nullable=False),
                sa.Column("weight_kg", sa.Float(), server_default="0", nullable=False),
                sa.Column("is_lot_tracked", sa.Boolean(), server_default="false", nullable=False),
                sa.Column("is_serial_tracked", sa.Boolean(), server_default="false", nullable=False),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_products")),
                sa.UniqueConstraint(
                    "tenant_id",
                    "sku",
                    name=op.f("uq_inventory_products_tenant_sku"),
                ),
            )
            op.create_index(
                op.f("ix_inventory_products_tenant_id"),
                "inventory_products",
                ["tenant_id"],
            )

        if not insp.has_table("inventory_quants"):
            op.create_table(
                "inventory_quants",
                *_base_columns(),
                sa.Column("product_id", sa.UUID(), nullable=False),
                sa.Column("location_id", sa.UUID(), nullable=False),
                sa.Column("lot_id", sa.UUID(), nullable=True),
                sa.Column("quantity", sa.Numeric(16, 4), server_default="0", nullable=False),
                sa.Column("reserved_quantity", sa.Numeric(16, 4), server_default="0", nullable=False),
                sa.Column("incoming_quantity", sa.Numeric(16, 4), server_default="0", nullable=False),
                sa.ForeignKeyConstraint(
                    ["product_id"],
                    ["inventory_products.id"],
                    name=op.f("fk_inventory_quants_product_id"),
                ),
                sa.ForeignKeyConstraint(
                    ["location_id"],
                    ["inventory_locations.id"],
                    name=op.f("fk_inventory_quants_location_id"),
                ),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_quants")),
                sa.UniqueConstraint(
                    "tenant_id",
                    "product_id",
                    "location_id",
                    "lot_id",
                    name=op.f("uq_inventory_quants_tenant_product_location_lot"),
                ),
            )
            op.create_index(
                op.f("ix_inventory_quants_tenant_id"),
                "inventory_quants",
                ["tenant_id"],
            )
            op.create_index(
                op.f("ix_inventory_quants_product_id"),
                "inventory_quants",
                ["product_id"],
            )
            op.create_index(
                op.f("ix_inventory_quants_location_id"),
                "inventory_quants",
                ["location_id"],
            )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_table("inventory_quants")
        op.drop_table("inventory_products")
        op.drop_table("inventory_locations")
        op.drop_table("inventory_warehouses")
    finally:
        _advisory_unlock()
