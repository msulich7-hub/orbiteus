"""Pydantic schemas for shipping module."""

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
    dispatch_id: uuid.UUID | None = None
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
    dispatch_id: uuid.UUID | None = None
    error_message: str = ""


class IfsQueueRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ifs_shipment_id: str
    ifs_sid: str = ""
    objstate: str = ""
    state: str = "queued"
    dispatch_id: uuid.UUID | None = None
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


class DispatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DispatchWrite(BaseModel):
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


class HandlingUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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


class HandlingUnitWrite(BaseModel):
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


class WaybillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispatch_id: uuid.UUID | None = None
    sequence: int = 1
    carrier_code: str = "MOCK"
    state: str = "draft"
    tracking_number: str = ""
    label_attachment_id: uuid.UUID | None = None
    error_message: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WaybillWrite(BaseModel):
    dispatch_id: uuid.UUID | None = None
    sequence: int = 1
    carrier_code: str = "MOCK"
    state: str = "draft"
    tracking_number: str = ""
    label_attachment_id: uuid.UUID | None = None
    label_payload_json: str = "{}"
    error_message: str = ""


class PreviewHandlingUnit(BaseModel):
    id: str
    type: str
    pack_type: str
    qty: int = 1
    weight_kg: float = 0.0
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0


class SuggestedWaybillPlan(BaseModel):
    index: int
    carrier_code: str
    hu_ids: list[str] = Field(default_factory=list)
    weight_kg: float = 0.0
    is_pallet: bool = False


class SuggestedPlan(BaseModel):
    waybills: list[SuggestedWaybillPlan] = Field(default_factory=list)


class ComposePreviewResponse(BaseModel):
    ifs_shipment_id: str
    queue_id: uuid.UUID
    state: str
    suggested_mode: str
    suggested_carrier: str
    order_no: str | None = None
    order_id: uuid.UUID | None = None
    recipient: dict | None = None
    handling_units: list[PreviewHandlingUnit] = Field(default_factory=list)
    suggested_plan: SuggestedPlan
    blocking_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ComposePlanBody(BaseModel):
    order_id: uuid.UUID | None = None
    waybills: list[dict] = Field(default_factory=list)


class ComposePlanResponse(BaseModel):
    saved: bool = True
    revision: int = 1
    dispatch_id: uuid.UUID | None = None


class DispatchPlanWaybillBody(BaseModel):
    carrier_code: str
    hu_ids: list[str] = Field(default_factory=list)
    parcels: list[dict] = Field(default_factory=list)
    is_pallet: bool = False
    force_carrier: str | None = None


class DispatchPlanBody(BaseModel):
    order_id: uuid.UUID
    waybills: list[DispatchPlanWaybillBody] = Field(default_factory=list)
    print_labels: bool = True


class WaybillJobResponse(BaseModel):
    index: int
    outbox_id: str
    waybill_id: uuid.UUID | None = None
    state: str = "processing"


class DispatchPlanResponse(BaseModel):
    ok: bool = True
    outbox_batch_id: str
    waybill_jobs: list[WaybillJobResponse] = Field(default_factory=list)
    ifs_shipment_id: str


class DispatchStatusWaybill(BaseModel):
    index: int
    waybill_id: uuid.UUID | None = None
    state: str
    tracking_number: str | None = None
    error_message: str | None = None


class DispatchStatusResponse(BaseModel):
    ifs_shipment_id: str
    queue_state: str
    dispatch_state: str | None = None
    waybills: list[DispatchStatusWaybill] = Field(default_factory=list)


class DispatchWorkspaceDispatch(BaseModel):
    id: uuid.UUID
    state: str
    ifs_shipment_id: str
    pickup_site_code: str = ""
    recommended_carrier_code: str = "MOCK"
    waybill_count: int = 1
    destination_json: str = "{}"
    sender_json: str = "{}"
    metadata_json: str = "{}"


class DispatchWorkspaceQueue(BaseModel):
    id: uuid.UUID
    objstate: str = ""
    payload_json: str = "{}"
    state: str = "queued"


class DispatchWorkspaceUnit(BaseModel):
    id: uuid.UUID
    pack_type: str
    unit_type: str
    qty: int
    weight_kg: float
    length_cm: float
    width_cm: float
    height_cm: float
    waybill_id: uuid.UUID | None = None
    sequence: int = 0


class DispatchWorkspaceWaybill(BaseModel):
    id: uuid.UUID
    sequence: int
    carrier_code: str
    state: str
    tracking_number: str = ""
    unit_ids: list[uuid.UUID] = Field(default_factory=list)


class DispatchWorkspaceRead(BaseModel):
    dispatch: DispatchWorkspaceDispatch
    queue: DispatchWorkspaceQueue | None = None
    units: list[DispatchWorkspaceUnit] = Field(default_factory=list)
    waybills: list[DispatchWorkspaceWaybill] = Field(default_factory=list)
    carriers: CarrierStatusResponse


class DispatchPatchBody(BaseModel):
    state: str | None = None
    waybill_count: int | None = Field(default=None, ge=1, le=5)


class AssignUnitBody(BaseModel):
    unit_id: uuid.UUID
    waybill_id: uuid.UUID | None = None


class StartDispatchResponse(BaseModel):
    dispatch_id: uuid.UUID


class IfsInboxCounts(BaseModel):
    queued: int = 0
    claimed: int = 0
    in_dispatch: int = 0
    completed: int = 0
    failed: int = 0


class IfsInboxResponse(BaseModel):
    items: list[IfsQueueRowRead] = Field(default_factory=list)
    counts: IfsInboxCounts


class WaybillSubmitBody(BaseModel):
    order_id: uuid.UUID


class WaybillSubmitResponse(BaseModel):
    ok: bool = True
    outbox_id: str
    state: str = "processing"
    waybill_id: uuid.UUID


class SubmitAllResponse(BaseModel):
    ok: bool = True
    outbox_ids: list[str] = Field(default_factory=list)
    state: str = "processing"
