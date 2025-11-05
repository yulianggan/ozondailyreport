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


def date_range(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)

