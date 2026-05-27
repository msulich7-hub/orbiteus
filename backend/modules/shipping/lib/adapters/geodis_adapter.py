"""Orbiteus Geodis adapter — native Python (no Mercato subprocess)."""

from __future__ import annotations

from typing import Any

from modules.shipping.lib.adapters.geodis.client import GeodisCarrier
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


def _build_request_from_dispatch(payload: dict[str, Any]) -> ShipmentRequest:
    if payload.get("ifs_payload") and payload.get("packages"):
        return build_shipment_request_from_ifs(
            payload["ifs_payload"],
            payload.get("carrier_code") or "GEODIS",
            payload["packages"],
        )

    recipient_raw = payload.get("recipient") or {
        "company_name": "Firma Testowa Sp. z o.o.",
        "address": "ul. Testowa 1",
        "zip": "00-001",
        "city": "Warszawa",
        "country": "PL",
        "phone": "+48123456789",
    }
    parcels_raw = payload.get("parcels")
    if parcels_raw:
        parcels = [
            ParcelInfo(
                weight=float(p.get("weight") or 1),
                length=p.get("length"),
                width=p.get("width"),
                height=p.get("height"),
                pack_type=p.get("pack_type") or p.get("packType") or p.get("reference"),
                reference=p.get("reference"),
            )
            for p in parcels_raw
        ]
    else:
        weight = float(payload.get("weight_kg") or 150)
        parcels = [
            ParcelInfo(
                weight=weight,
                length=120,
                width=80,
                height=100,
                pack_type="EUR",
                reference="EUR",
            )
        ]

    opts = dict(payload.get("options") or {})
    if payload.get("is_pallet") and "srv_code" not in opts:
        opts.setdefault("srv_code", "ST")

    return ShipmentRequest(
        order_no=str(payload.get("reference") or payload.get("order_id") or "ORB-GEODIS"),
        contract=payload.get("contract"),
        customer_no=None,
        carrier_code="GEODIS",
        recipient=_party_from_dict(recipient_raw),
        sender=_party_from_dict(payload["sender"]) if payload.get("sender") else None,
        parcels=parcels,
        goods_description=payload.get("goods_description"),
        options=opts,
    )


class GeodisPythonAdapter:
    def __init__(self, code: str = "GEODIS") -> None:
        self.code = code.upper()
        self._carrier = GeodisCarrier()

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
