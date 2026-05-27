"""DSV / DB Schenker Connect SOAP client — port of dsv-carrier.ts."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from modules.shipping.lib.adapters.dsv.config import DsvCarrierConfig, resolve_dsv_config_from_env
from modules.shipping.lib.adapters.dsv.locations import get_payer_shipper_profile, resolve_pickup_location
from modules.shipping.lib.adapters.dsv.pickup_date import next_dsv_pickup_window
from modules.shipping.lib.adapters.dsv.types import (
    DsvAddress,
    DsvApplicationArea,
    DsvBarcodeReference,
    DsvBarcodeRequest,
    DsvBookingLandRequest,
    DsvBookingResponse,
    DsvPickupDates,
    DsvReference,
    DsvShipmentPosition,
    DsvShippingInformation,
)
from modules.shipping.lib.adapters.errors import CarrierIntegrationError
from modules.shipping.lib.shipment_types import ShipmentRequest

DSV_DEFAULT_BARCODE_REQUEST = DsvBarcodeRequest(format="A6", start_pos=1, separated=True)
DSV_DEFAULT_CARGO_DESCRIPTION = "AKCESORIA DACHOWE"

EU_DESTINATION = frozenset(
    {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HU",
        "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    }
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


def _read_options_boolean(raw: Any) -> bool | None:
    if raw in ("auto", "", None):
        return None
    if isinstance(raw, bool):
        return raw
    if raw in ("true", 1, "1"):
        return True
    if raw in ("false", 0, "0"):
        return False
    return None


def _pickup_address_differs_from_shipper(pickup: DsvAddress, shipper: DsvAddress) -> bool:
    return (
        pickup.schenker_address_id != shipper.schenker_address_id
        or pickup.postal_code != shipper.postal_code
        or pickup.street != shipper.street
        or pickup.city != shipper.city
        or pickup.name1 != shipper.name1
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

def build_address_xml(a: DsvAddress) -> str:
    cp = ""
    if a.contact_person:
        cp = f"""<contactPerson>
        {f"<name>{_esc(a.contact_person.name)}</name>" if a.contact_person.name else ""}
        {f"<phone>{_esc(a.contact_person.phone)}</phone>" if a.contact_person.phone else ""}
        {f"<email>{_esc(a.contact_person.email)}</email>" if a.contact_person.email else ""}
       </contactPerson>"""
    return f"""<address>
    {cp}
    <name1>{_esc(a.name1)}</name1>
    {f"<name2>{_esc(a.name2)}</name2>" if a.name2 else ""}
    {f"<vatNo>{_esc(a.vat_no)}</vatNo>" if a.vat_no else ""}
    {f"<email>{_esc(a.email)}</email>" if a.email else ""}
    <locationType>{a.location_type}</locationType>
    {f"<mobilePhone>{_esc(a.mobile_phone)}</mobilePhone>" if a.mobile_phone else ""}
    <personType>{a.person_type}</personType>
    {f"<phone>{_esc(a.phone)}</phone>" if a.phone else ""}
    <postalCode>{_esc(a.postal_code)}</postalCode>
    {f"<schenkerAddressId>{_esc(a.schenker_address_id)}</schenkerAddressId>" if a.schenker_address_id else ""}
    <street>{_esc(a.street)}</street>
    <city>{_esc(a.city)}</city>
    <countryCode>{_esc(a.country_code)}</countryCode>
    <type>{a.type}</type>
  </address>"""


def build_shipment_position_xml(sp: DsvShipmentPosition) -> str:
    return f"""<shipmentPosition>
    <dgr>{str(sp.dgr).lower()}</dgr>
    <cargoDesc>{_esc(sp.cargo_desc)}</cargoDesc>
    {f"<length>{sp.length}</length>" if sp.length else ""}
    {f"<width>{sp.width}</width>" if sp.width else ""}
    {f"<height>{sp.height}</height>" if sp.height else ""}
    <volume>{sp.volume}</volume>
    <grossWeight>{sp.gross_weight}</grossWeight>
    <packageType>{_esc(sp.package_type)}</packageType>
    <pieces>{sp.pieces}</pieces>
    <stackable>{str(sp.stackable).lower()}</stackable>
  </shipmentPosition>"""


def build_soap_envelope(b: DsvBookingLandRequest) -> str:
    app = b.application_area
    app_area = f"""
    <applicationArea>
      <accessKey>{_esc(app.access_key)}</accessKey>
      {f"<groupId>{app.group_id}</groupId>" if app.group_id is not None else ""}
      {f"<requestID>{_esc(app.request_id)}</requestID>" if app.request_id else ""}
      {f"<userId>{_esc(app.user_id)}</userId>" if app.user_id else ""}
    </applicationArea>"""

    barcode_req = ""
    if b.barcode_request:
        br = b.barcode_request
        barcode_req = (
            f'<barcodeRequest start_pos="{br.start_pos}" separated="{str(br.separated).lower()}" '
            f'directThermalMedia="{str(br.direct_thermal_media).lower()}">{br.format}</barcodeRequest>'
        )

    addresses = "\n".join(build_address_xml(a) for a in b.addresses)
    refs = "\n".join(
        f"<reference><number>{_esc(r.number)}</number><id>{_esc(r.id)}</id></reference>"
        for r in (b.references or [])
    )
    positions = "\n".join(build_shipment_position_xml(sp) for sp in b.shipping_information.shipment_positions)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://www.schenker.com/Booking/v1_1">
  <soapenv:Header/>
  <soapenv:Body>
    <v1:getBookingRequestLand>
      <in>
        {app_area}
        <bookingLand submitBooking="{str(b.submit_booking).lower()}" returnBarcodeReferences="{str(b.return_barcode_references).lower()}">
          {barcode_req}
          {addresses}
          <incoterm>{_esc(b.incoterm)}</incoterm>
          <incotermLocation>{_esc(b.incoterm_location)}</incotermLocation>
          <productCode>{_esc(b.product_code)}</productCode>
          <measurementType>{b.measurement_type}</measurementType>
          {f"<cargoDescription>{_esc(b.cargo_description)}</cargoDescription>" if b.cargo_description else ""}
          <customsClearance>{str(b.customs_clearance).lower()}</customsClearance>
          <grossWeight>{_esc(b.gross_weight)}</grossWeight>
          <indoorDelivery>{str(b.indoor_delivery).lower()}</indoorDelivery>
          <pickupDates>
            <pickUpDateFrom>{b.pickup_dates.pick_up_date_from}</pickUpDateFrom>
            <pickUpDateTo>{b.pickup_dates.pick_up_date_to}</pickUpDateTo>
          </pickupDates>
          {refs}
          {f"<handlingInstructions>{_esc(b.handling_instructions)}</handlingInstructions>" if b.handling_instructions else ""}
          <neutralShipping>{str(b.neutral_shipping).lower()}</neutralShipping>
          <specialCargo>{str(b.special_cargo).lower()}</specialCargo>
          <serviceType>{b.service_type}</serviceType>
          <shippingInformation>
            {positions}
            {f"<grossWeight>{b.shipping_information.gross_weight}</grossWeight>" if b.shipping_information.gross_weight else ""}
            <volume>{b.shipping_information.volume}</volume>
          </shippingInformation>
          <express>{str(b.express).lower()}</express>
          <foodRelated>{str(b.food_related).lower()}</foodRelated>
          <heatedTransport>{str(b.heated_transport).lower()}</heatedTransport>
          <homeDelivery>{str(b.home_delivery).lower()}</homeDelivery>
          <measureUnit>{b.measure_unit}</measureUnit>
          {f"<measureUnitVolume>{b.measure_unit_volume}</measureUnitVolume>" if b.measure_unit_volume else ""}
          <ownPickup>{str(b.own_pickup).lower()}</ownPickup>
          <pharmaceuticals>false</pharmaceuticals>
        </bookingLand>
      </in>
    </v1:getBookingRequestLand>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_barcode_request_envelope(
    creds_access_key: str,
    creds_group_id: int | None,
    booking_id: str,
    barcode: DsvBarcodeRequest,
) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://www.schenker.com/Booking/v1_1">
  <soapenv:Header/>
  <soapenv:Body>
    <v1:getBookingBarcodeRequest>
      <in>
        <applicationArea>
          <accessKey>{_esc(creds_access_key)}</accessKey>
          {f"<groupId>{creds_group_id}</groupId>" if creds_group_id is not None else ""}
        </applicationArea>
        <bookingId>{_esc(booking_id)}</bookingId>
        <barcodeRequest start_pos="{barcode.start_pos}" separated="{str(barcode.separated).lower()}" directThermalMedia="{str(barcode.direct_thermal_media).lower()}">{barcode.format}</barcodeRequest>
      </in>
    </v1:getBookingBarcodeRequest>
  </soapenv:Body>
</soapenv:Envelope>"""


