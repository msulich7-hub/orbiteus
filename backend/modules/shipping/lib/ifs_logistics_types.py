"""Canonical IFS logistics payload (mercato-logistics-hub ifs-logistics-payload.ts)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LogisticsPackageType = Literal["parcel", "pallet", "locker"]


class IfsLogisticsLine(BaseModel):
    line_no: int | None = None
    type: LogisticsPackageType | None = None
    pack_type: str | None = None
    qty: float | int | None = None
    weight_kg: float | None = None
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    paczkomat: bool = False
    locker_point_id: str | None = None
    catalog_no: str | None = None
    catalog_desc: str | None = None


class IfsLogisticsAddress(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    line1: str = ""
    line2: str | None = None
    city: str = ""
    postal_code: str = ""
    country_code: str = "PL"
    phone: str | None = None
    email: str | None = None


class HandlingUnitSummary(BaseModel):
    pack_type: str
    type: Literal["pallet", "parcel"]
    qty: int
    weight_kg: float | None = None
    length_cm: float = 0
    width_cm: float = 0
    height_cm: float = 0


class LogisticsMeta(BaseModel):
    tracking_number: str | None = None
    customer_order_no: str | None = None
    is_vip: bool = False
    packing_date: str | None = None
    coordinator: str | None = None
    packer: str | None = None
    invoice_no: str | None = None
    email_notification: bool = False


class IfsLogisticsPayload(BaseModel):
    shipment_id: str | int
    contract: str | None = None
    order_no: str | None = None
    objstate: str | None = None
    total_weight_kg: float | None = None
    forward_agent_id: str | None = None
    dsv_pickup_location: str | None = None
    note_text: str | None = None
    custom_fields: dict[str, Any] | None = None
    logistics_meta: LogisticsMeta | None = None
    handling_units_summary: list[HandlingUnitSummary] | None = None
    destination: IfsLogisticsAddress
    sender: IfsLogisticsAddress | None = None
    lines: list[IfsLogisticsLine] = Field(default_factory=list)

    def model_dump_json_ready(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
