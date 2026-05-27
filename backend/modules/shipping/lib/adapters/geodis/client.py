"""Geodis PUGO SOAP client — port of mercato-shipping-hub geodis-carrier.ts."""

from __future__ import annotations

import asyncio
import base64
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx

from modules.shipping.lib.adapters.errors import CarrierIntegrationError
from modules.shipping.lib.adapters.geodis.pickup_date import next_geodis_suggested_pickup_date
from modules.shipping.lib.adapters.geodis.types import (
    GEODIS_PALLET_DEFINITIONS,
    GeodisCredentials,
    GeodisParcel,
    GeodisSenderConfig,
    resolve_geodis_package_symbol,
)
from modules.shipping.lib.shipment_types import ShipmentAddressParty, ShipmentRequest

DEFAULT_ENDPOINT = "http://ugo.pekaes.com.pl/ugogate_001.asmx"
DEFAULT_SOAP_NS = "http://ugo.pekaes.com.pl/ugogate_001"
WAYBILL_RE = re.compile(r"^PL\d{10,20}$", re.I)


@dataclass
class GeodisCarrierConfig:
    endpoint: str
    soap_namespace: str
    credentials: GeodisCredentials
    sender: GeodisSenderConfig
    default_srv_code: str = "ST"
    delivery_hour_from: str = "08:00"
    delivery_hour_to: str = "16:00"
    label_max_retries: int = 5
    label_retry_delay_ms: int = 3000
    skip_label_download: bool = False


def resolve_geodis_config_from_env() -> GeodisCarrierConfig:
    import os

    shipper_id = (os.environ.get("GEODIS_SHIPPER_ID") or "").strip()
    password = (os.environ.get("GEODIS_PASSWORD") or "").strip()
    if not shipper_id or not password:
        raise RuntimeError("Set GEODIS_SHIPPER_ID and GEODIS_PASSWORD environment variables.")

    def _truthy(v: str | None) -> bool:
        return (v or "").lower() in ("1", "true", "yes")

    return GeodisCarrierConfig(
        endpoint=os.environ.get("GEODIS_ENDPOINT") or DEFAULT_ENDPOINT,
        soap_namespace=os.environ.get("GEODIS_SOAP_NS") or DEFAULT_SOAP_NS,
        credentials=GeodisCredentials(shipper_id=int(shipper_id), password=password),
        sender=GeodisSenderConfig(
            symbol=os.environ.get("GEODIS_SENDER_SYMBOL") or "PL244538",
            name=os.environ.get("GEODIS_SENDER_NAME") or "MDM NT SP. Z O.O.",
            person=os.environ.get("GEODIS_SENDER_PERSON") or "Dział Wysyłek",
            phone=os.environ.get("GEODIS_SENDER_PHONE") or "500000000",
            country=os.environ.get("GEODIS_SENDER_COUNTRY") or "PL",
            city=os.environ.get("GEODIS_SENDER_CITY") or "BIELSKO BIALA",
            street_full=os.environ.get("GEODIS_SENDER_STREET") or "BESTWINSKA 143",
            zip_code=os.environ.get("GEODIS_SENDER_ZIP") or "43-346",
        ),
        default_srv_code=os.environ.get("GEODIS_SRV_CODE") or "ST",
        delivery_hour_from=os.environ.get("GEODIS_DELIVERY_HOUR_FROM") or "08:00",
        delivery_hour_to=os.environ.get("GEODIS_DELIVERY_HOUR_TO") or "16:00",
        label_max_retries=int(os.environ.get("GEODIS_LABEL_MAX_RETRIES") or "5"),
        label_retry_delay_ms=int(os.environ.get("GEODIS_LABEL_RETRY_DELAY_MS") or "3000"),
        skip_label_download=_truthy(os.environ.get("GEODIS_TEST_SKIP_LABEL")),
    )


