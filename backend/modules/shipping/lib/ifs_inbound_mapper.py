"""Build IfsLogisticsPayload from raw IFS webhook (mercato ifs_bridge webhook route.ts)."""

from __future__ import annotations

from typing import Any

from modules.shipping.lib.cf_handling_units_parser import (
    HandlingUnit,
    merge_ifs_payload_lines_with_cf_handling_units,
    parse_cf_handling_units,
    parse_cf_logistics_metadata,
)
from modules.shipping.lib.coerce_ifs_payload import coerce_ifs_logistics_payload
from modules.shipping.lib.ifs_dispatch_profiles import resolve_ifs_dispatch_profile
from modules.shipping.lib.ifs_logistics_types import (
    HandlingUnitSummary,
    IfsLogisticsPayload,
    LogisticsMeta,
)


def _handling_units_to_summary(units: list[HandlingUnit]) -> list[HandlingUnitSummary]:
    return [
        HandlingUnitSummary(
            pack_type=u.pack_type,
            type=u.type,
            qty=u.qty,
            weight_kg=u.weight_kg,
            length_cm=u.length_cm,
            width_cm=u.width_cm,
            height_cm=u.height_cm,
        )
        for u in units
    ]


def build_logistics_payload_from_ifs_webhook(raw: dict[str, Any]) -> IfsLogisticsPayload:
    """Map MS_INTEGRATION_API JSON → canonical queue payload."""
    cf = raw.get("custom_fields") if isinstance(raw.get("custom_fields"), dict) else None
    cf_handling = parse_cf_handling_units(cf) if cf else []
    cf_meta = parse_cf_logistics_metadata(cf) if cf else None

    merged_lines = merge_ifs_payload_lines_with_cf_handling_units(
        raw.get("lines") if isinstance(raw.get("lines"), list) else None,
        cf,
    )

    dispatch_profile = resolve_ifs_dispatch_profile(raw.get("contract"))
    total_weight = None
    if cf_meta and cf_meta.total_net_weight is not None:
        total_weight = cf_meta.total_net_weight
    elif raw.get("total_weight") is not None:
        total_weight = float(raw["total_weight"])
    elif raw.get("total_weight_kg") is not None:
        total_weight = float(raw["total_weight_kg"])

    forward_agent = (
        cf_meta.carrier_code if cf_meta and cf_meta.carrier_code else raw.get("forward_agent_id")
    )

    body: dict[str, Any] = {
        "shipment_id": raw["shipment_id"],
        "contract": raw.get("contract"),
        "order_no": raw.get("order_no"),
        "objstate": raw.get("objstate"),
        "total_weight_kg": total_weight,
        "forward_agent_id": forward_agent,
        "note_text": (cf_meta.logistics_notes if cf_meta else None) or raw.get("note_text"),
        "destination": {
            "company_name": raw.get("customer_address_name"),
            "contact_name": raw.get("deliver_to_customer_no"),
            "line1": raw.get("customer_address1") or raw.get("customer_address_name") or "",
            "line2": raw.get("customer_address2"),
            "city": raw.get("customer_city") or "",
            "postal_code": raw.get("customer_zip_code") or "",
            "country_code": raw.get("customer_country") or "PL",
            "phone": raw.get("customer_phone"),
            "email": raw.get("customer_email"),
        },
        "lines": merged_lines,
    }

    if dispatch_profile:
        body["dsv_pickup_location"] = dispatch_profile.dsv_pickup_location_key
        body["sender"] = {
            "company_name": dispatch_profile.sender_company_name,
            "line1": dispatch_profile.origin_line1,
            "line2": dispatch_profile.origin_line2,
            "city": dispatch_profile.origin_city,
            "postal_code": dispatch_profile.origin_postal_code,
            "country_code": dispatch_profile.origin_country_code,
        }

    if cf:
        body["custom_fields"] = cf

    if cf_meta:
        body["logistics_meta"] = LogisticsMeta(
            tracking_number=cf_meta.tracking_number,
            customer_order_no=cf_meta.customer_order_no,
            is_vip=cf_meta.is_vip,
            packing_date=cf_meta.packing_date,
            coordinator=cf_meta.coordinator,
            packer=cf_meta.packer,
            invoice_no=cf_meta.invoice_no,
            email_notification=cf_meta.email_notification,
        ).model_dump()

    if cf_handling:
        body["handling_units_summary"] = [
            u.model_dump() for u in _handling_units_to_summary(cf_handling)
        ]

    return coerce_ifs_logistics_payload(body)


def payload_to_dispatch_packages(payload: IfsLogisticsPayload) -> list[dict[str, Any]]:
    """Convert queue lines → packages list for build_shipment_request_from_ifs."""
    packages: list[dict[str, Any]] = []
    for i, line in enumerate(payload.lines):
        pack_type = line.pack_type
        if not pack_type:
            continue
        qty = max(1, int(line.qty or 1))
        packages.append(
            {
                "pack_type": pack_type,
                "quantity": qty,
                "weight_kg": line.weight_kg,
                "length_cm": line.length_cm,
                "width_cm": line.width_cm,
                "height_cm": line.height_cm,
                "source_line_index": i,
            }
        )
    if packages:
        return packages

    for i, hu in enumerate(payload.handling_units_summary or []):
        packages.append(
            {
                "pack_type": hu.pack_type,
                "quantity": hu.qty,
                "weight_kg": hu.weight_kg,
                "length_cm": hu.length_cm,
                "width_cm": hu.width_cm,
                "height_cm": hu.height_cm,
                "source_line_index": i,
            }
        )
    return packages


def payload_to_ifs_dispatch_dict(payload: IfsLogisticsPayload) -> dict[str, Any]:
    """Minimal ifs_payload dict for dispatch adapters."""
    dest = payload.destination
    return {
        "shipment_id": payload.shipment_id,
        "order_no": payload.order_no or str(payload.shipment_id),
        "contract": payload.contract,
        "total_weight_kg": payload.total_weight_kg,
        "forward_agent_id": payload.forward_agent_id,
        "note_text": payload.note_text,
        "destination": {
            "company_name": dest.company_name,
            "contact_name": dest.contact_name,
            "line1": dest.line1,
            "line2": dest.line2,
            "city": dest.city,
            "postal_code": dest.postal_code,
            "country_code": dest.country_code,
            "phone": dest.phone,
            "email": dest.email,
        },
        "sender": payload.sender.model_dump() if payload.sender else None,
    }
