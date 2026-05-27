"""Call mercato-shipping-hub adapters (same TS code as production Mercato)."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    # .../Testorbiteka/crm-engine/backend/modules/shipping/lib/adapters/mercato_hub.py
    return Path(__file__).resolve().parents[6]


def _mercato_hub() -> Path:
    env = os.environ.get("MERCATO_SHIPPING_HUB")
    if env:
        return Path(env)
    root = _repo_root()
    return root.parent.parent / "mercato" / "modules" / "mercato-shipping-hub"


def _label_script() -> Path:
    return _repo_root() / "scripts" / "shipping-label-tests.mjs"


def request_label_sync(carrier_code: str, order_no: str) -> dict:
    hub = _mercato_hub()
    script = _label_script()
    if not hub.is_dir():
        raise RuntimeError(f"MERCATO_SHIPPING_HUB not found: {hub}")
    if not script.is_file():
        raise RuntimeError(f"Label script missing: {script}")

    env = os.environ.copy()
    env["MERCATO_SHIPPING_HUB"] = str(hub)
    proc = subprocess.run(
        ["npx", "tsx", str(_label_script().parent / "shipping-bridge-single.ts"), carrier_code.lower(), order_no],
        cwd=str(_mercato_hub()),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RuntimeError(err)
    return json.loads(proc.stdout.strip())


class MercatoHubAdapter:
    """Orbiteus adapter delegating to mercato-shipping-hub (no duplicate carrier logic)."""

    def __init__(self, code: str) -> None:
        self.code = code.upper()

    async def create_label(self, payload: dict) -> dict:
        order_no = payload.get("reference") or payload.get("order_id") or "ORB-LABEL"
        result = await asyncio.to_thread(
            request_label_sync,
            self.code,
            str(order_no),
        )
        label_url = result.get("labelUrl") or ""
        label_b64 = None
        if isinstance(label_url, str) and label_url.startswith("data:") and "," in label_url:
            label_b64 = label_url.split(",", 1)[1]
        return {
            "carrier_code": self.code,
            "tracking_number": result.get("trackingNumber") or result.get("shipmentId") or "",
            "shipment_id": result.get("shipmentId"),
            "label_base64": label_b64,
            "label_file": result.get("labelFile"),
            "raw": result,
        }
