"""Mailbox integration port — vendor-neutral email events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class EmailMessage:
    """Normalized mailbox webhook payload (e.g. Gmail `email.received`)."""

    event: str
    provider: str
    message_id: str | None = None
    subject: str | None = None
    from_email: str | None = None
    to_email: str | None = None
    body: str | None = None
    res_model: str | None = None
    res_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def email_message_to_activity_body(message: EmailMessage) -> dict[str, Any]:
    """Map a normalized email event to `log_email_to_timeline` body."""
    return {
        "name": "Email",
        "res_model": message.res_model,
        "res_id": message.res_id,
        "subject": message.subject,
        "body": message.body or message.subject or "Email",
    }


@runtime_checkable
class MailboxPort(Protocol):
    """Adapter boundary for inbound provider webhooks and outbound send APIs."""

    def parse_webhook(self, provider: str, payload: dict[str, Any]) -> EmailMessage | None:
        """Return a normalized event, or None when the payload is not handled."""
        ...
