"""IFS inbound integration port — vendor-neutral shipment events from Oracle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class IfsShipmentEvent:
    """Normalized IFS webhook payload (MS_INTEGRATION_API JSON)."""

    shipment_id: str
    ifs_sid: str
    objstate: str
    raw: dict[str, Any] = field(default_factory=dict)
    logistics_payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IfsInboundPort(Protocol):
    """Adapter boundary for Oracle UTL_HTTP shipment webhooks."""

    def parse_webhook(
        self,
        raw: dict[str, Any],
        *,
        ifs_sid: str = "UNKNOWN",
    ) -> IfsShipmentEvent:
        """Map raw JSON to normalized event + canonical logistics payload."""
        ...
