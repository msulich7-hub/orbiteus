"""DPD Poland carrier client — REST booking + SOAP labels."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from modules.shipping.lib.adapters.dpd.config import DpdCarrierConfig, DpdPayerType, resolve_dpd_config_from_env
from modules.shipping.lib.adapters.dpd.soap_labels import SessionType, fetch_sped_labels_pdf_base64
from modules.shipping.lib.adapters.errors import CarrierIntegrationError
from modules.shipping.lib.shipment_types import ShipmentAddressParty, ShipmentRequest


def dpd_nullable_contact(value: str | None) -> str | None:
    if value is None:
        return None
    t = str(value).strip()
    return t if t else None


def _strip_postal(zip_code: str) -> str:
    return zip_code.replace("-", "").replace(" ", "")


def _party_to_dpd_address(
    party: ShipmentAddressParty,
    *,
    fid: int | None = None,
) -> dict[str, Any]:
    company = party.company_name or ""
    if party.first_name and party.last_name:
        name = f"{party.first_name} {party.last_name}".strip()
    elif party.company_name:
        name = ""
    else:
        name = ""

    addr: dict[str, Any] = {
        "company": company,
        "name": name,
        "address": party.address,
        "city": party.city,
        "postalCode": _strip_postal(party.zip),
        "countryCode": party.country or "PL",
    }
    email = dpd_nullable_contact(party.email)
    phone = dpd_nullable_contact(party.phone)
    if email is not None:
        addr["email"] = email
    if phone is not None:
        addr["phone"] = phone
    if fid is not None:
        addr["fid"] = fid
    return addr


def build_generate_packages_body(req: ShipmentRequest, config: DpdCarrierConfig) -> dict[str, Any]:
    """Build REST generatePackagesNumbers JSON — exported for unit tests."""
    sender_cfg = config.sender
    o = req.sender

    if o:
        sender_addr = _party_to_dpd_address(o, fid=config.credentials.fid)
        if not sender_addr.get("company"):
            sender_addr["company"] = sender_cfg.company
        if not sender_addr.get("name"):
            sender_addr["name"] = sender_cfg.name
        if not sender_addr.get("address"):
            sender_addr["address"] = sender_cfg.address
        if not sender_addr.get("city"):
            sender_addr["city"] = sender_cfg.city
        if not sender_addr.get("postalCode"):
            sender_addr["postalCode"] = sender_cfg.postal_code
    else:
        sender_addr = {
            "company": sender_cfg.company,
            "name": sender_cfg.name,
            "address": sender_cfg.address,
            "city": sender_cfg.city,
            "postalCode": sender_cfg.postal_code,
            "countryCode": sender_cfg.country_code,
        }
        email = dpd_nullable_contact(sender_cfg.email)
        phone = dpd_nullable_contact(sender_cfg.phone)
        if email is not None:
            sender_addr["email"] = email
        if phone is not None:
            sender_addr["phone"] = phone
        sender_addr["fid"] = config.credentials.fid

    receiver_addr = _party_to_dpd_address(req.recipient)

    parcels: list[dict[str, Any]] = []
    for i, p in enumerate(req.parcels):
        content = (p.content or req.goods_description or "Czesci zamienne")[:300]
        parcel: dict[str, Any] = {
            "content": content,
            "weight": p.weight,
        }
        if p.length is not None:
            parcel["sizeX"] = round(p.length)
        if p.width is not None:
            parcel["sizeY"] = round(p.width)
        if p.height is not None:
            parcel["sizeZ"] = round(p.height)
        ref = p.reference or f"{req.order_no}/{i + 1}"
        parcel["customerData1"] = ref
        guid = req.options.get("parcelGuid")
        if isinstance(guid, str) and guid:
            parcel["reference"] = guid
        parcels.append(parcel)

    services = _build_services(req)
    payer_type: DpdPayerType = req.options.get("payerType") or config.default_payer_type  # type: ignore[assignment]
    if payer_type not in ("SENDER", "RECEIVER", "THIRD_PARTY"):
        payer_type = "SENDER"

    fid = config.credentials.fid
    pkg: dict[str, Any] = {
        "ref1": req.order_no,
        "sender": sender_addr,
        "receiver": receiver_addr,
        "parcels": parcels,
        "payerType": payer_type,
        "payerFID": fid,
    }
    ref2 = req.options.get("ref2")
    ref3 = req.options.get("ref3")
    if isinstance(ref2, str) and ref2:
        pkg["ref2"] = ref2
    if isinstance(ref3, str) and ref3:
        pkg["ref3"] = ref3
    if services:
        pkg["services"] = services
    if payer_type == "THIRD_PARTY":
        pkg["thirdPartyFID"] = fid

    return {
        "packages": [pkg],
        "generationPolicy": "ALL_OR_NOTHING",
        "langCode": "PL",
    }


def _build_services(req: ShipmentRequest) -> dict[str, Any]:
    svc: dict[str, Any] = {}
    opts = req.options or {}

    cod = opts.get("cod")
    if isinstance(cod, dict) and cod.get("amount"):
        svc["cod"] = {
            "amount": str(cod["amount"]),
            "currency": cod.get("currency") or "PLN",
        }

    declared = opts.get("declaredValue")
    if isinstance(declared, dict) and declared.get("amount"):
        svc["declaredValue"] = {
            "amount": str(declared["amount"]),
            "currency": declared.get("currency") or "PLN",
        }

    guarantee = opts.get("guarantee")
    if isinstance(guarantee, dict):
        svc["guarantee"] = guarantee

    self_col = opts.get("selfCol")
    if isinstance(self_col, dict):
        svc["selfCol"] = self_col

    dpd_pickup = opts.get("dpdPickup")
    if isinstance(dpd_pickup, str) and dpd_pickup:
        svc["dpdPickup"] = {"pudo": dpd_pickup}

    if opts.get("cud") is True:
        svc["cud"] = {}

    return svc


def _dpd_package_id(pkg: dict[str, Any]) -> int | str | None:
    for key in ("packageId", "package_Id", "packageID", "id", "Id"):
        if key in pkg and pkg[key] is not None:
            return pkg[key]
    return None


class DpdCarrier:
    def __init__(self, config: DpdCarrierConfig | None = None) -> None:
        self.config = config or resolve_dpd_config_from_env()

    async def request_shipment(self, req: ShipmentRequest) -> dict[str, Any]:
        body = build_generate_packages_body(req, self.config)
        gen_resp = await self._post("shipment/v1/generatePackagesNumbers", body)

        if os.environ.get("DPD_DEBUG"):
            import sys

            print("[DPD DEBUG] generatePackagesNumbers:", json.dumps(gen_resp, indent=2), file=sys.stderr)

        if gen_resp.get("status") != "OK":
            err_parts: list[str] = []
            for e in gen_resp.get("errorDetails") or []:
                if isinstance(e, dict):
                    err_parts.append(f"{e.get('code')}: {e.get('info')}")
            packages = gen_resp.get("packages") or []
            if packages and isinstance(packages[0], dict):
                for f in packages[0].get("invalidFields") or []:
                    if isinstance(f, dict):
                        err_parts.append(f"{f.get('fieldName')}: {f.get('info')}")
            raise CarrierIntegrationError(
                "DPD",
                f"generatePackagesNumbers failed: {'; '.join(err_parts) or 'Unknown error'}",
            )

        pkg = (gen_resp.get("packages") or [None])[0]
        if not pkg or not isinstance(pkg, dict) or pkg.get("status") != "OK":
            invalid = []
            if isinstance(pkg, dict):
                for f in pkg.get("invalidFields") or []:
                    if isinstance(f, dict):
                        invalid.append(f"{f.get('fieldName')}: {f.get('info')}")
            raise CarrierIntegrationError(
                "DPD",
                f"Package booking error: {'; '.join(invalid) or pkg.get('status') if isinstance(pkg, dict) else 'missing'}",
            )

        parcel_rows = pkg.get("parcels") or []
        waybills = [
            str(p["waybill"])
            for p in parcel_rows
            if isinstance(p, dict) and p.get("waybill")
        ]
        if not waybills:
            raise CarrierIntegrationError("DPD", "No waybill in response")

        first_waybill = waybills[0]
        session_type: SessionType = (
            "DOMESTIC" if (req.recipient.country or "PL").upper() == "PL" else "INTERNATIONAL"
        )

        label_b64: str | None = None
        try:
            label_b64 = await fetch_sped_labels_pdf_base64(
                waybills,
                session_type,
                self.config.credentials,
                self.config.soap_package_url,
                self.config.label_format,
            )
        except CarrierIntegrationError:
            raise
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("DPD SOAP label warning: %s", exc)

        ship_id = _dpd_package_id(pkg) or gen_resp.get("sessionId") or first_waybill
        mime = "application/pdf" if self.config.label_format == "PDF" else "application/octet-stream"
        label_url = (
            f"data:{mime};base64,{label_b64}"
            if label_b64
            else f"https://tracktrace.dpd.com.pl/parcelDetails?typ1=1&p1={first_waybill}"
        )

        return {
            "tracking_number": first_waybill,
            "label_url": label_url,
            "label_base64": label_b64,
            "shipment_id": str(ship_id),
            "carrier_code": "DPD",
            "raw": {
                "packageId": _dpd_package_id(pkg),
                "sessionId": gen_resp.get("sessionId"),
                "waybills": waybills,
                "allParcels": parcel_rows,
            },
        }

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        creds = self.config.credentials
        basic = base64.b64encode(f"{creds.login}:{creds.password}".encode()).decode()

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {basic}",
                    "X-DPD-FID": str(creds.master_fid),
                },
            )
        text = res.text
        if not res.is_success:
            detail = text.strip() or f"(empty body, content-type: {res.headers.get('content-type')})"
            try:
                detail = json.dumps(json.loads(text))
            except json.JSONDecodeError:
                detail = text[:800]
            raise CarrierIntegrationError(
                "DPD",
                f"REST error ({res.status_code} {res.reason_phrase}): {detail}",
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CarrierIntegrationError("DPD", f"Response is not valid JSON: {text[:300]}") from exc
        if not isinstance(parsed, dict):
            raise CarrierIntegrationError("DPD", "Response JSON is not an object")
        return parsed
