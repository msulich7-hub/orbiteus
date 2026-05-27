#!/usr/bin/env python
"""DPD native smoke — generate N waybill labels (default 9 = 3 sites × 3 parcel scenarios).

Usage (from crm-engine/backend):
  python scripts/dpd_orbiteus_smoke.py       # 9 labels
  python scripts/dpd_orbiteus_smoke.py 3     # quick: BIS/CIE/BAZ × scenario S only

Requires DPD_LOGIN, DPD_PASSWORD, DPD_MASTER_FID (DPD_ENV=test recommended).
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

# Allow `python scripts/dpd_orbiteus_smoke.py` from backend/
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.shipping.lib.adapters.dpd_adapter import DpdPythonAdapter, sender_from_ifs_contract


@dataclass(frozen=True)
class ParcelScenario:
    code: str
    weight: float
    length: float
    width: float
    height: float


SCENARIOS: tuple[ParcelScenario, ...] = (
    ParcelScenario("S", 5.5, 40, 30, 20),
    ParcelScenario("M", 15.0, 50, 40, 30),
    ParcelScenario("L", 31.0, 60, 40, 35),
)

SITES: tuple[tuple[str, str], ...] = (
    ("BIS", "BIS^01"),
    ("CIE", "CIE^01"),
    ("BAZ", "BAZ^01"),
)


def _build_matrix(count: int) -> list[tuple[str, str, ParcelScenario]]:
    full = [(site, contract, sc) for site, contract in SITES for sc in SCENARIOS]
    return full if count >= len(full) else full[: max(1, count)]


async def _run_one(
    adapter: DpdPythonAdapter,
    site: str,
    contract: str,
    scenario: ParcelScenario,
    stamp: str,
    index: int,
) -> tuple[bool, str, str | None]:
    order_no = f"ORB-DPD-{site}-{scenario.code}-{stamp}-{index:02d}"
    sender = sender_from_ifs_contract(contract)
    req_payload = {
        "reference": order_no,
        "contract": contract,
        "sender": None,
        "recipient": {
            "company_name": "Firma Testowa Sp. z o.o.",
            "first_name": "Jan",
            "last_name": "Kowalski",
            "address": "ul. Testowa 1",
            "zip": "02-274",
            "city": "Warszawa",
            "country": "PL",
            "phone": "+48123456789",
            "email": "test@example.com",
        },
        "parcels": [
            {
                "weight": scenario.weight,
                "length": scenario.length,
                "width": scenario.width,
                "height": scenario.height,
                "reference": scenario.code,
                "content": "Czesci zamienne - smoke DPD",
            }
        ],
        "goods_description": "Czesci zamienne - smoke DPD",
    }
    if sender:
        req_payload["sender"] = {
            "company_name": sender.company_name,
            "address": sender.address,
            "zip": sender.zip,
            "city": sender.city,
            "country": sender.country,
        }

    try:
        result = await adapter.create_label(req_payload)
        tracking = result.get("tracking_number") or ""
        label_b64 = result.get("label_base64")
        if label_b64 and tracking:
            out = Path(f"dpd-label-{tracking}.pdf")
            out.write_bytes(base64.b64decode(label_b64))
            return True, tracking, str(out)
        if tracking:
            return True, tracking, None
        return False, "no tracking", None
    except Exception as exc:
        return False, str(exc), None


async def main_async(count: int, delay_ms: int) -> int:
    matrix = _build_matrix(count)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    adapter = DpdPythonAdapter()
    ok_count = 0
    failures: list[str] = []

    print(f"[dpd-smoke] Running {len(matrix)} DPD label(s) (DPD_ENV={__import__('os').environ.get('DPD_ENV', 'test')})")

    for i, (site, contract, scenario) in enumerate(matrix, start=1):
        label = f"{site}/{scenario.code} ({scenario.weight}kg)"
        print(f"  [{i}/{len(matrix)}] {label} ... ", end="", flush=True)
        ok, detail, pdf = await _run_one(adapter, site, contract, scenario, stamp, i)
        if ok:
            ok_count += 1
            suffix = f" -> {pdf}" if pdf else ""
            print(f"OK {detail}{suffix}")
        else:
            print(f"FAIL {detail}")
            failures.append(f"{label}: {detail}")
        if i < len(matrix) and delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

    print(f"\n[dpd-smoke] Result: {ok_count}/{len(matrix)} OK")
    if failures:
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="DPD native label smoke test")
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=9,
        help="Number of labels (default 9 = 3 sites × 3 scenarios)",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=700,
        help="Delay between API calls (default 700)",
    )
    args = parser.parse_args()
    count = max(1, args.count)
    code = asyncio.run(main_async(count, args.delay_ms))
    sys.exit(code)


if __name__ == "__main__":
    main()
