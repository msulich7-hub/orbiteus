"""Shipping domain models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from orbiteus_core.base_domain import BaseModel

SHIPMENT_STATES = (
    "draft",
    "queued",
    "label_created",
    "dispatched",
    "delivered",
    "failed",
    "cancelled",
)

IFS_QUEUE_STATES = (
    "queued",
    "claimed",
    "in_dispatch",
    "completed",
    "failed",
    "processing",
    "dispatched",
)

DISPATCH_STATES = (
    "draft",
    "composing",
    "submitting",
    "partial_labels",
    "ready_to_print",
    "closed",
    "cancelled",
)

WAYBILL_STATES = (
    "draft",
    "queued",
    "label_created",
    "failed",
    "cancelled",
)


@dataclass
class Shipment(BaseModel):
    """Outbound shipment linked to orders.order via UUID only."""

    order_id: uuid.UUID | None = None
    carrier_code: str = "MOCK"
    state: str = "draft"
    tracking_number: str = ""
    weight_kg: float = 0.0
    is_pallet: bool = False
    is_locker: bool = False
    forward_agent_id: str = ""
    reference: str = ""
    label_payload_json: str = "{}"
    error_message: str = ""


@dataclass
class IfsShipmentQueue(BaseModel):
    """Inbound IFS shipment from Oracle webhook (SECONDARY path)."""

    ifs_shipment_id: str = ""
    ifs_sid: str = ""
    objstate: str = ""
    payload_json: str = "{}"
    state: str = "queued"
    dispatch_id: uuid.UUID | None = None
    error_message: str = ""


@dataclass
class Dispatch(BaseModel):
    """Kiosk workspace for one IFS shipment."""

    ifs_queue_id: uuid.UUID | None = None
    ifs_shipment_id: str = ""
    state: str = "draft"
    pickup_site_code: str = ""
    recommended_carrier_code: str = "MOCK"
    destination_json: str = "{}"
    sender_json: str = "{}"
    metadata_json: str = "{}"
    waybill_count: int = 1
    assigned_user_id: uuid.UUID | None = None


@dataclass
class HandlingUnit(BaseModel):
    """Draggable pack tile within a dispatch workspace."""

    dispatch_id: uuid.UUID | None = None
    pack_type: str = ""
    unit_type: str = "parcel"
    qty: int = 1
    weight_kg: float = 0.0
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0
    waybill_id: uuid.UUID | None = None
    sequence: int = 0


@dataclass
class Waybill(BaseModel):
    """One carrier label job within a dispatch."""

    dispatch_id: uuid.UUID | None = None
    sequence: int = 1
    carrier_code: str = "MOCK"
    state: str = "draft"
    tracking_number: str = ""
    label_attachment_id: uuid.UUID | None = None
    label_payload_json: str = "{}"
    error_message: str = ""
    submitted_at: object | None = None
    label_created_at: object | None = None