def _esc(val: str | None) -> str:
    if not val:
        return ""
    return (
        val.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _dig(obj: ET.Element | None, *local_names: str) -> ET.Element | None:
    cur = obj
    for name in local_names:
        if cur is None:
            return None
        found = None
        for child in cur:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == name:
                found = child
                break
        cur = found
    return cur


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


class GeodisCarrier:
    code = "GEODIS"

    def __init__(self, config: GeodisCarrierConfig | None = None) -> None:
        self.config = config or resolve_geodis_config_from_env()

    async def request_shipment(self, req: ShipmentRequest) -> dict[str, Any]:
        shipment_xml = self._build_shipment_xml(req)
        waybill = await self._add_shipment(shipment_xml, req.order_no)

        label_url = ""
        label_b64: str | None = None
        if self.config.skip_label_download:
            label_url = f"geodis://label-skipped/{waybill}"
        else:
            try:
                label_b64 = await self.download_label(waybill)
                label_url = f"data:application/pdf;base64,{label_b64}"
            except Exception as exc:  # noqa: BLE001
                label_url = f"geodis://label-pending/{waybill}"
                return {
                    "tracking_number": waybill,
                    "label_url": label_url,
                    "shipment_id": waybill,
                    "carrier_code": self.code,
                    "label_warning": str(exc),
                    "raw": {"waybill": waybill},
                }

        return {
            "tracking_number": waybill,
            "label_url": label_url,
            "shipment_id": waybill,
            "carrier_code": self.code,
            "label_base64": label_b64,
            "raw": {"waybill": waybill},
        }

    async def download_label(self, waybill: str) -> str:
        server_file = await self._request_label_generation(waybill)
        return await self._fetch_printout(server_file)

    async def _add_shipment(self, shipment_data_xml: str, reference: str) -> str:
        body = f"""
      <ShipperId>{self.config.credentials.shipper_id}</ShipperId>
      <Password>{_esc(self.config.credentials.password)}</Password>
      <ShipmentDataXML><![CDATA[{shipment_data_xml}]]></ShipmentDataXML>
    """
        response_xml = await self._call_soap("AddShipment", body)
        root = ET.fromstring(response_xml)
        body_el = _dig(root, "Body")
        result_el = _dig(body_el, "AddShipmentResponse", "AddShipmentResult")
        if result_el is None:
            raise CarrierIntegrationError("GEODIS", f"AddShipment: unexpected response for {reference}")

        code = int(_text(_dig(result_el, "Result")) or "-1")
        details = _text(_dig(result_el, "ResultDetails1"))

        if "<result>false</result>" in details.lower() or "<errors>" in details.lower():
            err_match = re.search(r"<error>([^<]*)</error>", details, re.I)
            raise CarrierIntegrationError(
                "GEODIS",
                (err_match.group(1).strip() if err_match else details[:400]),
            )

        if code == 0:
            w = details.strip()
            if WAYBILL_RE.match(w):
                return w
            raise CarrierIntegrationError("GEODIS", f"AddShipment: expected waybill, got {w[:200]}")

        if code == 1:
            match = re.search(r"<number>(.*?)</number>", details, re.I)
            if match and WAYBILL_RE.match(match.group(1).strip()):
                return match.group(1).strip()

        raise CarrierIntegrationError("GEODIS", f"AddShipment error (code={code}): {details[:300]}")

    async def _request_label_generation(self, waybill: str) -> str:
        for attempt in range(self.config.label_max_retries):
            body = f"""
        <ShipperId>{self.config.credentials.shipper_id}</ShipperId>
        <Password>{_esc(self.config.credentials.password)}</Password>
        <ShipmentNo>{_esc(waybill)}</ShipmentNo>
      """
            response_xml = await self._call_soap("PrintShipmentLabels", body)
            root = ET.fromstring(response_xml)
            body_el = _dig(root, "Body")
            result_el = _dig(body_el, "PrintShipmentLabelsResponse", "PrintShipmentLabelsResult")
            code = int(_text(_dig(result_el, "Result")) or "-1")
            if code < 0:
                details = _text(_dig(result_el, "ResultDetails1"))
                raise CarrierIntegrationError("GEODIS", f"PrintShipmentLabels error (code={code}): {details[:300]}")

            details = _text(_dig(result_el, "ResultDetails1"))
            file_match = re.search(r"<filename>(.*?\.pdf)</filename>", details, re.I)
            if file_match:
                return file_match.group(1).strip()

            if attempt < self.config.label_max_retries - 1:
                await asyncio.sleep(self.config.label_retry_delay_ms / 1000.0)

        raise CarrierIntegrationError(
            "GEODIS",
            f"Label not ready after {self.config.label_max_retries} retries for {waybill}",
        )

    async def _fetch_printout(self, server_file_name: str) -> str:
        body = f"""
      <ShipperId>{self.config.credentials.shipper_id}</ShipperId>
      <Password>{_esc(self.config.credentials.password)}</Password>
      <FileName>{_esc(server_file_name)}</FileName>
    """
        response_xml = await self._call_soap("GetPrintout", body)
        root = ET.fromstring(response_xml)
        body_el = _dig(root, "Body")
        result_el = _dig(body_el, "GetPrintoutResponse", "GetPrintoutResult")
        code = int(_text(_dig(result_el, "Result")) or "-1")
        file_content = _text(_dig(result_el, "FileContent"))
        if code >= 0 and file_content:
            base64.b64decode(file_content, validate=True)
            return file_content
        details = _text(_dig(result_el, "ResultDetails1"))
        raise CarrierIntegrationError("GEODIS", f"GetPrintout failed (code={code}): {details[:300]}")

    async def _call_soap(self, operation: str, body_content: str) -> str:
        ns = self.config.soap_namespace
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Body>
    <{operation} xmlns="{_esc(ns)}">
      {body_content}
    </{operation}>
  </soap:Body>
</soap:Envelope>"""
        soap_action = f'"{ns}/{operation}"'
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                self.config.endpoint,
                content=envelope.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": soap_action,
                },
            )
        text = res.text
        if not res.is_success:
            raise CarrierIntegrationError("GEODIS", f"SOAP error ({res.status_code}): {text[:500]}")
        return text

    def _resolve_sender(self, req: ShipmentRequest) -> GeodisSenderConfig:
        base = self.config.sender
        o = req.sender
        if not o:
            return base
        full_name = " ".join(x for x in (o.first_name, o.last_name) if x).strip()
        street = ", ".join(x for x in (o.address, o.address2) if x).strip()
        return GeodisSenderConfig(
            symbol=base.symbol,
            name=(o.company_name or base.name).strip() or base.name,
            person=full_name or base.person,
            phone=o.phone or base.phone,
            country=o.country or base.country,
            city=(o.city or base.city).upper(),
            street_full=street or base.street_full,
            zip_code=o.zip or base.zip_code,
        )

    def _build_parcels(self, req: ShipmentRequest) -> list[GeodisParcel]:
        out: list[GeodisParcel] = []
        for p in req.parcels:
            raw_type = p.pack_type or p.reference or "EUR"
            pallet_type = resolve_geodis_package_symbol(raw_type)
            defn = GEODIS_PALLET_DEFINITIONS.get(pallet_type, {})
            name = str(defn.get("name") or f"Paczka {pallet_type}")
            qty = 1
            length_m = (p.length / 100.0) if p.length is not None else float(defn.get("length") or 1.2)
            width_m = (p.width / 100.0) if p.width is not None else float(defn.get("width") or 0.8)
            height_m = (p.height / 100.0) if p.height is not None else float(defn.get("height") or 1.0)
            volume = length_m * width_m * height_m * qty
            if volume <= 0:
                volume = 0.001
            mp_single = float(defn.get("pallet_places") or (length_m * width_m) / 0.96)
            if mp_single <= 0:
                mp_single = 0.01
            mp = mp_single * qty
            if pallet_type == "PAL.INNA":
                mp = max(mp, 1.0)
            out.append(
                GeodisParcel(
                    package_symbol=pallet_type,
                    name=name,
                    amount=qty,
                    weight_total=p.weight * qty,
                    volume_total=volume,
                    pal_places_total=mp,
                    length=length_m,
                    width=width_m,
                    height=height_m,
                )
            )
        return out

    def _build_shipment_xml(self, req: ShipmentRequest) -> str:
        s = self._resolve_sender(req)
        r = req.recipient
        parcels = self._build_parcels(req)
        total_weight = sum(p.weight_total for p in parcels)
        total_volume = sum(p.volume_total for p in parcels)
        total_mp = sum(p.pal_places_total for p in parcels)
        total_qty = sum(p.amount for p in parcels)

        opts = req.options or {}
        services = list(opts.get("services") or [])
        stackable = bool(opts.get("stackable") or False)
        srv_code = str(opts.get("srv_code") or self.config.default_srv_code)
        pickup_date = str(opts.get("pickup_date") or next_geodis_suggested_pickup_date())
        pickup_hour_from = str(opts.get("pickup_hour_from") or "08:00")
        pickup_hour_to = str(opts.get("pickup_hour_to") or "16:00")

        receiver_name = r.company_name or (
            f"{r.first_name or ''} {r.last_name or ''}".strip() or "Odbiorca"
        )
        street_no = r.address2 or " "

        parcel_xml = "\n".join(
            f"""      <Parcel>
        <PackageSymbol>{_esc(p.package_symbol)}</PackageSymbol>
        <Name>{_esc(p.name)}</Name>
        <Amount>{p.amount}</Amount>
        <Dimension>
          <Width>{p.width:.2f}</Width>
          <Height>{p.height:.2f}</Height>
          <Length>{p.length:.2f}</Length>
        </Dimension>
        <WeightTotal>{p.weight_total:.2f}</WeightTotal>
        <VolumeTotal>{p.volume_total:.3f}</VolumeTotal>
        <PalPlacesTotal>{p.pal_places_total:.2f}</PalPlacesTotal>
        <ReturnAmount>0</ReturnAmount>
      </Parcel>"""
            for p in parcels
        )

        services_xml = ""
        if services:
            services_xml = "<Services>\n" + "\n".join(
                f"      <Service><Symbol>{_esc(str(svc))}</Symbol></Service>" for svc in services
            ) + "\n    </Services>"

        return f"""<PUGOShipments>
  <Shipment>
    <Category>2</Category>
    <Shipper>
      <Contact>
        <Person>{_esc(s.person)}</Person>
        <Phone>{_esc(s.phone)}</Phone>
      </Contact>
      <Symbol>{_esc(s.symbol)}</Symbol>
      <Name>{_esc(s.name)}</Name>
      <Address>
        <Country>{_esc(s.country)}</Country>
        <City>{_esc(s.city)}</City>
        <Street>{_esc(s.street_full)}</Street>
        <ZipCode>{_esc(s.zip_code)}</ZipCode>
      </Address>
    </Shipper>
    <PayerType>sender</PayerType>
    <References>
      <Reference>
        <Number>{_esc(req.order_no)}</Number>
      </Reference>
    </References>
    <Pickup>
      <SuggestedDate>{_esc(pickup_date)}</SuggestedDate>
      <HourFrom>{_esc(pickup_hour_from)}</HourFrom>
      <HourTo>{_esc(pickup_hour_to)}</HourTo>
      <Terminal>false</Terminal>
    </Pickup>
    <Delivery>
      <HourFrom>{_esc(self.config.delivery_hour_from)}</HourFrom>
      <HourTo>{_esc(self.config.delivery_hour_to)}</HourTo>
      <Consignee>
        <Symbol>{_esc(receiver_name)}</Symbol>
        <Name>{_esc(receiver_name)}</Name>
        <Address>
          <Country>{_esc(r.country)}</Country>
          <City>{_esc(r.city)}</City>
          <Street>{_esc(r.address)}</Street>
          <StreetNo>{_esc(street_no)}</StreetNo>
          <ZipCode>{_esc(r.zip)}</ZipCode>
        </Address>
        <Contact>
          <Phone>{_esc(r.phone or '999999999')}</Phone>
        </Contact>
      </Consignee>
      <Terminal>false</Terminal>
    </Delivery>
    <Parcels>
{parcel_xml}
    </Parcels>
{("    " + services_xml) if services_xml else ""}
    <Stackable>{str(stackable).lower()}</Stackable>
    <SrvCode>{_esc(srv_code)}</SrvCode>
    <Totals>
      <Weight>{total_weight:.2f}</Weight>
      <PalPlaces>{total_mp:.2f}</PalPlaces>
      <Volume>{total_volume:.3f}</Volume>
      <Amount>{total_qty}</Amount>
      <ReturnAmount>0</ReturnAmount>
    </Totals>
    <Options>
      <PrintShipperDataOnPostalReceipt>pickupAddress</PrintShipperDataOnPostalReceipt>
      <ExtRetPacks>false</ExtRetPacks>
    </Options>
    <InsuranceDetails>
      <Currency>PLN</Currency>
    </InsuranceDetails>
  </Shipment>
</PUGOShipments>"""
