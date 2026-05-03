"""Prometheus metrics primitives.

Exposed at `/metrics`. Registered globally so multiple workers can share the
same scrape endpoint shape (label sets are stable).
"""
from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Series declared in docs/29-observability.md
# ---------------------------------------------------------------------------

request_count = Counter(
    "orbiteus_http_requests_total",
    "Total HTTP requests served",
    labelnames=("method", "route", "status"),
)

request_duration = Histogram(
    "orbiteus_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


async def metrics_endpoint() -> Response:
    """Return the Prometheus exposition format payload."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
