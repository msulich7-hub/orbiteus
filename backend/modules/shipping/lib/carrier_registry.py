"""Carrier code registry — ported from mercato-shipping-hub carrier-registry.ts."""

from __future__ import annotations

from typing import Protocol


class UnknownCarrierError(LookupError):
    def __init__(self, carrier_code: str) -> None:
        self.carrier_code = carrier_code
        super().__init__(
            f'Unknown carrier code "{carrier_code}". '
            "Supported: DSV, SCHENKER, DBSCHENKER, GEODIS, PEKAES, DPD, INPOST, MOCK."
        )


# Mercato providerKey / IFS forward_agent_id aliases → canonical code
CARRIER_ALIASES: dict[str, str] = {
    "DSV": "DSV",
    "SCHENKER": "DSV",
    "DBSCHENKER": "DSV",
    "GEODIS": "GEODIS",
    "PEKAES": "GEODIS",
    "DPD": "DPD",
    "INPOST": "INPOST",
    "MOCK": "MOCK",
    "GLS": "GLS",  # planned in Mercato — adapter TBD
}

SUPPORTED_CARRIERS = frozenset(CARRIER_ALIASES)


def normalize_carrier_code(carrier_code: str | None) -> str:
    if not carrier_code or not carrier_code.strip():
        raise UnknownCarrierError("<empty>")
    key = carrier_code.strip().upper()
    if key not in CARRIER_ALIASES:
        raise UnknownCarrierError(key)
    return CARRIER_ALIASES[key]


class CarrierAdapter(Protocol):
    code: str

    async def create_label(self, payload: dict) -> dict:
        """Return {tracking_number, label_base64?, raw?}."""


def adapter_for(code: str) -> CarrierAdapter:
    canonical = normalize_carrier_code(code)
    import os

    from modules.shipping.lib.adapters.mock import MockCarrierAdapter
    from modules.shipping.lib.adapters.mercato_hub import MercatoHubAdapter
    from modules.shipping.lib.adapters.geodis_adapter import GeodisPythonAdapter
    from modules.shipping.lib.adapters.dsv_adapter import DsvPythonAdapter
    from modules.shipping.lib.adapters.dpd_adapter import DpdPythonAdapter
    from modules.shipping.lib.carrier_settings import get_carrier_settings

    if canonical == "MOCK":
        return MockCarrierAdapter()

    cfg = get_carrier_settings()
    if not cfg.carrier_configured(canonical):
        raise NotImplementedError(
            f"Carrier {canonical} not configured — set env vars from crm-engine/.env.shipping.example"
        )

    if canonical in ("GEODIS", "PEKAES") and os.environ.get("SHIPPING_GEODIS_NATIVE", "1").lower() not in (
        "0",
        "false",
        "no",
    ):
        return GeodisPythonAdapter(canonical)

    if canonical == "DSV" and os.environ.get("SHIPPING_DSV_NATIVE", "1").lower() not in (
        "0",
        "false",
        "no",
    ):
        return DsvPythonAdapter(canonical)

    if canonical == "DPD" and os.environ.get("SHIPPING_DPD_NATIVE", "1").lower() not in (
        "0",
        "false",
        "no",
    ):
        return DpdPythonAdapter(canonical)

    return MercatoHubAdapter(canonical)
