"""Map IFS logistics payload → ShipmentRequest (mercato-logistics-hub shipment-mapper.ts)."""

from __future__ import annotations

from typing import Any

from modules.shipping.lib.ifs_dispatch_profiles import resolve_ifs_dispatch_profile
from modules.shipping.lib.ifs_packaging import get_default_dimensions, resolve_carrier_pack_type
from modules.shipping.lib.shipment_types import ParcelInfo, ShipmentAddressParty, ShipmentRequest


def _ifs_address_to_party(raw: dict[str, Any]) -> ShipmentAddressParty:
    contact = (raw.get("contact_name") or "").strip()
    parts = contact.split(None, 1) if contact else []
    return ShipmentAddressParty(
        company_name=raw.get("company_name"),
        first_name=parts[0] if parts else None,
        last_name=parts[1] if len(parts) > 1 else None,
        address=raw.get("line1") or "",
        address2=raw.get("line2"),
        zip=raw.get("postal_code") or "",
        city=raw.get("city") or "",
        country=raw.get("country_code") or "PL",
        phone=raw.get("phone"),
        email=raw.get("email"),
    )


def _expand_parcels(
    packages: list[dict[str, Any]],
    carrier_code: str,
    payload: dict[str, Any],
) -> list[ParcelInfo]:
    out: list[ParcelInfo] = []
    unit_count = sum(max(1, int(p.get("quantity") or 1)) for p in packages)
    total_tare = sum(
        max(0.0, float(p.get("weight_kg") or 0)) * max(1, int(p.get("quantity") or 1))
        for p in packages
    )
    shipment_gross = max(0.0, float(payload.get("total_weight_kg") or 0))
    content_gross = max(0.0, shipment_gross - total_tare)
    content_per_unit = content_gross / unit_count if unit_count > 0 and content_gross > 0 else 0.0

    for pkg in packages:
        n = max(1, int(pkg.get("quantity") or 1))
        tare = max(0.0, float(pkg.get("weight_kg") or 0))
        gross = max(0.01, round(tare + content_per_unit, 2))
        ifs_pack = pkg.get("pack_type")
        pack_type = resolve_carrier_pack_type(carrier_code, ifs_pack)
        dims = get_default_dimensions(str(ifs_pack)) if ifs_pack else None
        for i in range(n):
            out.append(
                ParcelInfo(
                    weight=gross,
                    length=pkg.get("length_cm") or (dims.length_cm if dims else None),
                    width=pkg.get("width_cm") or (dims.width_cm if dims else None),
                    height=pkg.get("height_cm") or (dims.height_cm if dims else None),
                    reference=(
                        f"{pkg.get('pack_type')}-{pkg.get('source_line_index')}-{i + 1}"
                        if pkg.get("pack_type")
                        else None
                    ),
                    pack_type=pack_type,
                    content=payload.get("note_text"),
                )
            )
    return out or [ParcelInfo(weight=1.0)]


def build_shipment_request_from_ifs(
    payload: dict[str, Any],
    carrier_code: str,
    packages: list[dict[str, Any]],
) -> ShipmentRequest:
    """Build carrier-neutral ShipmentRequest from IFS logistics hub payload."""
    order_no = payload.get("order_no") or str(payload.get("shipment_id") or "ORB-SHIP")
    destination = payload.get("destination") or {}
    contract = payload.get("contract")
    dispatch_profile = resolve_ifs_dispatch_profile(contract)
    sender_raw = payload.get("sender")

    options: dict[str, Any] = {}
    sender_party: ShipmentAddressParty | None = None

    if dispatch_profile:
        options["pickupLocation"] = dispatch_profile.dsv_pickup_location_key
        sender_party = ShipmentAddressParty(
            company_name=dispatch_profile.sender_company_name,
            address=dispatch_profile.origin_line1,
            address2=dispatch_profile.origin_line2,
            zip=dispatch_profile.origin_postal_code,
            city=dispatch_profile.origin_city,
            country=dispatch_profile.origin_country_code,
        )
    elif sender_raw:
        sender_party = _ifs_address_to_party(sender_raw)

    return ShipmentRequest(
        order_no=str(order_no),
        contract=contract,
        customer_no=None,
        carrier_code=carrier_code.upper(),
        recipient=_ifs_address_to_party(destination),
        sender=sender_party,
        parcels=_expand_parcels(packages, carrier_code, payload),
        goods_description=payload.get("note_text"),
        options=options,
    )
