"""Geodis PUGO types — port of mercato-shipping-hub geodis-types.ts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

GEODIS_PALLET_DEFINITIONS: Final[dict[str, dict[str, float | str]]] = {
    "EUR": {"name": "Europaleta 1.2x0.8", "length": 1.20, "width": 0.80, "height": 1.80, "pallet_places": 1.00},
    "PAL.INNA": {"name": "PALETA INNA JEDNORAZOWA", "length": 0.00, "width": 0.00, "height": 0.00, "pallet_places": 0.00},
    "PAL0808": {"name": "Paleta 0.8x0.8", "length": 0.80, "width": 0.80, "height": 1.20, "pallet_places": 0.67},
    "PAL15": {"name": "Paleta 1.2x1.2", "length": 1.20, "width": 1.20, "height": 1.80, "pallet_places": 1.50},
    "PAL1612": {"name": "Paleta 1.6x1.2", "length": 1.60, "width": 1.20, "height": 1.80, "pallet_places": 2.00},
    "PAL2004": {"name": "Paleta 2.0x0.4", "length": 2.00, "width": 0.40, "height": 1.00, "pallet_places": 0.83},
    "PAL2005": {"name": "Paleta 2.0x0.5", "length": 2.00, "width": 0.50, "height": 1.00, "pallet_places": 1.04},
    "PAL3004": {"name": "Paleta 3.0x0.4", "length": 3.00, "width": 0.40, "height": 1.00, "pallet_places": 1.25},
    "PAL3008": {"name": "Paleta 3.0x0.8", "length": 3.00, "width": 0.80, "height": 1.00, "pallet_places": 2.50},
    "PLP": {"name": "Paleta 1.2x1.0", "length": 1.20, "width": 1.00, "height": 1.80, "pallet_places": 1.25},
    "PLPAL": {"name": "Półpaleta 0.60x0.80", "length": 0.80, "width": 0.60, "height": 1.00, "pallet_places": 0.50},
}

GEODIS_PALLET_CODE_ALIASES: Final[dict[str, str]] = {
    "PAL1212": "PAL15",
    "PAL1210": "PLP",
}


def resolve_geodis_package_symbol(value: str) -> str:
    t = (value or "").strip()
    if not t:
        return "EUR"
    return GEODIS_PALLET_CODE_ALIASES.get(t) or GEODIS_PALLET_CODE_ALIASES.get(t.upper()) or t


@dataclass
class GeodisCredentials:
    shipper_id: int
    password: str


@dataclass
class GeodisSenderConfig:
    symbol: str
    name: str
    person: str
    phone: str
    country: str
    city: str
    street_full: str
    zip_code: str


@dataclass
class GeodisParcel:
    package_symbol: str
    name: str
    amount: int
    weight_total: float
    volume_total: float
    pal_places_total: float
    length: float
    width: float
    height: float
