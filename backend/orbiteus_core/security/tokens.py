"""JWT token creation and validation.

PR 6 changes:
- Access TTL default 15 min (was 60). Configurable via env.
- Refresh TTL default 7 days (was 30). Configurable via env.
- Every token carries a `jti` (JWT ID) used by the Redis revocation list.
- Refresh tokens rotate on use — the old `jti` lands in the blacklist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from orbiteus_core.config import settings


def _new_jti() -> str:
    return uuid.uuid4().hex


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = dict(data)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload.setdefault("jti", _new_jti())
    payload["exp"] = expire
    payload["type"] = "access"
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    payload = dict(data)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload.setdefault("jti", _new_jti())
    payload["exp"] = expire
    payload["type"] = "refresh"
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            raise JWTError("Not an access token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def decode_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid refresh token: {e}") from e
