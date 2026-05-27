"""Coerce loose IFS webhook JSON → IfsLogisticsPayload (mercato coerce-ifs-payload.ts)."""

from __future__ import annotations

from typing import Any

from modules.shipping.lib.ifs_logistics_types import (
    HandlingUnitSummary,
    IfsLogisticsAddress,
    IfsLogisticsLine,
    IfsLogisticsPayload,
    LogisticsMeta,
)


def coerce_ifs_logistics_payload(body: Any) -> IfsLogisticsPayload:
    if not body or not isinstance(body, dict):
        raise ValueError("Body must be a JSON object")

    o: dict[str, Any] = body
    shipment_id = o.get("shipment_id", o.get("shipmentId"))
    if shipment_id is None:
        raise ValueError("Missing shipment_id")

    lines: list[IfsLogisticsLine] = []
    if isinstance(o.get("lines"), list):
        for i, line in enumerate(o["lines"]):
            if not isinstance(line, dict):
                continue
            lines.append(
                IfsLogisticsLine(
                    line_no=line.get("line_no") if isinstance(line.get("line_no"), int) else i + 1,
                    type=line.get("type"),
                    pack_type=line.get("pack_type") or line.get("packType"),
                    qty=line.get("qty") or line.get("qty_to_ship"),
                    weight_kg=line.get("weight_kg") or line.get("weight"),
                    length_cm=line.get("length_cm") or line.get("lengthCm"),
                    width_cm=line.get("width_cm") or line.get("widthCm"),
                    height_cm=line.get("height_cm") or line.get("heightCm"),
                    paczkomat=bool(line.get("paczkomat")),
                    locker_point_id=line.get("locker_point_id"),
                    catalog_no=line.get("catalog_no"),
                    catalog_desc=line.get("catalog_desc"),
                )
            )

    dest_src = o.get("destination") if isinstance(o.get("destination"), dict) else o
    destination = IfsLogisticsAddress(
        company_name=dest_src.get("customer_address_name")
        or dest_src.get("company_name")
        or dest_src.get("companyName"),
        contact_name=dest_src.get("contact_name") or dest_src.get("contactName"),
        line1=(
            dest_src.get("line1")
            or dest_src.get("customer_address1")
            or str(dest_src.get("customer_address_name") or "")
        ),
        line2=dest_src.get("line2") or dest_src.get("customer_address2"),
        city=str(dest_src.get("customer_city") or dest_src.get("city") or ""),
        postal_code=str(
            dest_src.get("customer_zip_code")
            or dest_src.get("postal_code")
            or dest_src.get("postalCode")
            or dest_src.get("zip")
            or ""
        ),
        country_code=str(
            dest_src.get("customer_country")
            or dest_src.get("country_code")
            or dest_src.get("countryCode")
            or "PL"
        ),
        phone=dest_src.get("customer_phone") or dest_src.get("phone"),
        email=dest_src.get("customer_email") or dest_src.get("email"),
    )

    if not destination.line1 or not destination.city:
        raise ValueError(
            "destination must include line1 and city (or customer_address_* fields)"
        )

    custom_fields = o.get("custom_fields") if isinstance(o.get("custom_fields"), dict) else None

    logistics_meta = None
    if isinstance(o.get("logistics_meta"), dict):
        lm = o["logistics_meta"]
        logistics_meta = LogisticsMeta(
            tracking_number=lm.get("tracking_number"),
            customer_order_no=lm.get("customer_order_no"),
            is_vip=bool(lm.get("is_vip")),
            packing_date=lm.get("packing_date"),
            coordinator=lm.get("coordinator"),
            packer=lm.get("packer"),
            invoice_no=lm.get("invoice_no"),
            email_notification=bool(lm.get("email_notification")),
        )

    sender = None
    if isinstance(o.get("sender"), dict):
        snd = o["sender"]
        s_line1 = (
            str(snd.get("line1") or snd.get("address") or "").strip()
            or str(snd.get("customer_address1") or "").strip()
        )
        s_city = str(snd.get("city") or snd.get("customer_city") or "").strip()
        s_zip = str(
            snd.get("postal_code")
            or snd.get("postalCode")
            or snd.get("zip")
            or snd.get("customer_zip_code")
            or ""
        ).strip()
        if s_line1 and s_city and s_zip:
            sender = IfsLogisticsAddress(
                company_name=snd.get("company_name") or snd.get("companyName"),
                contact_name=snd.get("contact_name") or snd.get("contactName"),
                line1=s_line1,
                line2=snd.get("line2") or snd.get("address2") or snd.get("customer_address2"),
                city=s_city,
                postal_code=s_zip,
                country_code=str(
                    snd.get("country_code")
                    or snd.get("countryCode")
                    or snd.get("customer_country")
                    or "PL"
                ),
                phone=snd.get("phone") or snd.get("customer_phone"),
                email=snd.get("email") or snd.get("customer_email"),
            )

    handling_units_summary = None
    if isinstance(o.get("handling_units_summary"), list):
        handling_units_summary = []
        for hu in o["handling_units_summary"]:
            if not isinstance(hu, dict):
                continue
            handling_units_summary.append(
                HandlingUnitSummary(
                    pack_type=str(hu.get("pack_type") or ""),
                    type="pallet" if hu.get("type") == "pallet" else "parcel",
                    qty=int(hu.get("qty") or 0),
                    weight_kg=hu.get("weight_kg") if isinstance(hu.get("weight_kg"), (int, float)) else None,
                    length_cm=float(hu.get("length_cm") or 0),
                    width_cm=float(hu.get("width_cm") or 0),
                    height_cm=float(hu.get("height_cm") or 0),
                )
            )

    return IfsLogisticsPayload(
        shipment_id=shipment_id,
        contract=o.get("contract"),
        order_no=o.get("order_no") or o.get("orderNo"),
        objstate=o.get("objstate"),
        total_weight_kg=o.get("total_weight_kg") or o.get("total_weight"),
        forward_agent_id=o.get("forward_agent_id"),
        dsv_pickup_location=(
            str(o["dsv_pickup_location"]).strip()
            if isinstance(o.get("dsv_pickup_location"), str) and o["dsv_pickup_location"].strip()
            else None
        ),
        note_text=o.get("note_text"),
        custom_fields=custom_fields,
        logistics_meta=logistics_meta,
        handling_units_summary=handling_units_summary,
        destination=destination,
        sender=sender,
        lines=lines,
    )
