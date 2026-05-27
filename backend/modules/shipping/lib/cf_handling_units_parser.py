"""CF$_ → handling units — port of mercato ifs_bridge cf-handling-units-parser.ts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from modules.shipping.lib.ifs_packaging import get_default_dimensions

HandlingUnitType = Literal["pallet", "parcel"]


@dataclass
class HandlingUnit:
    pack_type: str
    type: HandlingUnitType
    qty: int
    weight_kg: float | None
    length_cm: float
    width_cm: float
    height_cm: float


@dataclass
class CfLogisticsMetadata:
    carrier_code: str | None
    tracking_number: str | None
    customer_order_no: str | None
    logistics_notes: str | None
    is_vip: bool
    total_net_weight: float | None
    packing_date: str | None
    coordinator: str | None
    packer: str | None
    invoice_no: str | None
    email_notification: bool


CF_PALLET_MAP: dict[str, str] = {
    "cf_p_a": "PAL_A",
    "cf_p_b": "PAL_B",
    "cf_p_c": "PAL_C",
    "cf_p_d": "PAL_D",
    "cf_p_e": "PAL_E",
    "cf_p_f": "PAL_F",
    "cf_p_g": "PAL_G",
    "cf_p_h": "PAL_H",
    "cf_p_i": "PAL_I",
    "cf_p_j": "PAL_J",
    "cf_p_o": "PAL_O",
    "cf_p_p": "PAL_P",
    "cf_p_r": "PAL_R",
    "cf_p_y": "PAL_Y",
    "cf_paleta_a": "PAL_A",
    "cf_paleta_b": "PAL_B",
    "cf_paleta_c": "PAL_C",
    "cf_paleta_d": "PAL_D",
    "cf_paleta_e": "PAL_E",
    "cf_paleta_f": "PAL_F",
    "cf_paleta_g": "PAL_G",
    "cf_paleta_h": "PAL_H",
    "cf_paleta_i": "PAL_I",
    "cf_paleta_j": "PAL_J",
    "cf_paleta_o": "PAL_O",
    "cf_paleta_p": "PAL_P",
    "cf_paleta_r": "PAL_R",
    "cf_paleta_y": "PAL_Y",
}

CF_PARCEL_MAP: dict[str, str] = {
    "cf_paczkaastd": "PACZKASTD",
    "cf_paczkastd": "PACZKASTD",
    "cf_paczkaanst": "PACZKANST",
    "cf_paczaanst": "PACZKANST",
    "cf_dluzycaa": "DLUZYCA",
    "cf_dluzyca": "DLUZYCA",
}


def _parse_qty(val: Any) -> int:
    if val is None:
        return 0
    try:
        n = float(val) if not isinstance(val, (int, float)) else val
    except (TypeError, ValueError):
        return 0
    if n > 0:
        return int(n)
    return 0


def normalize_cf_record(cf: dict[str, Any]) -> dict[str, Any]:
    """MS_INTEGRATION_API: ``CF$_PACZKAASTD`` → ``cf_paczkaastd``."""
    out: dict[str, Any] = {}
    for raw_key, val in cf.items():
        norm = raw_key.strip().lower().replace("$", "")
        if norm not in out:
            out[norm] = val
    return out


def parse_cf_handling_units(cf: dict[str, Any]) -> list[HandlingUnit]:
    norm = normalize_cf_record(cf)
    units: list[HandlingUnit] = []

    for cf_key, pack_type in CF_PALLET_MAP.items():
        qty = _parse_qty(norm.get(cf_key))
        if qty == 0:
            continue
        dims = get_default_dimensions(pack_type)
        units.append(
            HandlingUnit(
                pack_type=pack_type,
                type="pallet",
                qty=qty,
                weight_kg=dims.weight_kg if dims else None,
                length_cm=dims.length_cm if dims else 120.0,
                width_cm=dims.width_cm if dims else 80.0,
                height_cm=dims.height_cm if dims else 150.0,
            )
        )

    for cf_key, pack_type in CF_PARCEL_MAP.items():
        qty = _parse_qty(norm.get(cf_key))
        if qty == 0:
            continue
        dims = get_default_dimensions(pack_type)
        units.append(
            HandlingUnit(
                pack_type=pack_type,
                type="parcel",
                qty=qty,
                weight_kg=dims.weight_kg if dims else None,
                length_cm=dims.length_cm if dims else 40.0,
                width_cm=dims.width_cm if dims else 40.0,
                height_cm=dims.height_cm if dims else 100.0,
            )
        )

    return units


def expand_handling_units_to_lines(
    units: list[HandlingUnit],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    line_no = 1
    for unit in units:
        for _ in range(unit.qty):
            lines.append(
                {
                    "line_no": line_no,
                    "pack_type": unit.pack_type,
                    "type": unit.type,
                    "qty": 1,
                    "weight_kg": unit.weight_kg,
                    "length_cm": unit.length_cm,
                    "width_cm": unit.width_cm,
                    "height_cm": unit.height_cm,
                }
            )
            line_no += 1
    return lines


def merge_ifs_payload_lines_with_cf_handling_units(
    lines: list[dict[str, Any]] | None,
    custom_fields: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    cf = custom_fields if isinstance(custom_fields, dict) else None
    cf_handling_units = parse_cf_handling_units(cf) if cf else []

    ifs_lines: list[dict[str, Any]] = []
    for i, row in enumerate(lines or []):
        ifs_lines.append(
            {
                "line_no": i + 1,
                "catalog_no": row.get("catalog_no"),
                "catalog_desc": row.get("catalog_desc"),
                "qty": row.get("qty") or row.get("qty_to_ship") or row.get("sales_qty") or 1,
                "weight_kg": row.get("weight_kg") or row.get("weight"),
                "pack_type": row.get("pack_type") or row.get("packType"),
                "type": row.get("type"),
                "length_cm": row.get("length_cm"),
                "width_cm": row.get("width_cm"),
                "height_cm": row.get("height_cm"),
            }
        )

    has_pack_type = any(
        l.get("pack_type") not in (None, "") for l in ifs_lines
    )

    if cf_handling_units and not has_pack_type:
        expanded = expand_handling_units_to_lines(cf_handling_units)
        return [
            {
                "line_no": l["line_no"],
                "catalog_no": None,
                "catalog_desc": None,
                "qty": l["qty"],
                "weight_kg": l["weight_kg"],
                "pack_type": l["pack_type"],
                "type": l["type"],
                "length_cm": l["length_cm"],
                "width_cm": l["width_cm"],
                "height_cm": l["height_cm"],
            }
            for l in expanded
        ]

    if cf_handling_units and has_pack_type:
        expanded = expand_handling_units_to_lines(cf_handling_units)
        base = len(ifs_lines)
        return ifs_lines + [
            {
                "line_no": base + l["line_no"],
                "catalog_no": None,
                "catalog_desc": None,
                "qty": l["qty"],
                "weight_kg": l["weight_kg"],
                "pack_type": l["pack_type"],
                "type": l["type"],
                "length_cm": l["length_cm"],
                "width_cm": l["width_cm"],
                "height_cm": l["height_cm"],
            }
            for l in expanded
        ]

    return ifs_lines


def parse_cf_logistics_metadata(cf: dict[str, Any]) -> CfLogisticsMetadata:
    norm = normalize_cf_record(cf)

    def _str(key: str) -> str | None:
        v = norm.get(key)
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    def _num(key: str) -> float | None:
        v = norm.get(key)
        if v is None:
            return None
        try:
            n = float(v) if not isinstance(v, (int, float)) else float(v)
        except (TypeError, ValueError):
            return None
        return n if n == n else None  # noqa: PLR0124 — reject NaN

    vip = _str("cf_tk_vip_db")
    email = _str("cf_tk_potw_email_db")
    return CfLogisticsMetadata(
        carrier_code=_str("cf_c_przewoznik"),
        tracking_number=_str("cf_tk_nr_listu"),
        customer_order_no=_str("cf_tk_nr_zam_kli"),
        logistics_notes=_str("cf_tk_uwagi_log"),
        is_vip=vip in ("TRUE", "Y"),
        total_net_weight=_num("cf_tk_waga_net_sum"),
        packing_date=_str("cf_data_pak"),
        coordinator=_str("cf_koordinator"),
        packer=_str("cf_ubda_pakowacz"),
        invoice_no=_str("cf_pb_nr_fak"),
        email_notification=email in ("TRUE", "Y"),
    )
