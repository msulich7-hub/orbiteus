"""Carrier env settings — same variable names as Mercato shipping-hub / OM presets.

Source of truth for names:
  mercato/modules/mercato-shipping-hub/.env.example
  mercato/open-mercato/packages/carrier-*/lib/preset.ts
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CarrierSettings(BaseSettings):
    """Reads process env; field names map to Mercato DSV_*, GEODIS_*, DPD_*, INPOST_*."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    # Logistics routing (mercato-logistics-hub / LOGISTICS-HUB.md)
    logistics_pallet_carrier: str = Field(default="geodis", alias="LOGISTICS_PALLET_CARRIER")
    logistics_heavy_kg: float = Field(default=100.0, alias="LOGISTICS_HEAVY_KG")
    logistics_light_max_kg: float = Field(default=30.0, alias="LOGISTICS_LIGHT_MAX_KG")
    logistics_respect_ifs_agent: bool = Field(default=True, alias="LOGISTICS_RESPECT_IFS_AGENT")

    # DSV / Schenker
    dsv_access_key: str | None = Field(default=None, alias="DSV_ACCESS_KEY")
    dsv_group_id: str | None = Field(default=None, alias="DSV_GROUP_ID")
    dsv_user_id: str | None = Field(default=None, alias="DSV_USER_ID")
    dsv_env: str = Field(default="test", alias="DSV_ENV")
    dsv_endpoint: str | None = Field(default=None, alias="DSV_ENDPOINT")
    dsv_incoterm: str = Field(default="DAP", alias="DSV_INCOTERM")
    dsv_product_code: str = Field(default="43", alias="DSV_PRODUCT_CODE")
    dsv_vat_no: str = Field(default="5482614481", alias="DSV_VAT_NO")
    dsv_default_location: str = Field(default="bielsko", alias="DSV_DEFAULT_LOCATION")
    dsv_sender_country: str = Field(default="PL", alias="DSV_SENDER_COUNTRY")
    dsv_sender_phone: str | None = Field(default=None, alias="DSV_SENDER_PHONE")
    dsv_sender_email: str | None = Field(default=None, alias="DSV_SENDER_EMAIL")
    dsv_international_group_id: int = Field(default=2170537, alias="DSV_INTERNATIONAL_GROUP_ID")

    # Geodis
    geodis_shipper_id: str | None = Field(default=None, alias="GEODIS_SHIPPER_ID")
    geodis_password: str | None = Field(default=None, alias="GEODIS_PASSWORD")

    # DPD (OM_INTEGRATION_DPD_* aliases in preset.ts)
    dpd_login: str | None = Field(default=None, validation_alias="DPD_LOGIN")
    dpd_password: str | None = Field(default=None, validation_alias="DPD_PASSWORD")
    dpd_master_fid: str | None = Field(default=None, validation_alias="DPD_MASTER_FID")
    dpd_fid: str | None = Field(default=None, validation_alias="DPD_FID")
    dpd_env: str = Field(default="test", validation_alias="DPD_ENV")
    dpd_endpoint: str | None = Field(default=None, validation_alias="DPD_ENDPOINT")
    dpd_soap_url: str | None = Field(default=None, validation_alias="DPD_SOAP_URL")
    dpd_label_format: str = Field(default="PDF", validation_alias="DPD_LABEL_FORMAT")
    shipping_dpd_native: bool = Field(default=True, validation_alias="SHIPPING_DPD_NATIVE")

    # InPost
    inpost_api_token: str | None = Field(default=None, alias="INPOST_API_TOKEN")
    inpost_organization_id: str | None = Field(default=None, alias="INPOST_ORGANIZATION_ID")
    inpost_env: str = Field(default="sandbox", alias="INPOST_ENV")

    # Kanał B / IFS relay (optional — async feedback)
    ifs_relay_base_url: str | None = Field(default=None, alias="IFS_RELAY_BASE_URL")
    ifs_relay_server_api_key: str | None = Field(default=None, alias="IFS_RELAY_SERVER_API_KEY")

    # IFS inbound webhook (Oracle MS_INTEGRATION_API SECONDARY)
    ifs_webhook_enabled: bool = Field(default=True, alias="IFS_WEBHOOK_ENABLED")
    ifs_webhook_secret: str | None = Field(default=None, alias="IFS_WEBHOOK_SECRET")
    ifs_auto_dispatch: bool = Field(default=False, alias="IFS_AUTO_DISPATCH")
    ifs_webhook_allowlist: str | None = Field(default=None, alias="IFS_WEBHOOK_ALLOWLIST")

    def carrier_configured(self, code: str) -> bool:
        canonical = code.upper()
        if canonical in ("DSV", "SCHENKER", "DBSCHENKER"):
            return bool(self.dsv_access_key)
        if canonical in ("GEODIS", "PEKAES"):
            return bool(self.geodis_shipper_id and self.geodis_password)
        if canonical == "DPD":
            return bool(self.dpd_login and self.dpd_password and self.dpd_master_fid)
        if canonical == "INPOST":
            return bool(self.inpost_api_token and self.inpost_organization_id)
        if canonical == "MOCK":
            return True
        return False

    def configured_carriers(self) -> list[str]:
        return [c for c in ("MOCK", "DPD", "INPOST", "GEODIS", "DSV") if self.carrier_configured(c)]


@lru_cache
def get_carrier_settings() -> CarrierSettings:
    return CarrierSettings()
