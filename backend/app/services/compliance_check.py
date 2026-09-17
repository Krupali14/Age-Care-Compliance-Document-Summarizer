"""Checking a case-study document against a compliance document's requirements.

The compliance document supplies the requirements; the case study is the evidence.
Every obligation and deadline the compliance document carries gets one verdict, and
deadlines are resolved against the moment the case study says the incident happened.
"""

import logging
import re
from datetime import datetime, time

from app.services.extraction import _latest_date_in

logger = logging.getLogger(__name__)

# "3:10pm", "3.10 pm", "15:10", "3pm". The hour alone is only taken when it carries
# am/pm — a bare "15" in a sentence is a quantity, not a time.
_TIME = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)\b|\b([01]?\d|2[0-3]):([0-5]\d)\b",
    re.IGNORECASE,
)

# How far into the document to look. An incident record states when it happened in
# its opening lines; a mention 20 pages later is a cross-reference to another event.
INCIDENT_SCAN_CHARS = 3000


def _first_time_in(text: str) -> time | None:
    match = _TIME.search(text)
    if match is None:
        return None
    if match.group(3):  # 12-hour form
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or 0)
        if match.group(3).lower() == "pm":
            hour += 12
        return time(hour, minute)
    return time(int(match.group(4)), int(match.group(5)))


def find_incident_datetime(text: str, fallback: datetime) -> tuple[datetime, str]:
    """When the incident happened, and whether the document said so.

    A relative deadline ("within 24 hours of the incident") is meaningless until the
    incident has a time. Where the case study states one, that is the clock; where it
    does not, the upload time stands in and the caller is told so, rather than the
    report implying a precision it does not have.
    """
    head = text[:INCIDENT_SCAN_CHARS]
    when = _latest_date_in(head)
    if when is None:
        return fallback, "upload_time"
    return datetime.combine(when, _first_time_in(head) or time(0, 0)), "stated"
