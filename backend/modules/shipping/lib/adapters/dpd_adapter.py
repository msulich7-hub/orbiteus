"""Orbiteus DPD adapter — native Python (no Mercato subprocess)."""

from __future__ import annotations

from typing import Any

from modules.shipping.lib.adapters.dpd.client import DpdCarrier
from modules.shipping.lib.ifs_dispatch_profiles import resolve_ifs_dispatch_profile
from modules.shipping.lib.ifs_mapper import build_shipment_request_from_ifs
from modules.shipping.lib.shipment_types import ParcelInfo, ShipmentAddressParty, ShipmentRequest


def _party_from_dict(raw: dict[str, Any]) -> ShipmentAddressParty:
    return ShipmentAddressParty(
        company_name=raw.get("company_name") or raw.get("companyName"),
        first_name=raw.get("first_name") or raw.get("firstName"),
        last_name=raw.get("last_name") or raw.get("lastName"),
        address=raw.get("address") or "",
        address2=raw.get("address2"),
        zip=raw.get("zip") or "",
        city=raw.get("city") or "",
        country=raw.get("country") or "PL",
        phone=raw.get("phone"),
        email=raw.get("email"),
    )


def sender_from_ifs_contract(contract: str | None) -> ShipmentAddressParty | None:
    """Map BIS/CIE/BAZ contract prefix to DPD sender address."""
    profile = resolve_ifs_dispatch_profile(contract)
    if profile is None:
        return None
    return ShipmentAddressParty(
        company_name=profile.sender_company_name,
        first_name=None,
        last_name=None,
        address=profile.origin_line1,
        address2=profile.origin_line2,
        zip=profile.origin_postal_code,
        city=profile.origin_city,
        country=profile.origin_country_code,
    )


def _build_request_from_dispatch(payload: dict[str, Any]) -> ShipmentRequest:
    if payload.get("ifs_payload") and payload.get("packages"):
        return build_shipment_request_from_ifs(
            payload["ifs_payload"],
            payload.get("carrier_code") or "DPD",
            payload["packages"],
        )

    contract = payload.get("contract")
    sender = _party_from_dict(payload["sender"]) if payload.get("sender") else None
    if sender is None and contract:
        sender = sender_from_ifs_contract(str(contract))

    recipient_raw = payload.get("recipient") or {
        "company_name": "Firma Testowa Sp. z o.o.",
        "first_name": "Jan",
        "last_name": "Kowalski",
        "address": "ul. Testowa 1",
        "zip": "02-274",
        "city": "Warszawa",
        "country": "PL",
        "phone": "+48123456789",
        "email": "test@example.com",
    }

    parcels_raw = payload.get("parcels")
    if parcels_raw:
        parcels = [
            ParcelInfo(
                weight=float(p.get("weight") or 1),
                length=p.get("length"),
                width=p.get("width"),
                height=p.get("height"),
                reference=p.get("reference"),
                content=p.get("content"),
            )
            for p in parcels_raw
        ]
    else:
        weight = float(payload.get("weight_kg") or 5.5)
        parcels = [
            ParcelInfo(
                weight=weight,
                length=40,
                width=30,
                height=20,
                reference="S",
                content=payload.get("goods_description"),
            )
        ]

    return ShipmentRequest(
        order_no=str(payload.get("reference") or payload.get("order_id") or "ORB-DPD"),
        contract=contract,
        customer_no=None,
        carrier_code="DPD",
        recipient=_party_from_dict(recipient_raw),
        sender=sender,
        parcels=parcels,
        goods_description=payload.get("goods_description") or "Czesci zamienne - test DPD",
        options=dict(payload.get("options") or {}),
    )


class DpdPythonAdapter:
    def __init__(self, code: str = "DPD") -> None:
        self.code = code.upper()
        self._carrier = DpdCarrier()

    async def create_label(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = _build_request_from_dispatch({**payload, "carrier_code": self.code})
        result = await self._carrier.request_shipment(req)
        label_b64 = result.get("label_base64")
        if not label_b64 and isinstance(result.get("label_url"), str):
            url = result["label_url"]
            if url.startswith("data:") and "," in url:
                label_b64 = url.split(",", 1)[1]
        return {
            "carrier_code": self.code,
            "tracking_number": result.get("tracking_number") or "",
            "shipment_id": result.get("shipment_id"),
            "label_base64": label_b64,
            "label_url": result.get("label_url"),
            "raw": result.get("raw"),
        }
