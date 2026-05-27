"""Smoke test IFS webhook route (mapping only, no DB)."""

from __future__ import annotations

import json
from pathlib import Path

from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook

FIXTURES = Path(__file__).parent / "fixtures"


def test_webhook_payload_maps_to_logistics() -> None:
    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    payload = build_logistics_payload_from_ifs_webhook(raw)
    assert payload.destination.city == "Warszawa"
    assert payload.handling_units_summary is not None
    assert len(payload.lines) >= 1
