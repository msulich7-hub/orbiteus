"""Mock carrier — dev/test (mercato mock-carrier-adapter)."""

from __future__ import annotations

import uuid


class MockCarrierAdapter:
    code = "MOCK"

    async def create_label(self, payload: dict) -> dict:
        ref = payload.get("reference") or payload.get("order_id") or "MOCK"
        return {
            "carrier_code": self.code,
            "tracking_number": f"MOCK-{uuid.uuid4().hex[:12].upper()}",
            "label_base64": None,
            "raw": {"mock": True, "reference": str(ref)},
        }
