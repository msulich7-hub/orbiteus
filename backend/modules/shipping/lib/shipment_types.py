"""Shipment request types — aligned with mercato-shipping-hub carrier.interface.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShipmentAddressParty:
    address: str
    zip: str
    city: str
    country: str = "PL"
    company_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    address2: str | None = None
    phone: str | None = None
    email: str | None = None


@dataclass
class ParcelInfo:
    weight: float
    length: float | None = None
    width: float | None = None
    height: float | None = None
    reference: str | None = None
    pack_type: str | None = None
    content: str | None = None


@dataclass
class ShipmentRequest:
    order_no: str
    carrier_code: str
    recipient: ShipmentAddressParty
    parcels: list[ParcelInfo]
    contract: str | None = None
    customer_no: str | None = None
    sender: ShipmentAddressParty | None = None
    goods_description: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
