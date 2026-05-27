"""Tests for IFS CF$_ handling units parser and inbound mapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.shipping.lib.cf_handling_units_parser import (
    merge_ifs_payload_lines_with_cf_handling_units,
    normalize_cf_record,
    parse_cf_handling_units,
    parse_cf_logistics_metadata,
)
from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook
from modules.shipping.lib.ifs_packaging import get_default_dimensions, is_pallet, resolve_carrier_pack_type

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_cf_oracle_keys() -> None:
    norm = normalize_cf_record({"CF$_PACZKAASTD": 3, "CF$_P_D": 1})
    assert norm["cf_paczkaastd"] == 3
    assert norm["cf_p_d"] == 1


def test_parse_cf_p_a_to_pal_a() -> None:
    units = parse_cf_handling_units({"cf_p_a": 2})
    assert len(units) == 1
    assert units[0].pack_type == "PAL_A"
    assert units[0].type == "pallet"
    assert units[0].qty == 2


def test_cf_paczaanst_typo_alias() -> None:
    units = parse_cf_handling_units({"cf_paczaanst": 1})
    assert units[0].pack_type == "PACZKANST"


def test_merge_cf_when_lines_empty() -> None:
    merged = merge_ifs_payload_lines_with_cf_handling_units(
        [],
        {"cf_p_d": 1, "cf_paczkaastd": 2},
    )
    assert len(merged) == 3
    pack_types = {m["pack_type"] for m in merged}
    assert "PAL_D" in pack_types
    assert "PACZKASTD" in pack_types


def test_resolve_carrier_pack_type_pal_d_geodis() -> None:
    assert resolve_carrier_pack_type("GEODIS", "PAL_D") == "PAL3008"
    assert resolve_carrier_pack_type("DSV", "PAL_A") == "EP"


def test_is_pallet_and_dimensions() -> None:
    assert is_pallet("PAL_A")
    assert not is_pallet("PACZKASTD")
    dims = get_default_dimensions("PAL_D")
    assert dims is not None
    assert dims.length_cm == 300


def test_parse_cf_logistics_metadata() -> None:
    meta = parse_cf_logistics_metadata(
        {"cf_tk_waga_net_sum": 120.5, "cf_c_przewoznik": "GEODIS"}
    )
    assert meta.total_net_weight == 120.5
    assert meta.carrier_code == "GEODIS"


def test_ifs_inbound_port_parses_event() -> None:
    from modules.shipping.lib.ifs_inbound_adapter import ShippingIfsInboundAdapter

    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    event = ShippingIfsInboundAdapter().parse_webhook(raw, ifs_sid="TEST")
    assert event.shipment_id == "900123"
    assert event.ifs_sid == "TEST"
    assert "lines" in event.logistics_payload


def test_build_logistics_payload_from_fixture() -> None:
    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    payload = build_logistics_payload_from_ifs_webhook(raw)
    assert str(payload.shipment_id) == "900123"
    assert payload.dsv_pickup_location == "bazanowice"
    assert payload.sender is not None
    assert len(payload.lines) >= 3
    assert payload.total_weight_kg == 185.5
