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
    "processing",
    "dispatched",
    "failed",
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
    error_message: str = ""
