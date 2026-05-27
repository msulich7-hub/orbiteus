"""Public IFS webhook — mounted under /api/shipping/ifs (Orbiteus module prefix).

Legacy alias: /api/ifs/webhook/shipment (api.py) for Oracle URLs already configured.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.db import get_session

from modules.shipping.controller.services import ingest_ifs_webhook
from modules.shipping.lib.carrier_settings import get_carrier_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shipping-ifs-webhook"])


def _verify_client_ip(request: Request) -> None:
    cfg = get_carrier_settings()
    allowlist = (cfg.ifs_webhook_allowlist or "").strip()
    if not allowlist:
        return
    client_host = request.client.host if request.client else ""
    allowed = {ip.strip() for ip in allowlist.split(",") if ip.strip()}
    if client_host not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client IP not allowed for IFS webhook",
        )


def _verify_webhook_secret(request: Request, raw_body: bytes) -> None:
    cfg = get_carrier_settings()
    secret = (cfg.ifs_webhook_secret or "").strip()
    if not secret:
        return
    sig = (
        request.headers.get("x-om-signature")
        or request.headers.get("x-ifs-signature")
        or ""
    ).strip()
    if not sig:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected) and not hmac.compare_digest(sig, f"sha256={expected}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


@router.post("/webhook/shipment", status_code=status.HTTP_202_ACCEPTED)
async def ifs_shipment_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Receive shipment from IFS (UTL_HTTP). No JWT — LAN + optional HMAC."""
    cfg = get_carrier_settings()
    if not cfg.ifs_webhook_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="IFS webhook disabled")

    _verify_client_ip(request)
    raw_body = await request.body()
    _verify_webhook_secret(request, raw_body)

    try:
        raw: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body") from exc

    if raw.get("shipment_id") is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing shipment_id")

    ifs_sid = request.headers.get("x-ifs-sid") or "UNKNOWN"
    request_id = request.headers.get("x-request-id")

    try:
        row = await ingest_ifs_webhook(
            session,
            raw,
            ifs_sid=ifs_sid,
            request_id=request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("IFS webhook ingest failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    await session.commit()

    logger.info(
        "IFS webhook queued shipment_id=%s sid=%s tenant=%s",
        row.ifs_shipment_id,
        row.ifs_sid,
        row.tenant_id,
    )

    return {
        "ok": True,
        "shipment_id": row.ifs_shipment_id,
        "queue_id": str(row.id),
        "state": row.state,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "received_at": row.create_date.isoformat() if row.create_date else None,
    }
