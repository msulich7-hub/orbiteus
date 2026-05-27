"""Routing — MatrixSplit + IFS forward agent (mercato-logistics-hub strategies)."""

from __future__ import annotations

from modules.shipping.lib.carrier_registry import normalize_carrier_code
from modules.shipping.lib.carrier_settings import CarrierSettings, get_carrier_settings


def resolve_carrier_for_shipment(
    *,
    forward_agent_id: str | None = None,
    weight_kg: float | None = None,
    is_locker: bool = False,
    is_pallet: bool = False,
    settings: CarrierSettings | None = None,
) -> str:
    """Return canonical carrier code (MOCK, DPD, DSV, GEODIS, INPOST)."""
    cfg = settings or get_carrier_settings()

    if cfg.logistics_respect_ifs_agent and forward_agent_id:
        return normalize_carrier_code(forward_agent_id)

    if is_locker:
        return "INPOST"

    w = weight_kg or 0.0
    if is_pallet or w >= cfg.logistics_heavy_kg:
        pallet = (cfg.logistics_pallet_carrier or "geodis").lower()
        return "DSV" if pallet in ("schenker", "dsv") else "GEODIS"

    if w > 0 and w <= cfg.logistics_light_max_kg:
        return "DPD"

    return "DPD"
