"""Pydantic schemas for shipping.shipment."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID | None = None
    carrier_code: str
    state: str
    tracking_number: str = ""
    weight_kg: float = 0.0
    is_pallet: bool = False
    is_locker: bool = False
    forward_agent_id: str = ""
    reference: str = ""
    error_message: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ShipmentWrite(BaseModel):
    order_id: uuid.UUID | None = None
    carrier_code: str = "MOCK"
    state: str = "draft"
    weight_kg: float = 0.0
    is_pallet: bool = False
    is_locker: bool = False
    forward_agent_id: str = ""
    reference: str = ""


class AddressBody(BaseModel):
    company_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    address: str = ""
    address2: str | None = None
    zip: str = ""
    city: str = ""
    country: str = "PL"
    phone: str | None = None
    email: str | None = None


class ParcelBody(BaseModel):
    weight: float = Field(default=1.0, ge=0.01)
    length: float | None = None
    width: float | None = None
    height: float | None = None
    pack_type: str | None = None
    reference: str | None = None


class DispatchBody(BaseModel):
    order_id: uuid.UUID
    weight_kg: float = Field(default=1.0, ge=0)
    is_pallet: bool = False
    is_locker: bool = False
    forward_agent_id: str = ""
    force_carrier: str | None = None
    recipient: AddressBody | None = None
    parcels: list[ParcelBody] | None = None
    ifs_payload: dict | None = None
    packages: list[dict] | None = None


class SimulateBody(BaseModel):
    weight_kg: float = Field(default=1.0, ge=0)
    is_pallet: bool = False
    is_locker: bool = False
    forward_agent_id: str = ""


class CarrierStatusResponse(BaseModel):
    configured_carriers: list[str]
    routing_defaults: dict[str, str | float | bool]


class IfsQueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ifs_shipment_id: str
    ifs_sid: str = ""
    objstate: str = ""
    state: str = "queued"
    payload_json: str = "{}"
    error_message: str = ""
    tenant_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IfsQueueWrite(BaseModel):
    ifs_shipment_id: str
    ifs_sid: str = ""
    objstate: str = ""
    payload_json: str = "{}"
    state: str = "queued"
    error_message: str = ""


class IfsQueueRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ifs_shipment_id: str
    ifs_sid: str = ""
    objstate: str = ""
    state: str = "queued"
    payload_json: str = "{}"
    error_message: str = ""
    order_no: str | None = None
    forward_agent_id: str | None = None
    total_weight_kg: float | None = None
    line_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IfsQueueDispatchBody(BaseModel):
    order_id: uuid.UUID
    force_carrier: str | None = None


class DispatchAcceptedResponse(BaseModel):
    ok: bool = True
    outbox_id: str
    state: str = "processing"
    ifs_shipment_id: str | None = None
