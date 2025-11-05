from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Optional


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y/%-m/%-d",
    "%Y-%m-%dT%H:%M:%S",
]


def parse_any_date(value: str) -> date:
    last_error: Optional[Exception] = None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(f"Unsupported date format: {value}") from last_error


def month_start(d: date) -> date:
    return d.replace(day=1)


def month_end(d: date) -> date:
    """Return the last day of the month containing d."""
    ms = month_start(d)
    # next month start
    if ms.month == 12:
        next_ms = ms.replace(year=ms.year + 1, month=1)
    else:
        next_ms = ms.replace(month=ms.month + 1)
    return next_ms - timedelta(days=1)


def date_range(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def iso_week_bounds(d: date) -> tuple[date, date]:
    """Return (monday, sunday) for ISO week containing d."""
    weekday = d.isoweekday()  # 1=Mon .. 7=Sun
    monday = d - timedelta(days=weekday - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def build_weeks(end: date, n: int) -> list[tuple[date, date]]:
    """Build list of n ISO week ranges ending at week containing 'end'.
    Returns in ascending order (oldest week first).
    """
    latest_mon, latest_sun = iso_week_bounds(end)
    weeks: list[tuple[date, date]] = []
    cur_mon = latest_mon
    for _ in range(n):
        cur_sun = cur_mon + timedelta(days=6)
        weeks.append((cur_mon, cur_sun))
        cur_mon = cur_mon - timedelta(days=7)
    weeks.reverse()  # oldest first
    return weeks


def build_months(end: date, n: int) -> list[tuple[date, date, str]]:
    """Build list of n natural months ending at month containing 'end'.
    Returns list of (start_date, end_date, label_ym) oldest first.
    """
    # month containing end
    cur = end
    months: list[tuple[date, date, str]] = []
    for _ in range(n):
        ms = month_start(cur)
        me = month_end(cur)
        label = f"{ms.year:04d}-{ms.month:02d}"
        months.append((ms, me, label))
        # move to previous month
        if ms.month == 1:
            cur = ms.replace(year=ms.year - 1, month=12, day=15)
        else:
            cur = ms.replace(month=ms.month - 1, day=15)
    months.reverse()
    return months
