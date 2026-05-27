"""Telephony integration port — vendor-neutral call events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class CallEvent:
    """Normalized telephony webhook payload (e.g. Aircall `call.ended`)."""

    event: str
    provider: str
    call_id: str | None = None
    direction: str | None = None
    duration_sec: int | None = None
    from_number: str | None = None
    to_number: str | None = None
    res_model: str | None = None
    res_id: str | None = None
    summary: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def call_event_to_activity_body(event: CallEvent) -> dict[str, Any]:
    """Map a normalized call event to `log_telephony_call` body."""
    return {
        "name": "Call",
        "res_model": event.res_model,
        "res_id": event.res_id,
        "duration_sec": event.duration_sec,
        "summary": event.summary or "Phone call",
    }


@runtime_checkable
class TelephonyPort(Protocol):
    """Adapter boundary for inbound provider webhooks and outbound dial APIs."""

    def parse_webhook(self, provider: str, payload: dict[str, Any]) -> CallEvent | None:
        """Return a normalized event, or None when the payload is not handled."""
        ...
