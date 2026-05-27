"""DPD PackageObjServices — SOAP generateSpedLabelsV4."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Literal

import httpx

from modules.shipping.lib.adapters.dpd.auth import DpdCredentials
from modules.shipping.lib.adapters.errors import CarrierIntegrationError

SessionType = Literal["DOMESTIC", "INTERNATIONAL"]
DocFormat = Literal["PDF", "ZPL", "EPL", "XML"]


def _esc_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_generate_sped_labels_v4_xml(
    waybills: list[str],
    session_type: SessionType,
    creds: DpdCredentials,
    output_doc_format: DocFormat = "PDF",
) -> str:
    waybill_xml = "".join(f"<waybill>{_esc_xml(w)}</waybill>" for w in waybills)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:dpd="http://dpdservices.dpd.com.pl/">
  <soapenv:Header/>
  <soapenv:Body>
    <dpd:generateSpedLabelsV4>
      <dpdServicesParamsV1>
        <policy>IGNORE_ERRORS</policy>
        <session>
          <packages>
            <parcels>
              {waybill_xml}
            </parcels>
          </packages>
          <sessionType>{session_type}</sessionType>
        </session>
      </dpdServicesParamsV1>
      <outputDocFormatV1>{output_doc_format}</outputDocFormatV1>
      <outputDocPageFormatV1>LBL_PRINTER</outputDocPageFormatV1>
      <outputLabelType>BIC3</outputLabelType>
      <authDataV1>
        <login>{_esc_xml(creds.login)}</login>
        <masterFid>{creds.master_fid}</masterFid>
        <password>{_esc_xml(creds.password)}</password>
      </authDataV1>
    </dpd:generateSpedLabelsV4>
  </soapenv:Body>
</soapenv:Envelope>"""


def _dig(obj: ET.Element | None, *local_names: str) -> ET.Element | None:
    if obj is None:
        return None
    for name in local_names:
        found: ET.Element | None = None
        for child in obj:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == name:
                found = child
                break
        if found is None:
            return None
        obj = found
    return obj


def _element_text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    return (el.text or "").strip() or None


def parse_document_data(soap_text: str) -> str:
    try:
        root = ET.fromstring(soap_text)
    except ET.ParseError as exc:
        raise CarrierIntegrationError("DPD", f"SOAP response is not valid XML: {soap_text[:200]}") from exc

    body = _dig(root, "Body")
    fault = _dig(body, "Fault")
    if fault is not None:
        fs = _element_text(_dig(fault, "faultstring")) or "SOAP Fault"
        raise CarrierIntegrationError("DPD", f"SOAP Fault: {fs}")

    ret = _dig(body, "generateSpedLabelsV4Response", "return")
    if ret is None:
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag == "return":
                ret = el
                break

    if ret is None:
        raise CarrierIntegrationError("DPD", f"SOAP: missing return in response ({soap_text[:200]})")

    doc_el = _dig(ret, "documentData")
    if doc_el is None:
        for child in ret:
            tag = child.tag.split("}")[-1]
            if tag == "documentData":
                doc_el = child
                break

    doc = _element_text(doc_el)
    if not doc:
        raise CarrierIntegrationError("DPD", "SOAP: missing documentData in response")
    return doc


async def fetch_sped_labels_pdf_base64(
    waybills: list[str],
    session_type: SessionType,
    creds: DpdCredentials,
    soap_url: str,
    label_format: DocFormat = "PDF",
) -> str:
    xml = build_generate_sped_labels_v4_xml(waybills, session_type, creds, label_format)
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            soap_url,
            content=xml.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
        )
    text = res.text
    if not res.is_success:
        raise CarrierIntegrationError(
            "DPD",
            f"SOAP generateSpedLabelsV4 HTTP {res.status_code}: {text[:500]}",
        )
    return parse_document_data(text)
