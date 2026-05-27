"""Shipping IFS inbound queue table (shipping.ifs_queue).

Revision ID: m3g8b9c0d014
Revises: l2c3d4e5f013
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m3g8b9c0d014"
down_revision: Union[str, None] = "l2c3d4e5f013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116840)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116840)")


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
        conn = op.get_bind()
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'shipping_ifs_shipment_queue'"
            )
        ).scalar()
        if exists:
            return

        op.create_table(
            "shipping_ifs_shipment_queue",
            *_base_columns(),
            sa.Column("ifs_shipment_id", sa.String(length=64), nullable=False),
            sa.Column("ifs_sid", sa.String(length=16), server_default="", nullable=False),
            sa.Column("objstate", sa.String(length=64), server_default="", nullable=False),
            sa.Column("payload_json", sa.Text(), server_default="{}", nullable=False),
            sa.Column("state", sa.String(length=32), server_default="queued", nullable=False),
            sa.Column("error_message", sa.Text(), server_default="", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_shipping_ifs_shipment_queue")),
        )
        op.create_index(
            op.f("ix_shipping_ifs_shipment_queue_ifs_shipment_id"),
            "shipping_ifs_shipment_queue",
            ["ifs_shipment_id"],
            unique=True,
        )
        op.create_index(
            op.f("ix_shipping_ifs_shipment_queue_state"),
            "shipping_ifs_shipment_queue",
            ["state"],
        )
        op.create_index(
            op.f("ix_shipping_ifs_shipment_queue_tenant_id"),
            "shipping_ifs_shipment_queue",
            ["tenant_id"],
        )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_index(
            op.f("ix_shipping_ifs_shipment_queue_tenant_id"),
            table_name="shipping_ifs_shipment_queue",
        )
        op.drop_index(
            op.f("ix_shipping_ifs_shipment_queue_state"),
            table_name="shipping_ifs_shipment_queue",
        )
        op.drop_index(
            op.f("ix_shipping_ifs_shipment_queue_ifs_shipment_id"),
            table_name="shipping_ifs_shipment_queue",
        )
        op.drop_table("shipping_ifs_shipment_queue")
    finally:
        _advisory_unlock()
