"""IFS TR_FORW_PACKAGE_DEF → carrier pack type (mercato packaging-matrix.ts)."""



from __future__ import annotations



from dataclasses import dataclass



# IFS pack code → {dsv, geodis, dpd}

PACKAGING_MATRIX: dict[str, dict[str, str]] = {

    "PACZKASTD": {"dsv": "PC", "geodis": "PC", "dpd": "PARCEL"},

    "PACZKANST": {"dsv": "CTXX", "geodis": "PC", "dpd": "PARCEL"},

    "DLUZYCA": {"dsv": "CTXX", "geodis": "PA", "dpd": "PARCEL"},

    "PAL_A": {"dsv": "EP", "geodis": "EUR", "dpd": "PALLET"},

    "PAL_B": {"dsv": "XP1", "geodis": "PLP", "dpd": "PALLET"},

    "PAL_C": {"dsv": "XP", "geodis": "PAL1612", "dpd": "PALLET"},

    "PAL_D": {"dsv": "XP", "geodis": "PAL3008", "dpd": "PALLET"},

    "PAL_E": {"dsv": "XP", "geodis": "PAL2004", "dpd": "PALLET"},

    "PAL_F": {"dsv": "XP", "geodis": "PAL2005", "dpd": "PALLET"},

    "PAL_G": {"dsv": "XPP2", "geodis": "PLPAL", "dpd": "HALF_PALLET"},

    "PAL_H": {"dsv": "XP", "geodis": "PAL15", "dpd": "PALLET"},

    "PAL_I": {"dsv": "XP", "geodis": "PAL3004", "dpd": "PALLET"},

    "PAL_J": {"dsv": "XP", "geodis": "PAL15", "dpd": "PALLET"},

    "PAL_O": {"dsv": "XP", "geodis": "PAL3004", "dpd": "PALLET"},

    "PAL_P": {"dsv": "XP", "geodis": "PAL2004", "dpd": "PALLET"},

    "PAL_R": {"dsv": "XP", "geodis": "PAL2005", "dpd": "PALLET"},

    "PAL_Y": {"dsv": "XP", "geodis": "PAL0808", "dpd": "PALLET"},

}



# pack_type → is pallet (packTypeGlob PALLET in Mercato matrix)

_PALLET_TYPES = frozenset(PACKAGING_MATRIX) - {"PACZKASTD", "PACZKANST", "DLUZYCA"}



CARRIER_ALIAS: dict[str, str] = {

    "SCHENKER": "dsv",

    "DBSCHENKER": "dsv",

    "DSV": "dsv",

    "GEODIS": "geodis",

    "PEKAES": "geodis",

    "DPD": "dpd",

}





@dataclass(frozen=True)

class PackageDimensions:

    length_cm: float

    width_cm: float

    height_cm: float

    weight_kg: float





# Default dimensions from packaging-matrix.ts (IFS TR_FORW_PACKAGE_DEF subset)

_DEFAULT_DIMENSIONS: dict[str, PackageDimensions] = {

    "PACZKASTD": PackageDimensions(40, 40, 100, 0.3),

    "PACZKANST": PackageDimensions(20, 20, 200, 0.3),

    "DLUZYCA": PackageDimensions(265, 20, 20, 0.3),

    "PAL_A": PackageDimensions(120, 80, 180, 16),

    "PAL_B": PackageDimensions(120, 100, 140, 18),

    "PAL_C": PackageDimensions(160, 120, 130, 20),

    "PAL_D": PackageDimensions(300, 80, 100, 26),

    "PAL_E": PackageDimensions(200, 80, 100, 20),

    "PAL_F": PackageDimensions(200, 100, 100, 20),

    "PAL_G": PackageDimensions(80, 60, 180, 12),

    "PAL_H": PackageDimensions(170, 80, 170, 26),

    "PAL_I": PackageDimensions(300, 120, 130, 32),

    "PAL_J": PackageDimensions(120, 120, 180, 22),

    "PAL_O": PackageDimensions(300, 40, 100, 28),

    "PAL_P": PackageDimensions(200, 40, 100, 18),

    "PAL_R": PackageDimensions(200, 50, 100, 18),

    "PAL_Y": PackageDimensions(80, 80, 120, 14),

}





def get_default_dimensions(ifs_pack_type: str) -> PackageDimensions | None:

    return _DEFAULT_DIMENSIONS.get(ifs_pack_type)





def is_pallet(ifs_pack_type: str) -> bool:

    return ifs_pack_type in _PALLET_TYPES or ifs_pack_type.startswith("PAL")





def resolve_carrier_pack_type(carrier_code: str, ifs_pack_type: str | None) -> str | None:

    if not ifs_pack_type:

        return None

    provider = CARRIER_ALIAS.get(carrier_code.upper(), carrier_code.lower())

    row = PACKAGING_MATRIX.get(ifs_pack_type)

    if not row:

        return ifs_pack_type

    return row.get(provider, ifs_pack_type)

