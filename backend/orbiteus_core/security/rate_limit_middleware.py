"""Starlette middleware that applies token-bucket rate limits.

Order in the request flow
-------------------------
1. RequestIdMiddleware sets `request_id`.
2. RateLimitMiddleware (this file) checks IP, then tenant + user buckets
   when an access token is present.
3. Auth middleware decodes the JWT and populates RequestContext.

Why three buckets?
------------------
* IP bucket (`rl:ip:<ip>`)
    Defends against attackers who lack a valid token (registration
    flooders, naive scanners). Default 120/min.
* User bucket (`rl:user:<user_id>`)
    Defends against a single account hammering the API (script
    misconfigured, runaway browser tab). Default 60/min.
* Tenant bucket (`rl:tenant:<tenant_id>`)
    Defends against an entire tenant exhausting shared infra. Default
    1000/min.

JWT decoding here is **best-effort**: a transient signature failure
must NOT block a request that auth would otherwise reject with a clean
401. So we catch broadly and fall through.

Limits return HTTP 429 with `Retry-After`. The first bucket that
trips is the one reported in the response body.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from orbiteus_core.config import settings
from orbiteus_core.security.rate_limit import RateDecision, check

logger = logging.getLogger(__name__)


# Routes that are explicitly exempt (probes, metrics, public landing assets).
EXEMPT_PATHS: tuple[str, ...] = (
    "/api/health/live",
    "/api/health/ready",
    "/metrics",
    "/api/base/branding",
)


def _denied(decision: RateDecision, path: str) -> JSONResponse:
    logger.info(
        "rate_limit.blocked",
        extra={
            "bucket": decision.bucket,
            "count": decision.count,
            "limit": decision.limit,
            "path": path,
        },
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "code": "rate_limit.exceeded",
            "bucket": decision.bucket,
        },
        headers={"Retry-After": str(decision.retry_after)},
    )


def _read_access_token(request: Request) -> str | None:
    """Pull the access token out of the Authorization header or the
    `orbiteus_token` cookie. Returns None when absent."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip() or None
    cookie = request.cookies.get("orbiteus_token")
    return cookie or None


def _peek_jwt_claims(token: str) -> tuple[str | None, str | None]:
    """Return ``(tenant_id, user_id)`` from a verified access token.

    Returns ``(None, None)`` when the token is missing, malformed,
    expired, of the wrong type, or fails signature verification. We
    deliberately re-use the canonical decoder so an attacker cannot
    avoid the user/tenant buckets simply by forging a token — it has
    to be a valid one signed by us, which means it's a real session
    we want to count.
    """
    try:
        from orbiteus_core.security.tokens import decode_access_token

        payload = decode_access_token(token)
        return payload.get("tenant_id"), payload.get("sub")
    except Exception:  # noqa: BLE001
        return None, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if any(path == ex or path.startswith(ex + "/") for ex in EXEMPT_PATHS):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"

        # 1) IP bucket — covers anonymous + authenticated traffic.
        try:
            ip_decision = await check(f"ip:{ip}", settings.rate_limit_ip_per_minute)
        except Exception:  # noqa: BLE001
            # Redis outage MUST NOT block traffic. The request still passes
            # through every other layer (auth, RBAC, etc.) so this is safe.
            return await call_next(request)

        if not ip_decision.allowed:
            return _denied(ip_decision, path)

        # 2) Token-derived buckets — only run when an access token is on
        #    the request. We never block on a JWT-decode failure; the
        #    auth layer downstream is the canonical 401 path.
        token = _read_access_token(request)
        if token:
            tenant_id, user_id = _peek_jwt_claims(token)

            if tenant_id:
                try:
                    t_decision = await check(
                        f"tenant:{tenant_id}", settings.rate_limit_tenant_per_minute,
                    )
                except Exception:  # noqa: BLE001
                    t_decision = None
                if t_decision is not None and not t_decision.allowed:
                    return _denied(t_decision, path)

            if user_id:
                try:
                    u_decision = await check(
                        f"user:{user_id}", settings.rate_limit_user_per_minute,
                    )
                except Exception:  # noqa: BLE001
                    u_decision = None
                if u_decision is not None and not u_decision.allowed:
                    return _denied(u_decision, path)

        return await call_next(request)
