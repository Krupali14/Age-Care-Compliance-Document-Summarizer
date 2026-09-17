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

# Words that name the event deadlines hang off — the incident itself.
_INCIDENT_TRIGGER_WORDS = frozenset(
    ("incident", "occurred", "occurring", "happened", "error", "fall", "fell", "discovered", "found", "identified")
)


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


def _sentence_with_date(sentences: list[str], date_text: str) -> str | None:
    """The sentence containing the date match, if any."""
    for sentence in sentences:
        if date_text in sentence:
            return sentence
    return None


def _time_from_sentence(text: str) -> time | None:
    """Extract a time from a single sentence, or None."""
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


def _sentence_with_trigger_word(sentences: list[str]) -> str | None:
    """The first sentence containing an incident trigger word, if any."""
    for sentence in sentences:
        lower_sentence = sentence.lower()
        for word in _INCIDENT_TRIGGER_WORDS:
            if re.search(rf"\b{word}\b", lower_sentence):
                return sentence
    return None


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

    # Split head into sentences on `.`, `!`, `?`, and newlines
    sentences = re.split(r'[.!?\n]+', head)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Try to find the date's original text to locate its sentence
    # Re-search for date patterns to find the actual matched text
    date_match = None
    for pattern in [
        re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b"),
        re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"),
        re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"),
        re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{4})\b"),
    ]:
        match = pattern.search(head)
        if match:
            date_match = match.group(0)
            break

    # Priority 1: Time in sentence with trigger word
    trigger_sentence = _sentence_with_trigger_word(sentences)
    if trigger_sentence:
        trigger_time = _time_from_sentence(trigger_sentence)
        if trigger_time:
            return datetime.combine(when, trigger_time), "stated"

    # Priority 2: Time in sentence with the date
    if date_match:
        date_sentence = _sentence_with_date(sentences, date_match)
        if date_sentence:
            date_time = _time_from_sentence(date_sentence)
            if date_time:
                return datetime.combine(when, date_time), "stated"

    # Priority 3: First time in the head
    first_time = _first_time_in(head)
    if first_time:
        return datetime.combine(when, first_time), "stated"

    # Priority 4: Midnight
    return datetime.combine(when, time(0, 0)), "stated"
