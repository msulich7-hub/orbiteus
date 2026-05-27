"""DSV pickup location profiles — port of dsv-locations.ts / dsv-carrier.ts."""

from __future__ import annotations

from dataclasses import dataclass

from modules.shipping.lib.adapters.errors import CarrierIntegrationError

DSV_DEFAULT_INTERNATIONAL_GROUP_ID = 2170537


@dataclass(frozen=True)
class DsvPickupLocation:
    key: str
    label: str
    group_id: int
    shipper_address_id: str
    pickup_address_id: str
    sender_name: str
    sender_street: str
    sender_zip: str
    sender_city: str


PICKUP_LOCATIONS: tuple[DsvPickupLocation, ...] = (
    DsvPickupLocation(
        key="bielsko",
        label="PLdom MDM NT SP. Z O.O. - BIELSKO-BIAŁA",
        group_id=2170538,
        shipper_address_id="PLMDMNT007000",
        pickup_address_id="PLMDMNT007000",
        sender_name="MDM NT SP. Z O.O.",
        sender_street="ul. Bestwińska 143",
        sender_zip="43-346",
        sender_city="Bielsko-Biała",
    ),
    DsvPickupLocation(
        key="cieszyn",
        label="PLdom MDM SA - CIESZYN",
        group_id=2170539,
        shipper_address_id="PLMDMNT007000",
        pickup_address_id="PLMDMNT007004",
        sender_name="MDM SA",
        sender_street="ul. Bielska 206",
        sender_zip="43-400",
        sender_city="Cieszyn",
    ),
    DsvPickupLocation(
        key="bazanowice",
        label="PLdom MDM NT SP. Z O.O. - BAZANOWICE",
        group_id=2170540,
        shipper_address_id="PLMDMNT007000",
        pickup_address_id="PLMDMNT007005",
        sender_name="MDM NT SP. Z O.O.",
        sender_street="Cieszyńska 1F",
        sender_zip="43-440",
        sender_city="Bażanowice",
    ),
)


def get_pickup_locations() -> tuple[DsvPickupLocation, ...]:
    return PICKUP_LOCATIONS


def get_payer_shipper_profile() -> DsvPickupLocation:
    """Schenker SHIPPER (contractual payer) — always MDM NT Bielsko."""
    return PICKUP_LOCATIONS[0]


def resolve_pickup_location(key: str | None = None) -> DsvPickupLocation:
    if not key:
        return PICKUP_LOCATIONS[0]
    lowered = key.lower()
    for loc in PICKUP_LOCATIONS:
        if loc.key == lowered or str(loc.group_id) == key:
            return loc
    available = ", ".join(l.key for l in PICKUP_LOCATIONS)
    raise CarrierIntegrationError("DSV", f'Unknown pickup location "{key}". Available: {available}')
