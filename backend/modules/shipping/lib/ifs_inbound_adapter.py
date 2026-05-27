"""IFS inbound port implementation (shipping module)."""

from __future__ import annotations

from typing import Any

from orbiteus_core.ports.ifs_inbound import IfsInboundPort, IfsShipmentEvent

from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook


class ShippingIfsInboundAdapter:
    """Maps Oracle MS_INTEGRATION_API JSON → canonical logistics payload."""

    def parse_webhook(
        self,
        raw: dict[str, Any],
        *,
        ifs_sid: str = "UNKNOWN",
    ) -> IfsShipmentEvent:
        if raw.get("shipment_id") is None:
            raise ValueError("Missing shipment_id")
        logistics = build_logistics_payload_from_ifs_webhook(raw)
        return IfsShipmentEvent(
            shipment_id=str(raw["shipment_id"]),
            ifs_sid=ifs_sid,
            objstate=str(raw.get("objstate") or logistics.objstate or ""),
            raw=raw,
            logistics_payload=logistics.model_dump_json_ready(),
        )


def get_ifs_inbound_port() -> IfsInboundPort:
    return ShippingIfsInboundAdapter()
