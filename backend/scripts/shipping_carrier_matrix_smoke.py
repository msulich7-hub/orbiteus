#!/usr/bin/env python
"""Matrix smoke — N shipments per carrier (default 3 × MOCK, DPD, DSV, GEODIS).

Usage (from backend/):
  python scripts/shipping_carrier_matrix_smoke.py
  python scripts/shipping_carrier_matrix_smoke.py --per-carrier 3 --carriers MOCK,DPD
  python scripts/shipping_carrier_matrix_smoke.py --mock-only

Live carrier APIs require env from `.env.shipping.example` (DPD_*, DSV_*, GEODIS_*).
MOCK always runs without credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.shipping.lib.carrier_registry import adapter_for, normalize_carrier_code
from modules.shipping.lib.carrier_settings import get_carrier_settings


@dataclass(frozen=True)
class ShipmentScenario:
    code: str
    site: str
    contract: str
    weight: float
    length: float
    width: float
    height: float
    pack_type: str
    is_pallet: bool


DEFAULT_SCENARIOS: tuple[ShipmentScenario, ...] = (
    ShipmentScenario("S", "BIS", "BIS^01", 5.5, 40, 30, 20, "PACZKASTD", False),
    ShipmentScenario("M", "CIE", "CIE^01", 15.0, 50, 40, 30, "PACZKASTD", False),
    ShipmentScenario("L", "BAZ", "BAZ^01", 120.0, 120, 80, 150, "PAL_A", True),
)

DEFAULT_CARRIERS: tuple[str, ...] = ("MOCK", "DPD", "DSV", "GEODIS")


def _build_payload(carrier: str, scenario: ShipmentScenario, stamp: str, index: int) -> dict:
    order_no = f"ORB-{carrier}-{scenario.site}-{scenario.code}-{stamp}-{index:02d}"
    recipient = {
        "company_name": "Firma Testowa Sp. z o.o.",
        "first_name": "Jan",
        "last_name": "Kowalski",
        "address": "ul. Testowa 1",
        "zip": "02-274",
        "city": "Warszawa",
        "country": "PL",
        "phone": "+48123456789",
        "email": "test@example.com",
    }
    payload: dict = {
        "reference": order_no,
        "order_id": order_no,
        "carrier_code": carrier,
        "contract": scenario.contract,
        "weight_kg": scenario.weight,
        "is_pallet": scenario.is_pallet,
        "is_locker": False,
        "recipient": recipient,
        "parcels": [
            {
                "weight": scenario.weight,
                "length": scenario.length,
                "width": scenario.width,
                "height": scenario.height,
                "pack_type": scenario.pack_type,
                "reference": scenario.code,
                "content": f"Smoke {carrier} {scenario.code}",
            }
        ],
        "goods_description": f"Smoke matrix {carrier}",
    }
    if carrier == "DPD":
        from modules.shipping.lib.adapters.dpd_adapter import sender_from_ifs_contract

        sender = sender_from_ifs_contract(scenario.contract)
        if sender:
            payload["sender"] = {
                "company_name": sender.company_name,
                "address": sender.address,
                "zip": sender.zip,
                "city": sender.city,
                "country": sender.country,
            }
    return payload


async def _run_one(
    carrier: str,
    scenario: ShipmentScenario,
    stamp: str,
    index: int,
    out_dir: Path | None,
) -> tuple[bool, str, str | None]:
    cfg = get_carrier_settings()
    canonical = normalize_carrier_code(carrier)
    if canonical != "MOCK" and not cfg.carrier_configured(canonical):
        return False, "not configured (missing env)", None

    try:
        adapter = adapter_for(canonical)
    except NotImplementedError as exc:
        return False, str(exc), None

    payload = _build_payload(canonical, scenario, stamp, index)
    try:
        result = await adapter.create_label(payload)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None

    tracking = result.get("tracking_number") or ""
    label_b64 = result.get("label_base64")
    pdf_path: str | None = None
    if label_b64 and tracking and out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf = out_dir / f"{canonical}-{tracking}.pdf"
        pdf.write_bytes(base64.b64decode(label_b64))
        pdf_path = str(pdf)

    if tracking:
        return True, tracking, pdf_path
    return False, "no tracking_number in response", None


async def main_async(
    carriers: list[str],
    per_carrier: int,
    delay_ms: int,
    out_dir: Path | None,
) -> int:
    scenarios = list(DEFAULT_SCENARIOS)[: max(1, per_carrier)]
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    total = len(carriers) * len(scenarios)
    ok_count = 0
    failures: list[str] = []
    skipped = 0

    print(f"[shipping-matrix] {len(scenarios)} shipment(s) × {len(carriers)} carrier(s) = {total} runs")

    n = 0
    for carrier in carriers:
        canonical = normalize_carrier_code(carrier)
        print(f"\n=== {canonical} ===")
        for scenario in scenarios:
            n += 1
            label = f"{canonical}/{scenario.site}-{scenario.code} ({scenario.weight}kg)"
            print(f"  [{n}/{total}] {label} ... ", end="", flush=True)
            ok, detail, pdf = await _run_one(canonical, scenario, stamp, n, out_dir)
            if ok:
                ok_count += 1
                suffix = f" -> {pdf}" if pdf else ""
                print(f"OK {detail}{suffix}")
            elif "not configured" in detail:
                skipped += 1
                print(f"SKIP {detail}")
            else:
                print(f"FAIL {detail}")
                failures.append(f"{label}: {detail}")
            if delay_ms > 0 and n < total:
                await asyncio.sleep(delay_ms / 1000.0)

    attempted = total - skipped
    print(f"\n[shipping-matrix] OK {ok_count}/{attempted} (skipped {skipped} unconfigured)")
    if failures:
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0 if ok_count == attempted else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Shipping carrier matrix smoke (3× per carrier)")
    parser.add_argument(
        "--per-carrier",
        type=int,
        default=3,
        help="Shipments per carrier (max 3 scenarios defined; default 3)",
    )
    parser.add_argument(
        "--carriers",
        type=str,
        default=",".join(DEFAULT_CARRIERS),
        help="Comma-separated carrier codes (default MOCK,DPD,DSV,GEODIS)",
    )
    parser.add_argument(
        "--mock-only",
        action="store_true",
        help="Run MOCK only (CI-safe)",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=500,
        help="Delay between API calls",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Write label PDFs here when base64 returned",
    )
    args = parser.parse_args()

    carriers = ["MOCK"] if args.mock_only else [c.strip() for c in args.carriers.split(",") if c.strip()]
    code = asyncio.run(
        main_async(
            carriers=carriers,
            per_carrier=max(1, min(3, args.per_carrier)),
            delay_ms=args.delay_ms,
            out_dir=args.out_dir,
        )
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
