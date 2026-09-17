"""Turning a deadline's stated due date into a point in time, a bucket and a status.

Extraction stores `due_date` as the document writes it: either a calendar date
("2026-12-31") or a relative timeframe ("within 24 hours of the incident"). Neither
form can be sorted or filtered on as text, so everything is resolved here into one
`due_at` datetime plus the bucket it falls in.
"""

import re
from datetime import datetime, time, timedelta

from app.services.extraction import _latest_date_in

# Statuses a user can set on a deadline. Stored as plain strings.
STATUSES = ("not_started", "in_progress", "completed")
DEFAULT_STATUS = "not_started"

# Buckets, ordered from most to least urgent. "no_date" holds the relative
# timeframes whose trigger never happened and anything unparseable.
BUCKETS = ("overdue", "within_24_hours", "within_7_days", "within_30_days", "later", "no_date")

_UNITS = {
    "minute": timedelta(minutes=1),
    "min": timedelta(minutes=1),  # "30 mins"
    "hour": timedelta(hours=1),
    "hr": timedelta(hours=1),  # "48 hrs"
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "fortnight": timedelta(days=14),
    # ponytail: calendar months/years would need dateutil; these averages are close
    # enough for bucketing and sorting. Swap for relativedelta if exactness matters.
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}

# "within 30 days", "24 hours after the incident", "2 business days", "1 month",
# "within 30 minutes of the incident".
_RELATIVE = re.compile(
    r"\b(\d+)\s*(?:business|working|calendar)?\s*"
    r"(minutes?|mins?|hours?|hrs?|days?|weeks?|fortnights?|months?|years?)\b",
    re.IGNORECASE,
)


def parse_relative(value: str) -> timedelta | None:
    """The offset a relative timeframe names, or None if it names no timeframe.

    Several quantities in one phrase ("30 days and 4 hours") add up.
    """
    total = timedelta()
    for count, unit in _RELATIVE.findall(value):
        base = _UNITS.get(unit.lower().rstrip("s"))
        if base is not None:
            total += base * int(count)
    return total or None


def resolve_due_at(due_date: str | None, anchor: datetime) -> datetime | None:
    """The moment a deadline falls due.

    `anchor` is when the clock starts for a relative timeframe. The document never
    says when the incident it refers to happened, so the upload time stands in for
    it: a document uploaded at 2pm with a "within 4 hours" deadline is due at 6pm
    that day. A calendar date carries no time of day, so it falls due at the end of
    that day.
    """
    if not due_date or not due_date.strip():
        return None
    value = due_date.strip()
    try:
        return datetime.combine(datetime.fromisoformat(value).date(), time(23, 59, 59))
    except ValueError:
        pass
    when = _latest_date_in(value)
    if when is not None:
        return datetime.combine(when, time(23, 59, 59))
    offset = parse_relative(value)
    return anchor + offset if offset is not None else None


def bucket_for(due_at: datetime | None, now: datetime) -> str:
    """Which urgency bucket a due time falls in."""
    if due_at is None:
        return "no_date"
    remaining = due_at - now
    if remaining < timedelta(0):
        return "overdue"
    if remaining <= timedelta(hours=24):
        return "within_24_hours"
    if remaining <= timedelta(days=7):
        return "within_7_days"
    if remaining <= timedelta(days=30):
        return "within_30_days"
    return "later"
