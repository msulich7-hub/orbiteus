"""BYOK key storage with Fernet encryption (ADR-0004).

Public API:

    from orbiteus_core.ai.keys import store_credential, fetch_credential

Encryption key (`AI_SECRET_KEY`) lives in env, never in DB. Rotation requires
re-encrypting all existing rows — provide a CLI helper if needed.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    key = (settings.ai_secret_key or "").encode("utf-8")
    if not key or key == b"change-me-with-fernet-key":
        raise RuntimeError("AI_SECRET_KEY is unset; cannot read/write AI credentials")
    return Fernet(key)


def encrypt(secret: str) -> bytes:
    return _fernet().encrypt(secret.encode("utf-8"))


def decrypt(blob: bytes) -> str:
    try:
        return _fernet().decrypt(blob).decode("utf-8")
    except InvalidToken as exc:  # noqa: BLE001
        raise RuntimeError("AI credential decryption failed (bad AI_SECRET_KEY?)") from exc


async def store_credential(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    provider: str,
    secret: str,
    model_default: str | None = None,
    monthly_token_budget: int | None = None,
) -> uuid.UUID:
    from datetime import datetime, timezone

    from modules.base.model.mapping import ir_ai_credentials_table as t

    secret_enc = encrypt(secret)
    now = datetime.now(timezone.utc)

    existing = (
        await session.execute(
            select(t.c.id).where(t.c.tenant_id == tenant_id, t.c.provider == provider)
        )
    ).first()

    if existing is None:
        new_id = uuid.uuid4()
        await session.execute(
            insert(t).values(
                id=new_id,
                create_date=now,
                write_date=now,
                tenant_id=tenant_id,
                provider=provider,
                secret_encrypted=secret_enc,
                model_default=model_default,
                is_active=True,
                monthly_token_budget=monthly_token_budget,
                usage_tokens=0,
            )
        )
        return new_id

    await session.execute(
        update(t)
        .where(t.c.id == existing[0])
        .values(
            secret_encrypted=secret_enc,
            model_default=model_default,
            monthly_token_budget=monthly_token_budget,
            is_active=True,
            write_date=now,
        )
    )
    return existing[0]


async def fetch_credential(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    provider: str,
) -> dict[str, Any] | None:
    from modules.base.model.mapping import ir_ai_credentials_table as t

    row = (
        await session.execute(
            select(
                t.c.secret_encrypted,
                t.c.model_default,
                t.c.is_active,
                t.c.monthly_token_budget,
                t.c.usage_tokens,
            ).where(t.c.tenant_id == tenant_id, t.c.provider == provider)
        )
    ).first()
    if row is None:
        return None

    secret_enc, model_default, is_active, monthly_budget, usage = row
    if not is_active:
        return None
    return {
        "provider": provider,
        "secret": decrypt(secret_enc),
        "model_default": model_default,
        "monthly_token_budget": monthly_budget,
        "usage_tokens": usage,
    }
