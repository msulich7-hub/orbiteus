"""CRM forecast aggregation — weighted pipeline by close month (SPEC-010)."""
from __future__ import annotations

import calendar
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _month_label(d: date) -> str:
    return f"{_MONTH_NAMES[d.month - 1]} {d.year}"


def _iter_month_starts(start: date, end: date):
    current = _month_start(start)
    end_start = _month_start(end)
    while current <= end_start:
        yield current
        current = _next_month_start(current)


async def build_leads_forecast(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    pipeline_id: uuid.UUID | None = None,
    months_ahead: int = 6,
    assigned_user_id: uuid.UUID | None = None,
) -> dict:
    """Aggregate open leads into weighted revenue forecast by close month."""
    from modules.crm.controller.repositories import (
        LeadRepository,
        PipelineRepository,
        StageRepository,
    )

    pipeline_repo = PipelineRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)

    if pipeline_id is None:
        pipelines, _ = await pipeline_repo.search(limit=50)
        default = next((p for p in pipelines if p.is_default), None)
        if default:
            pipeline_id = default.id
        elif pipelines:
            pipeline_id = pipelines[0].id

    stages, _ = await stage_repo.search(limit=200)
    if pipeline_id:
        stages = [s for s in stages if s.pipeline_id == pipeline_id]

    open_stages = [s for s in stages if not s.is_won and not s.is_lost]
    stage_by_id = {s.id: s for s in open_stages}
    stage_order = sorted(open_stages, key=lambda s: s.sequence)

    today = date.today()
    range_end = _add_months(today, months_ahead)

    leads, _ = await lead_repo.search(limit=5000)
    if pipeline_id:
        leads = [lead for lead in leads if lead.pipeline_id == pipeline_id]
    if assigned_user_id:
        leads = [lead for lead in leads if lead.assigned_user_id == assigned_user_id]

    month_totals: dict[str, dict] = {}
    for month_start in _iter_month_starts(today, range_end):
        key = _month_key(month_start)
        month_totals[key] = {
            "month": key,
            "label": _month_label(month_start),
            "weighted_revenue": 0.0,
            "raw_revenue": 0.0,
            "deal_count": 0,
            "by_stage": defaultdict(lambda: {"weighted_revenue": 0.0, "deal_count": 0}),
        }

    total_weighted = 0.0
    total_raw = 0.0

    for lead in leads:
        close_date = lead.expected_close_date
        if close_date is None or close_date < today or close_date > range_end:
            continue
        if lead.stage_id is None:
            continue

        stage = stage_by_id.get(lead.stage_id)
        if stage is None:
            continue

        revenue = float(lead.expected_revenue or 0.0)
        weighted = revenue * float(stage.probability or 0.0) / 100.0
        month_key = _month_key(close_date)

        if month_key not in month_totals:
            continue

        bucket = month_totals[month_key]
        bucket["weighted_revenue"] += weighted
        bucket["raw_revenue"] += revenue
        bucket["deal_count"] += 1

        stage_bucket = bucket["by_stage"][stage.id]
        stage_bucket["weighted_revenue"] += weighted
        stage_bucket["deal_count"] += 1

        total_weighted += weighted
        total_raw += revenue

    months: list[dict] = []
    for month_start in _iter_month_starts(today, range_end):
        key = _month_key(month_start)
        bucket = month_totals[key]
        by_stage = []
        for stage in stage_order:
            stage_data = bucket["by_stage"].get(stage.id)
            if not stage_data or stage_data["deal_count"] == 0:
                continue
            by_stage.append({
                "stage_id": str(stage.id),
                "stage_name": stage.name,
                "weighted_revenue": round(stage_data["weighted_revenue"], 2),
                "deal_count": stage_data["deal_count"],
            })

        months.append({
            "month": bucket["month"],
            "label": bucket["label"],
            "weighted_revenue": round(bucket["weighted_revenue"], 2),
            "raw_revenue": round(bucket["raw_revenue"], 2),
            "deal_count": bucket["deal_count"],
            "by_stage": by_stage,
        })

    return {
        "pipeline_id": str(pipeline_id) if pipeline_id else None,
        "currency": "PLN",
        "months": months,
        "total_weighted": round(total_weighted, 2),
        "total_raw": round(total_raw, 2),
    }
