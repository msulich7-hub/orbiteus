"""DSV pickup window — next business day 09:00–17:00 (dsv-carrier.ts)."""

from __future__ import annotations

from datetime import datetime, timedelta


def next_dsv_pickup_window(from_dt: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (pickup_start, pickup_end) for next business day, skipping weekends."""
    base = from_dt or datetime.now()
    pickup = base.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    dow = pickup.weekday()
    if dow == 6:  # Sunday
        pickup += timedelta(days=1)
    elif dow == 5:  # Saturday
        pickup += timedelta(days=2)
    pickup_end = pickup.replace(hour=17, minute=0, second=0, microsecond=0)
    return pickup, pickup_end
