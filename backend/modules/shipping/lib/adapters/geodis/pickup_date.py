"""Geodis pickup date — next Polish business day (geodis-pickup-date.ts)."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _is_polish_public_holiday(d: date) -> bool:
    if d.month == 1 and d.day in (1, 6):
        return True
    if d.month == 5 and d.day in (1, 3):
        return True
    if d.month == 8 and d.day == 15:
        return True
    if d.month == 11 and d.day in (1, 11):
        return True
    if d.month == 12 and d.day in (25, 26):
        return True
    east = _easter_sunday(d.year)
    if d in (east, east + timedelta(days=1), east + timedelta(days=60)):
        return True
    return False


def next_geodis_suggested_pickup_date(from_dt: datetime | None = None) -> str:
    d = (from_dt or datetime.now()).date() + timedelta(days=1)
    while d.weekday() >= 5 or _is_polish_public_holiday(d):
        d += timedelta(days=1)
    return d.isoformat()
