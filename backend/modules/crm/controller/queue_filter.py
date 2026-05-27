"""Simple domain_json filter parser for crm.queue run (SPEC-007 v1)."""
from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Any

from orbiteus_core.context import RequestContext

from modules.crm.model.domain import Lead, Stage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lead_is_rotting(lead: Lead, stage: Stage | None, now: datetime | None = None) -> bool:
    """Match kanban / rotting endpoint logic."""
    from modules.crm.controller.services import evaluate_lead_rotting

    is_rotting, _, _ = evaluate_lead_rotting(lead, stage, now)
    return is_rotting


def _resolve_user_id(value: Any, ctx: RequestContext) -> uuid.UUID | None:
    if value in ("current_user", "$current_user"):
        return ctx.user_id
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _month_bounds(today: date) -> tuple[date, date]:
    last_day = monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


def matches_domain(
    lead: Lead,
    domain: dict,
    *,
    ctx: RequestContext,
    stage_by_id: dict[uuid.UUID, Stage],
    now: datetime | None = None,
) -> bool:
    """Apply domain_json keys. Unknown keys are ignored (v1)."""
    if not domain:
        return True
    if now is None:
        now = _utcnow()
    today = now.date()

    if "assigned_user_id" in domain:
        expected = _resolve_user_id(domain["assigned_user_id"], ctx)
        if expected is not None and lead.assigned_user_id != expected:
            return False

    if "stage_id" in domain:
        raw = domain["stage_id"]
        if isinstance(raw, list):
            allowed = {uuid.UUID(str(x)) for x in raw}
            if lead.stage_id not in allowed:
                return False
        else:
            if lead.stage_id != uuid.UUID(str(raw)):
                return False

    if "is_rotting" in domain:
        stage = stage_by_id.get(lead.stage_id) if lead.stage_id else None
        rotting = lead_is_rotting(lead, stage, now)
        want = bool(domain["is_rotting"])
        if rotting != want:
            return False

    if domain.get("expected_close_date__month") == "current":
        if lead.expected_close_date is None:
            return False
        start, end = _month_bounds(today)
        if not (start <= lead.expected_close_date <= end):
            return False

    inactive_days = domain.get("last_activity_at__inactive_days__gte")
    if inactive_days is not None:
        threshold = now - timedelta(days=int(inactive_days))
        if lead.last_activity_at is None:
            pass
        elif lead.last_activity_at > threshold:
            return False

    return True


def sort_leads(leads: list[dict], sort_json: dict) -> list[dict]:
    """Sort serialized lead rows by sort_json field/order."""
    if not sort_json:
        return leads
    field = sort_json.get("field", "name")
    order = sort_json.get("order", "asc")
    reverse = order == "desc"

    def key(row: dict) -> Any:
        val = row.get(field)
        if val is None:
            return (1, "")
        return (0, val)

    return sorted(leads, key=key, reverse=reverse)
