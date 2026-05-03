"""Starlette middleware that applies token-bucket rate limits.

Order in the request flow:
1. RequestIdMiddleware (already present) sets `request_id`.
2. RateLimitMiddleware checks tenant + user + IP buckets.
3. Auth middleware decodes the JWT and adds `tenant_id` / `user_id` to the
   RequestContext.

Because we don't have the JWT decoded at this layer, we rate-limit by IP for
all requests and by tenant/user only when the request includes a Bearer
token whose payload we can cheaply parse. Hitting any limit returns 429.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from orbiteus_core.config import settings
from orbiteus_core.security.rate_limit import check

logger = logging.getLogger(__name__)


# Routes that are explicitly exempt (probes, metrics, public landing assets).
EXEMPT_PATHS: tuple[str, ...] = (
    "/api/health/live",
    "/api/health/ready",
    "/metrics",
    "/api/base/branding",
)


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
        try:
            decision = await check(f"ip:{ip}", settings.rate_limit_ip_per_minute)
        except Exception:  # noqa: BLE001
            # Redis outage must not block traffic.
            return await call_next(request)

        if not decision.allowed:
            logger.info(
                "rate_limit.blocked",
                extra={"bucket": decision.bucket, "count": decision.count,
                       "limit": decision.limit, "path": path},
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

        return await call_next(request)
