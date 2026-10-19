from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def add_business_days(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def estimated_arrival(
    eta_business_days: int,
    now: datetime | None = None,
    cutoff: time = time(15, 0),
    timezone_name: str = "Asia/Singapore",
) -> date:
    current = now or datetime.now(ZoneInfo(timezone_name))
    start = current.date()
    if current.weekday() >= 5 or current.time() >= cutoff:
        start = add_business_days(start, 1)
    return add_business_days(start, eta_business_days)


def meets_deadline(eta_business_days: int, deadline: date | None, now: datetime | None = None) -> bool:
    return deadline is None or estimated_arrival(eta_business_days, now=now) <= deadline

