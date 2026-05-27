"""Shipping SQLAlchemy mapping."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping

from modules.shipping.controller.repositories import IfsQueueRepository, ShipmentRepository
from modules.shipping.model import schemas
from modules.shipping.model.domain import IfsShipmentQueue, Shipment

shipments_table: Table | None = None
ifs_shipment_queue_table: Table | None = None


def _build_tables() -> Table:
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
        Column("error_message", Text, server_default=""),
    )


def setup() -> None:
    global shipments_table, ifs_shipment_queue_table
    shipments_table = _build_tables()
    ifs_shipment_queue_table = _build_ifs_queue_table()
    register_mapping(Shipment, shipments_table)
    register_mapping(IfsShipmentQueue, ifs_shipment_queue_table)
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