def extract_schenker_error_detail(xml: str) -> tuple[str, str] | None:
    code_match = re.search(r"<code>\s*([^<]+?)\s*</code>", xml, re.I)
    message_match = re.search(r"<message>\s*([^<]+?)\s*</message>", xml, re.I)
    if not code_match and not message_match:
        return None
    return (code_match.group(1) if code_match else "", message_match.group(1) if message_match else "")


class DsvCarrier:
    code = "DSV"

    def __init__(self, config: DsvCarrierConfig | None = None) -> None:
        self.config = config or resolve_dsv_config_from_env()

    async def request_shipment(self, req: ShipmentRequest) -> dict[str, Any]:
        booking = self._build_land_booking(req)
        soap_xml = build_soap_envelope(booking)
        request_id = booking.application_area.request_id or f"OM-{req.order_no}"
        pack_types = ",".join(p.pack_type or "EP" for p in req.parcels)
        total_kg = sum(p.weight for p in req.parcels)

        try:
            response_xml = await self._call_soap(soap_xml, request_id)
        except Exception as exc:
            raise CarrierIntegrationError(
                "DSV",
                f"requestShipment FAILED orderNo={req.order_no} requestId={request_id} "
                f"packTypes={pack_types}: {exc}",
            ) from exc

        parsed = self._parse_response(
            response_xml,
            order_no=req.order_no,
            request_id=request_id,
            pack_types=pack_types,
        )

        first_barcode = parsed.barcode_references[0].barcode if parsed.barcode_references else None
        label_b64 = parsed.barcode_document
        label_url = (
            f"data:application/pdf;base64,{label_b64}"
            if label_b64
            else f"{self.config.endpoint}?bookingId={parsed.booking_id}"
        )

        if not label_b64:
            try:
                label_b64 = await self.request_barcode(parsed.booking_id)
                label_url = f"data:application/pdf;base64,{label_b64}"
            except Exception:
                pass

        return {
            "tracking_number": first_barcode or parsed.booking_id,
            "label_url": label_url,
            "shipment_id": parsed.booking_id,
            "carrier_code": self.code,
            "label_base64": label_b64,
            "raw": {
                "bookingId": parsed.booking_id,
                "barcodeReferences": [
                    {"barcode": r.barcode, "barcodeType": r.barcode_type}
                    for r in (parsed.barcode_references or [])
                ],
                "requestId": request_id,
                "totalKg": f"{total_kg:.2f}",
                "packTypes": pack_types,
            },
        }

    async def request_barcode(
        self,
        booking_id: str,
        fmt: str = "A6",
    ) -> str:
        barcode = (
            DsvBarcodeRequest(format="A4", start_pos=1, separated=False)
            if fmt == "A4"
            else DsvBarcodeRequest(format=fmt, start_pos=1, separated=True)  # type: ignore[arg-type]
        )
        xml = build_barcode_request_envelope(
            self.config.credentials.access_key,
            self.config.credentials.group_id,
            booking_id,
            barcode,
        )
        response_xml = await self._call_soap(xml)
        root = ET.fromstring(response_xml)
        body = _dig(root, "Body")
        resp = _dig(body, "getBookingBarcodeResponse", "out") or _dig(body, "getBookingBarcodeResponse")
        doc = _text(_dig(resp, "document"))
        if not doc:
            raise CarrierIntegrationError("DSV", "Barcode response missing document (label PDF).")
        return doc

    def _build_land_booking(self, req: ShipmentRequest) -> DsvBookingLandRequest:
        location_key = (req.options or {}).get("pickupLocation") or self.config.default_pickup_location
        loc = resolve_pickup_location(str(location_key))
        payer = get_payer_shipper_profile()

        pickup_start, pickup_end = next_dsv_pickup_window()

        shipper_address = DsvAddress(
            type="SHIPPER",
            name1=payer.sender_name,
            street=payer.sender_street,
            postal_code=payer.sender_zip,
            city=payer.sender_city,
            country_code=self.config.sender_country_code,
            person_type="COMPANY",
            location_type="PHYSICAL",
            schenker_address_id=payer.shipper_address_id,
            vat_no=self.config.vat_no,
            phone=self.config.sender_phone,
            email=self.config.sender_email,
        )

        pickup_address = DsvAddress(
            type="PICKUP",
            name1=loc.sender_name,
            street=loc.sender_street,
            postal_code=loc.sender_zip,
            city=loc.sender_city,
            country_code=self.config.sender_country_code,
            person_type="COMPANY",
            location_type="PHYSICAL",
            schenker_address_id=loc.pickup_address_id,
        )

        if req.sender:
            s = req.sender
            name1 = (
                (s.company_name or "").strip()
                or f"{s.first_name or ''} {s.last_name or ''}".strip()
                or loc.sender_name
            )
            pickup_address = DsvAddress(
                type="PICKUP",
                name1=name1,
                street=s.address,
                postal_code=s.zip,
                city=s.city,
                country_code=s.country or pickup_address.country_code,
                person_type="COMPANY",
                location_type="PHYSICAL",
                schenker_address_id=loc.pickup_address_id,
                phone=s.phone,
                email=s.email,
            )

        recipient = req.recipient
        consignee_name = (
            recipient.company_name
            or f"{recipient.first_name or ''} {recipient.last_name or ''}".strip()
        )
        consignee_address = DsvAddress(
            type="CONSIGNEE",
            name1=consignee_name,
            street=recipient.address,
            postal_code=recipient.zip,
            city=recipient.city,
            country_code=recipient.country,
            person_type="COMPANY" if recipient.company_name else "PRIVATE",
            location_type="PHYSICAL",
            phone=recipient.phone,
            email=recipient.email,
        )

        dest_country = (recipient.country or "PL").upper()
        sender_country = (self.config.sender_country_code or "PL").upper()
        cross_border = dest_country != sender_country
        intl_flag = _read_options_boolean((req.options or {}).get("dsvInternational"))
        use_international = intl_flag is True or (intl_flag is not False and cross_border)

        addresses = [shipper_address, consignee_address]
        if not use_international or _pickup_address_differs_from_shipper(pickup_address, shipper_address):
            addresses.append(pickup_address)

        cargo_override = str((req.options or {}).get("dsvCargoDescription") or "").strip()
        cargo_top = cargo_override or DSV_DEFAULT_CARGO_DESCRIPTION
        goods_trimmed = (req.goods_description or "").strip()

        positions: list[DsvShipmentPosition] = []
        for p in req.parcels:
            length = p.length or 100
            width = p.width or 80
            height = p.height or 60
            parcel_trimmed = (p.content or "").strip()
            vol = (length * width * height) / 1_000_000
            positions.append(
                DsvShipmentPosition(
                    cargo_desc=parcel_trimmed or goods_trimmed or cargo_top,
                    package_type=p.pack_type or "EP",
                    pieces=1,
                    gross_weight=f"{p.weight:.2f}",
                    volume=f"{vol:.2f}",
                    length=f"{length:.2f}",
                    width=f"{width:.2f}",
                    height=f"{height:.2f}",
                    stackable=True,
                    dgr=False,
                )
            )

        total_weight = sum(p.weight for p in req.parcels)
        total_volume = sum(float(pos.volume) for pos in positions)

        raw_group = (req.options or {}).get("dsvConnectGroupId")
        if isinstance(raw_group, (int, float)) and raw_group is not None:
            connect_group_id = int(raw_group)
        elif use_international:
            connect_group_id = self.config.international_group_id
        else:
            connect_group_id = loc.group_id

        customs_opt = _read_options_boolean((req.options or {}).get("dsvCustomsClearance"))
        if isinstance(customs_opt, bool):
            customs_clearance = customs_opt
        elif use_international and cross_border:
            customs_clearance = dest_country not in EU_DESTINATION
        else:
            customs_clearance = False

        incoterm_location = (
            f"{recipient.city}, {dest_country}"
            if use_international and cross_border
            else loc.sender_city or payer.sender_city
        )

        return DsvBookingLandRequest(
            application_area=DsvApplicationArea(
                access_key=self.config.credentials.access_key,
                group_id=connect_group_id,
                request_id=f"OM-{req.order_no}-{int(pickup_start.timestamp() * 1000)}",
                user_id=self.config.credentials.user_id,
            ),
            submit_booking=True,
            return_barcode_references=True,
            barcode_request=DSV_DEFAULT_BARCODE_REQUEST,
            addresses=addresses,
            incoterm=self.config.incoterm,
            incoterm_location=incoterm_location,
            product_code=self.config.product_code,
            measurement_type="METRIC",
            gross_weight=f"{total_weight:.2f}",
            cargo_description=cargo_top,
            customs_clearance=customs_clearance,
            indoor_delivery=False,
            neutral_shipping=False,
            special_cargo=False,
            service_type="D2D",
            express=False,
            food_related=False,
            heated_transport=False,
            home_delivery=False,
            measure_unit="VOLUME",
            measure_unit_volume=f"{total_volume:.2f}",
            own_pickup=False,
            pickup_dates=DsvPickupDates(
                pick_up_date_from=pickup_start.isoformat(),
                pick_up_date_to=pickup_end.isoformat(),
            ),
            references=[DsvReference(number=req.order_no, id="SHIPPER_REFERENCE_NUMBER")],
            shipping_information=DsvShippingInformation(
                shipment_positions=positions,
                gross_weight=f"{total_weight:.2f}",
                volume=f"{total_volume:.2f}",
            ),
        )

    async def _call_soap(self, xml: str, request_id: str | None = None) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                self.config.endpoint,
                content=xml.encode("utf-8"),
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
            )
        text = res.text
        if not res.is_success:
            detail = extract_schenker_error_detail(text)
            ctx = f' [code={detail[0]} message="{detail[1]}"]' if detail else ""
            raise CarrierIntegrationError(
                "DSV",
                f"SOAP error ({res.status_code}) requestId={request_id or '-'}{ctx}: {text[:500]}",
            )
        return text

    def _parse_response(
        self,
        xml: str,
        *,
        order_no: str | None = None,
        request_id: str | None = None,
        pack_types: str | None = None,
    ) -> DsvBookingResponse:
        root = ET.fromstring(xml)
        body = _dig(root, "Body")
        fault = _dig(body, "Fault")
        if fault is not None:
            fault_string = _text(_dig(fault, "faultstring")) or "SOAP Fault"
            detail = extract_schenker_error_detail(xml)
            code_msg = f' [schenkerCode={detail[0]} message="{detail[1]}"]' if detail else ""
            raise CarrierIntegrationError(
                "DSV",
                f"SOAP Fault (requestId={request_id or '-'} orderNo={order_no or '-'})"
                f"{code_msg}: {fault_string}",
            )

        resp = _dig(body, "getBookingResponse", "out") or _dig(body, "getBookingResponse")
        if resp is None:
            raise CarrierIntegrationError("DSV", f"Unexpected response structure: {xml[:300]}")

        barcode_refs: list[DsvBarcodeReference] = []
        refs_el = _dig(resp, "barcodeReference")
        if refs_el is not None:
            # single or repeated elements
            parent = resp
            for child in parent:
                tag = child.tag.split("}")[-1]
                if tag == "barcodeReference":
                    barcode_refs.append(
                        DsvBarcodeReference(
                            barcode=_text(_dig(child, "barcode")),
                            barcode_type=_text(_dig(child, "barcodeType")),
                        )
                    )

        app_area = _dig(resp, "applicationArea")
        return DsvBookingResponse(
            request_id=_text(_dig(app_area, "requestID")) or None,
            booking_id=_text(_dig(resp, "bookingId")),
            barcode_references=barcode_refs or None,
            barcode_document=_text(_dig(resp, "barcodeDocument")) or None,
        )
