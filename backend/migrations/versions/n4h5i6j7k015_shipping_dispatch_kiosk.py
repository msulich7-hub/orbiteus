"""Shipping dispatch kiosk tables (dispatch, waybill, handling_unit).

Revision ID: n4h5i6j7k015
Revises: m3g8b9c0d014
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n4h5i6j7k015"
down_revision: Union[str, None] = "m3g8b9c0d014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116841)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116841)")


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

        if not insp.has_table("shipping_dispatch"):
            op.create_table(
                "shipping_dispatch",
                *_base_columns(),
                sa.Column("ifs_queue_id", sa.UUID(), nullable=True),
                sa.Column("ifs_shipment_id", sa.String(length=64), nullable=False),
                sa.Column("state", sa.String(length=32), server_default="draft", nullable=False),
                sa.Column("pickup_site_code", sa.String(length=16), server_default=""),
                sa.Column("recommended_carrier_code", sa.String(length=32), server_default="MOCK"),
                sa.Column("destination_json", sa.Text(), server_default="{}"),
                sa.Column("sender_json", sa.Text(), server_default="{}"),
                sa.Column("metadata_json", sa.Text(), server_default="{}"),
                sa.Column("waybill_count", sa.Integer(), server_default="1", nullable=False),
                sa.Column("assigned_user_id", sa.UUID(), nullable=True),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_shipping_dispatch")),
            )
            op.create_index(
                op.f("ix_shipping_dispatch_ifs_shipment_id"),
                "shipping_dispatch",
                ["ifs_shipment_id"],
            )
            op.create_index(
                op.f("ix_shipping_dispatch_tenant_id"),
                "shipping_dispatch",
                ["tenant_id"],
            )
            op.create_index(
                op.f("ix_shipping_dispatch_state"),
                "shipping_dispatch",
                ["state"],
            )

        if not insp.has_table("shipping_handling_units"):
            op.create_table(
                "shipping_handling_units",
                *_base_columns(),
                sa.Column("dispatch_id", sa.UUID(), nullable=False),
                sa.Column("pack_type", sa.String(length=32), nullable=False, server_default=""),
                sa.Column("unit_type", sa.String(length=16), server_default="parcel", nullable=False),
                sa.Column("qty", sa.Integer(), server_default="1", nullable=False),
                sa.Column("weight_kg", sa.Float(), server_default="0", nullable=False),
                sa.Column("length_cm", sa.Float(), server_default="0", nullable=False),
                sa.Column("width_cm", sa.Float(), server_default="0", nullable=False),
                sa.Column("height_cm", sa.Float(), server_default="0", nullable=False),
                sa.Column("waybill_id", sa.UUID(), nullable=True),
                sa.Column("sequence", sa.Integer(), server_default="0", nullable=False),
                sa.ForeignKeyConstraint(
                    ["dispatch_id"],
                    ["shipping_dispatch.id"],
                    name=op.f("fk_shipping_handling_units_dispatch_id_shipping_dispatch"),
                ),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_shipping_handling_units")),
            )
            op.create_index(
                op.f("ix_shipping_handling_units_dispatch_id"),
                "shipping_handling_units",
                ["dispatch_id"],
            )
            op.create_index(
                op.f("ix_shipping_handling_units_waybill_id"),
                "shipping_handling_units",
                ["waybill_id"],
            )

        if not insp.has_table("shipping_waybills"):
            op.create_table(
                "shipping_waybills",
                *_base_columns(),
                sa.Column("dispatch_id", sa.UUID(), nullable=False),
                sa.Column("sequence", sa.Integer(), nullable=False),
                sa.Column("carrier_code", sa.String(length=32), server_default="MOCK", nullable=False),
                sa.Column("state", sa.String(length=32), server_default="draft", nullable=False),
                sa.Column("tracking_number", sa.String(length=128), server_default=""),
                sa.Column("label_attachment_id", sa.UUID(), nullable=True),
                sa.Column("label_payload_json", sa.Text(), server_default="{}"),
                sa.Column("error_message", sa.Text(), server_default=""),
                sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("label_created_at", sa.DateTime(timezone=True), nullable=True),
                sa.ForeignKeyConstraint(
                    ["dispatch_id"],
                    ["shipping_dispatch.id"],
                    name=op.f("fk_shipping_waybills_dispatch_id_shipping_dispatch"),
                ),
                sa.PrimaryKeyConstraint("id", name=op.f("pk_shipping_waybills")),
                sa.UniqueConstraint(
                    "dispatch_id",
                    "sequence",
                    name="uq_shipping_waybills_dispatch_sequence",
                ),
            )
            op.create_index(
                op.f("ix_shipping_waybills_dispatch_id"),
                "shipping_waybills",
                ["dispatch_id"],
            )
            op.create_index(
                op.f("ix_shipping_waybills_state"),
                "shipping_waybills",
                ["state"],
            )

        if insp.has_table("shipping_ifs_shipment_queue"):
            cols = {c["name"] for c in insp.get_columns("shipping_ifs_shipment_queue")}
            if "dispatch_id" not in cols:
                op.add_column(
                    "shipping_ifs_shipment_queue",
                    sa.Column("dispatch_id", sa.UUID(), nullable=True),
                )
                op.create_index(
                    op.f("ix_shipping_ifs_shipment_queue_dispatch_id"),
                    "shipping_ifs_shipment_queue",
                    ["dispatch_id"],
                )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        bind = op.get_bind()
        insp = sa.inspect(bind)
        if insp.has_table("shipping_ifs_shipment_queue"):
            cols = {c["name"] for c in insp.get_columns("shipping_ifs_shipment_queue")}
            if "dispatch_id" in cols:
                op.drop_index(
                    op.f("ix_shipping_ifs_shipment_queue_dispatch_id"),
                    table_name="shipping_ifs_shipment_queue",
                )
                op.drop_column("shipping_ifs_shipment_queue", "dispatch_id")
        if insp.has_table("shipping_waybills"):
            op.drop_table("shipping_waybills")
        if insp.has_table("shipping_handling_units"):
            op.drop_table("shipping_handling_units")
        if insp.has_table("shipping_dispatch"):
            op.drop_table("shipping_dispatch")
    finally:
        _advisory_unlock()
