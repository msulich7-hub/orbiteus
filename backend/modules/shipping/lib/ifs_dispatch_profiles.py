"""IFS contract → dispatch site (pickup / sender profile) — port of ifs-dispatch-profiles.ts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IfsDispatchSiteCode = Literal["BAZ", "CIE", "BIS"]


@dataclass(frozen=True)
class IfsDispatchProfile:
    site_code: IfsDispatchSiteCode
    dsv_pickup_location_key: str
    sender_company_name: str
    geodis_shipper_symbol: str
    origin_line1: str
    origin_city: str
    origin_postal_code: str
    origin_country_code: str = "PL"
    origin_line2: str | None = None


_PROFILES: dict[IfsDispatchSiteCode, IfsDispatchProfile] = {
    "BIS": IfsDispatchProfile(
        site_code="BIS",
        dsv_pickup_location_key="bielsko",
        sender_company_name="MDM NT SP. Z O.O.",
        geodis_shipper_symbol="PL244538",
        origin_line1="ul. Bestwińska 143",
        origin_city="Bielsko-Biała",
        origin_postal_code="43-346",
    ),
    "CIE": IfsDispatchProfile(
        site_code="CIE",
        dsv_pickup_location_key="cieszyn",
        sender_company_name="MDM SA",
        geodis_shipper_symbol="PL244538",
        origin_line1="ul. Bielska 206",
        origin_city="Cieszyn",
        origin_postal_code="43-400",
    ),
    "BAZ": IfsDispatchProfile(
        site_code="BAZ",
        dsv_pickup_location_key="bazanowice",
        sender_company_name="MDM NT SP. Z O.O.",
        geodis_shipper_symbol="PL244538",
        origin_line1="Cieszyńska 1F",
        origin_city="Bażanowice",
        origin_postal_code="43-440",
    ),
}


def _extract_site_code(contract: str) -> IfsDispatchSiteCode | None:
    raw = contract.strip().upper()
    if not raw:
        return None
    head = raw.split("^")[0].strip() if "^" in raw else raw
    if head.startswith("BAZ"):
        return "BAZ"
    if head.startswith("CIE"):
        return "CIE"
    if head.startswith("BIS"):
        return "BIS"
    return None


def resolve_ifs_dispatch_profile(contract: str | None) -> IfsDispatchProfile | None:
    if contract is None or not str(contract).strip():
        return None
    code = _extract_site_code(str(contract))
    if not code:
        return None
    return _PROFILES.get(code)
