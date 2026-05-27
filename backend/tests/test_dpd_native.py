"""Unit tests for native DPD adapter — no live HTTP."""

from __future__ import annotations

import os

import pytest

from modules.shipping.lib.adapters.dpd.auth import resolve_dpd_credentials
from modules.shipping.lib.adapters.dpd.client import build_generate_packages_body
from modules.shipping.lib.adapters.dpd.config import DpdCarrierConfig, DpdCredentials, DpdSenderProfile
from modules.shipping.lib.adapters.dpd.soap_labels import build_generate_sped_labels_v4_xml
from modules.shipping.lib.adapters.dpd_adapter import sender_from_ifs_contract
from modules.shipping.lib.carrier_registry import adapter_for
from modules.shipping.lib.shipment_types import ParcelInfo, ShipmentAddressParty, ShipmentRequest


def _dpd_config() -> DpdCarrierConfig:
    return DpdCarrierConfig(
        base_url="https://dpdservicesdemo.dpd.com.pl/public",
        soap_package_url="https://dpdservicesdemo.dpd.com.pl/DPDPackageObjServicesService/DPDPackageObjServices",
        credentials=DpdCredentials(login="test", password="secret", master_fid=1495, fid=1495),
        sender=DpdSenderProfile(
            company="MDM NT SP. Z O.O.",
            name="Logistyka",
            address="ul. Bestwińska 143",
            city="Bielsko-Biała",
            postal_code="43346",
        ),
        label_format="PDF",
        default_payer_type="SENDER",
    )


def test_resolve_dpd_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DPD_LOGIN", raising=False)
    monkeypatch.delenv("DPD_PASSWORD", raising=False)
    monkeypatch.delenv("DPD_MASTER_FID", raising=False)
    with pytest.raises(RuntimeError, match="Missing DPD credentials"):
        resolve_dpd_credentials()


def test_build_generate_request_bis_sender() -> None:
    sender = sender_from_ifs_contract("BIS^01")
    assert sender is not None
    assert sender.company_name == "MDM NT SP. Z O.O."
    assert "Bestwińska" in sender.address

    req = ShipmentRequest(
        order_no="ORB-DPD-BIS-001",
        carrier_code="DPD",
        contract="BIS^01",
        recipient=ShipmentAddressParty(
            company_name="Firma Test",
            address="ul. Testowa 1",
            zip="02-274",
            city="Warszawa",
            country="PL",
        ),
        sender=sender,
        parcels=[ParcelInfo(weight=5.5, length=40, width=30, height=20)],
        goods_description="Czesci zamienne",
    )
    body = build_generate_packages_body(req, _dpd_config())
    pkg = body["packages"][0]
    assert pkg["ref1"] == "ORB-DPD-BIS-001"
    assert pkg["sender"]["postalCode"] == "43346"
    assert pkg["receiver"]["postalCode"] == "02274"
    assert pkg["payerFID"] == 1495
    assert pkg["parcels"][0]["weight"] == 5.5


def test_build_soap_xml_escapes_and_waybills() -> None:
    creds = DpdCredentials(login="user&co", password='pa"ss', master_fid=1495, fid=1495)
    xml = build_generate_sped_labels_v4_xml(
        ["0000795537918Q", "WB<2>"],
        "DOMESTIC",
        creds,
        "PDF",
    )
    assert "user&amp;co" in xml
    assert "pa&quot;ss" in xml
    assert "<waybill>0000795537918Q</waybill>" in xml
    assert "DOMESTIC" in xml


def test_adapter_for_dpd_native(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPD_LOGIN", "test")
    monkeypatch.setenv("DPD_PASSWORD", "secret")
    monkeypatch.setenv("DPD_MASTER_FID", "1495")
    monkeypatch.setenv("SHIPPING_DPD_NATIVE", "1")
    from modules.shipping.lib.adapters.dpd_adapter import DpdPythonAdapter

    adapter = adapter_for("DPD")
    assert isinstance(adapter, DpdPythonAdapter)


def test_adapter_for_dpd_mercato_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DPD_LOGIN", "test")
    monkeypatch.setenv("DPD_PASSWORD", "secret")
    monkeypatch.setenv("DPD_MASTER_FID", "1495")
    monkeypatch.setenv("SHIPPING_DPD_NATIVE", "0")
    from modules.shipping.lib.adapters.mercato_hub import MercatoHubAdapter

    adapter = adapter_for("DPD")
    assert isinstance(adapter, MercatoHubAdapter)
