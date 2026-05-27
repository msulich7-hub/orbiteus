"""DSV env configuration — port of dsv-auth.ts + resolveDsvConfig()."""

from __future__ import annotations

import os
from dataclasses import dataclass

from modules.shipping.lib.adapters.dsv.locations import DSV_DEFAULT_INTERNATIONAL_GROUP_ID
from modules.shipping.lib.adapters.dsv.types import DsvConnectCredentials

ENDPOINT_TEST = "https://eschenker-fat.dbschenker.com/webservice/bookingWebServiceV1_1"
ENDPOINT_PROD = "https://eschenker.dbschenker.com/webservice/bookingWebServiceV1_1"


def _env_dsv(*keys: str) -> str | None:
    for key in keys:
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def resolve_dsv_credentials() -> DsvConnectCredentials:
    access_key = _env_dsv("DSV_ACCESS_KEY", "OM_INTEGRATION_DSV_ACCESS_KEY")
    if not access_key:
        raise RuntimeError(
            "Set DSV_ACCESS_KEY or OM_INTEGRATION_DSV_ACCESS_KEY "
            "(see crm-engine/.env.shipping.example)."
        )
    group_raw = _env_dsv("DSV_GROUP_ID", "OM_INTEGRATION_DSV_GROUP_ID")
    group_id = int(group_raw) if group_raw else None
    user_id = _env_dsv("DSV_USER_ID", "OM_INTEGRATION_DSV_USER_ID")
    return DsvConnectCredentials(access_key=access_key, group_id=group_id, user_id=user_id)


@dataclass
class DsvCarrierConfig:
    endpoint: str
    credentials: DsvConnectCredentials
    incoterm: str
    product_code: str
    vat_no: str
    default_pickup_location: str
    sender_country_code: str
    sender_phone: str | None
    sender_email: str | None
    international_group_id: int


def resolve_dsv_config_from_env() -> DsvCarrierConfig:
    env = (_env_dsv("DSV_ENV", "OM_INTEGRATION_DSV_ENV") or "test").lower()
    credentials = resolve_dsv_credentials()
    intl_raw = _env_dsv("DSV_INTERNATIONAL_GROUP_ID", "OM_INTEGRATION_DSV_INTERNATIONAL_GROUP_ID")
    intl_parsed = int(intl_raw) if intl_raw else None
    endpoint_override = os.environ.get("DSV_ENDPOINT")
    return DsvCarrierConfig(
        endpoint=endpoint_override or (ENDPOINT_PROD if env == "prod" else ENDPOINT_TEST),
        credentials=credentials,
        incoterm=_env_dsv("DSV_INCOTERM", "OM_INTEGRATION_DSV_INCOTERM") or "DAP",
        product_code=_env_dsv("DSV_PRODUCT_CODE", "OM_INTEGRATION_DSV_PRODUCT_CODE") or "43",
        vat_no=_env_dsv("DSV_VAT_NO", "OM_INTEGRATION_DSV_VAT_NO") or "5482614481",
        default_pickup_location=_env_dsv("DSV_DEFAULT_LOCATION", "OM_INTEGRATION_DSV_DEFAULT_LOCATION")
        or "bielsko",
        sender_country_code=_env_dsv("DSV_SENDER_COUNTRY", "OM_INTEGRATION_DSV_SENDER_COUNTRY") or "PL",
        sender_phone=_env_dsv("DSV_SENDER_PHONE", "OM_INTEGRATION_DSV_SENDER_PHONE"),
        sender_email=_env_dsv("DSV_SENDER_EMAIL", "OM_INTEGRATION_DSV_SENDER_EMAIL"),
        international_group_id=intl_parsed if intl_parsed is not None else DSV_DEFAULT_INTERNATIONAL_GROUP_ID,
    )
