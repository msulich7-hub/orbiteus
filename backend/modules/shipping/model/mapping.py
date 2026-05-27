"""Shipping SQLAlchemy mapping."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping

from modules.shipping.controller.repositories import (
    DispatchRepository,
    HandlingUnitRepository,
    IfsQueueRepository,
    ShipmentRepository,
    WaybillRepository,
)
from modules.shipping.model import schemas
from modules.shipping.model.domain import (
    Dispatch,
    HandlingUnit,
    IfsShipmentQueue,
    Shipment,
    Waybill,
)

shipments_table: Table | None = None
ifs_shipment_queue_table: Table | None = None
dispatch_table: Table | None = None
handling_units_table: Table | None = None
waybills_table: Table | None = None


def _build_shipments_table() -> Table:
    return Table(
        "shipping_shipments",
        metadata,
        *make_base_columns(),
        Column("order_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("carrier_code", String(32), nullable=False, server_default="MOCK", index=True),
        Column("state", String(32), nullable=False, server_default="draft", index=True),
        Column("tracking_number", String(128), nullable=False, server_default=""),
        Column("weight_kg", Float, server_default="0", nullable=False),
        Column("is_pallet", Boolean, server_default="false", nullable=False),
        Column("is_locker", Boolean, server_default="false", nullable=False),
        Column("forward_agent_id", String(64), server_default=""),
        Column("reference", String(128), server_default=""),
        Column("label_payload_json", Text, server_default="{}"),
        Column("error_message", Text, server_default=""),
    )


def _build_ifs_queue_table() -> Table:
    return Table(
        "shipping_ifs_shipment_queue",
        metadata,
        *make_base_columns(),
        Column("ifs_shipment_id", String(64), nullable=False, unique=True, index=True),
        Column("ifs_sid", String(16), nullable=False, server_default=""),
        Column("objstate", String(64), nullable=False, server_default=""),
        Column("payload_json", Text, nullable=False, server_default="{}"),
        Column("state", String(32), nullable=False, server_default="queued", index=True),
        Column("dispatch_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("error_message", Text, server_default=""),
    )


def _build_dispatch_table() -> Table:
    return Table(
        "shipping_dispatch",
        metadata,
        *make_base_columns(),
        Column("ifs_queue_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("ifs_shipment_id", String(64), nullable=False, index=True),
        Column("state", String(32), nullable=False, server_default="draft", index=True),
        Column("pickup_site_code", String(16), server_default=""),
        Column("recommended_carrier_code", String(32), server_default="MOCK"),
        Column("destination_json", Text, server_default="{}"),
        Column("sender_json", Text, server_default="{}"),
        Column("metadata_json", Text, server_default="{}"),
        Column("waybill_count", Integer, server_default="1", nullable=False),
        Column("assigned_user_id", UUID(as_uuid=True), nullable=True),
    )


def _build_handling_units_table() -> Table:
    return Table(
        "shipping_handling_units",
        metadata,
        *make_base_columns(),
        Column(
            "dispatch_id",
            UUID(as_uuid=True),
            ForeignKey("shipping_dispatch.id"),
            nullable=False,
            index=True,
        ),
        Column("pack_type", String(32), nullable=False, server_default=""),
        Column("unit_type", String(16), nullable=False, server_default="parcel"),
        Column("qty", Integer, server_default="1", nullable=False),
        Column("weight_kg", Float, server_default="0", nullable=False),
        Column("length_cm", Float, server_default="0", nullable=False),
        Column("width_cm", Float, server_default="0", nullable=False),
        Column("height_cm", Float, server_default="0", nullable=False),
        Column("waybill_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("sequence", Integer, server_default="0", nullable=False),
    )


def _build_waybills_table() -> Table:
    return Table(
        "shipping_waybills",
        metadata,
        *make_base_columns(),
        Column(
            "dispatch_id",
            UUID(as_uuid=True),
            ForeignKey("shipping_dispatch.id"),
            nullable=False,
            index=True,
        ),
        Column("sequence", Integer, nullable=False),
        Column("carrier_code", String(32), nullable=False, server_default="MOCK"),
        Column("state", String(32), nullable=False, server_default="draft", index=True),
        Column("tracking_number", String(128), server_default=""),
        Column("label_attachment_id", UUID(as_uuid=True), nullable=True),
        Column("label_payload_json", Text, server_default="{}"),
        Column("error_message", Text, server_default=""),
        Column("submitted_at", DateTime(timezone=True), nullable=True),
        Column("label_created_at", DateTime(timezone=True), nullable=True),
        UniqueConstraint("dispatch_id", "sequence", name="uq_shipping_waybills_dispatch_sequence"),
    )


def setup() -> None:
    global shipments_table, ifs_shipment_queue_table, dispatch_table, handling_units_table, waybills_table
    shipments_table = _build_shipments_table()
    ifs_shipment_queue_table = _build_ifs_queue_table()
    dispatch_table = _build_dispatch_table()
    handling_units_table = _build_handling_units_table()
    waybills_table = _build_waybills_table()

    register_mapping(Shipment, shipments_table)
    register_mapping(IfsShipmentQueue, ifs_shipment_queue_table)
    register_mapping(Dispatch, dispatch_table)
    register_mapping(HandlingUnit, handling_units_table)
    register_mapping(Waybill, waybills_table)

    register_model(
        "shipping.shipment",
        Shipment,
        ShipmentRepository,
        shipments_table,
        schemas.ShipmentRead,
        schemas.ShipmentWrite,
    )
    register_model(
        "shipping.ifs_queue",
        IfsShipmentQueue,
        IfsQueueRepository,
        ifs_shipment_queue_table,
        schemas.IfsQueueRead,
        schemas.IfsQueueWrite,
    )
    register_model(
        "shipping.dispatch",
        Dispatch,
        DispatchRepository,
        dispatch_table,
        schemas.DispatchRead,
        schemas.DispatchWrite,
    )
    register_model(
        "shipping.handling_unit",
        HandlingUnit,
        HandlingUnitRepository,
        handling_units_table,
        schemas.HandlingUnitRead,
        schemas.HandlingUnitWrite,
    )
    register_model(
        "shipping.waybill",
        Waybill,
        WaybillRepository,
        waybills_table,
        schemas.WaybillRead,
        schemas.WaybillWrite,
    )
