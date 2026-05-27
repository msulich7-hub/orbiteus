"""DPD carrier configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from modules.shipping.lib.adapters.dpd.auth import DpdCredentials, resolve_dpd_credentials

DpdDocFormat = Literal["PDF", "ZPL", "EPL", "XML"]
DpdPayerType = Literal["SENDER", "RECEIVER", "THIRD_PARTY"]

ENDPOINT_TEST = "https://dpdservicesdemo.dpd.com.pl/public"
ENDPOINT_PROD = "https://dpdservices.dpd.com.pl/public"
SOAP_TEST = "https://dpdservicesdemo.dpd.com.pl/DPDPackageObjServicesService/DPDPackageObjServices"
SOAP_PROD = "https://dpdservices.dpd.com.pl/DPDPackageObjServicesService/DPDPackageObjServices"


@dataclass(frozen=True)
class DpdSenderProfile:
    company: str
    name: str
    address: str
    city: str
    postal_code: str
    country_code: str = "PL"
    phone: str | None = None
    email: str | None = None


@dataclass
class DpdCarrierConfig:
    base_url: str
    soap_package_url: str
    credentials: DpdCredentials
    sender: DpdSenderProfile
    label_format: DpdDocFormat
    default_payer_type: DpdPayerType


def resolve_dpd_config_from_env() -> DpdCarrierConfig:
    env = (os.environ.get("DPD_ENV") or "test").lower()
    credentials = resolve_dpd_credentials()
    label_fmt = (os.environ.get("DPD_LABEL_FORMAT") or "PDF").upper()
    if label_fmt not in ("PDF", "ZPL", "EPL", "XML"):
        label_fmt = "PDF"

    return DpdCarrierConfig(
        base_url=os.environ.get("DPD_ENDPOINT") or (ENDPOINT_PROD if env == "prod" else ENDPOINT_TEST),
        soap_package_url=os.environ.get("DPD_SOAP_URL")
        or (SOAP_PROD if env == "prod" else SOAP_TEST),
        credentials=credentials,
        sender=DpdSenderProfile(
            company=os.environ.get("DPD_SENDER_COMPANY") or "MDM NT SP. Z O.O.",
            name=os.environ.get("DPD_SENDER_NAME") or "Logistyka",
            address=os.environ.get("DPD_SENDER_ADDRESS") or "ul. Bestwińska 143",
            city=os.environ.get("DPD_SENDER_CITY") or "Bielsko-Biała",
            postal_code=(os.environ.get("DPD_SENDER_POSTAL_CODE") or "43346").replace("-", ""),
            country_code=os.environ.get("DPD_SENDER_COUNTRY") or "PL",
            phone=os.environ.get("DPD_SENDER_PHONE"),
            email=os.environ.get("DPD_SENDER_EMAIL"),
        ),
        label_format=label_fmt,  # type: ignore[assignment]
        default_payer_type="SENDER",
    )
