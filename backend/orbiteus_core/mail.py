"""Minimal transactional mailer (DoD §3.4 + §11.7).

Two modes, picked by `settings.smtp_host`:

  * **dev / CI** (`smtp_host == ""`):
      `send_mail(...)` logs the rendered message to stdout under the
      `mail` logger and returns immediately. Tests + the password-reset
      flow can assert on the log line without standing up an SMTP server.
  * **production** (`smtp_host` set):
      `send_mail(...)` opens an `aiosmtplib.SMTP` connection, optionally
      `STARTTLS`, optionally authenticates, and sends a multipart
      `text/plain` + `text/html` message.

The interface is deliberately small: a single coroutine that takes a
recipient + subject + body. Anything richer (templates, attachments,
queued retries) lives in higher layers (e.g. a future `mail` module
that schedules through Celery).

This is *not* an Odoo-style `mail.thread` — that primitive is
consciously deferred (see `docs/pre-prompt.md`, "Post-v1.0 roadmap").
"""
from __future__ import annotations

import logging
from email.message import EmailMessage

from orbiteus_core.config import settings

logger = logging.getLogger("mail")


async def send_mail(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
) -> None:
    """Send a transactional email.

    Errors are logged but never raised — a transient SMTP outage MUST
    NOT propagate as a 500 to the caller (e.g. password-reset request).
    """
    sender = from_address or settings.smtp_from_address

    if not settings.smtp_host:
        logger.info(
            "mail.dev_log to=%s subject=%r body=%r",
            to, subject, body_text,
        )
        return

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
            timeout=10.0,
        )
        logger.info("mail.sent to=%s subject=%r", to, subject)
    except Exception:  # noqa: BLE001
        logger.exception("mail.send_failed to=%s subject=%r", to, subject)
