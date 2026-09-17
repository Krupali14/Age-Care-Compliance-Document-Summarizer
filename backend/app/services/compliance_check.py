"""Checking a case-study document against a compliance document's requirements.

The compliance document supplies the requirements; the case study is the evidence.
Every obligation and deadline the compliance document carries gets one verdict, and
deadlines are resolved against the moment the case study says the incident happened.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, field_validator

from app.database import SessionLocal
from app.models import CheckFinding, ComplianceCheck, Deadline, Obligation
from app.services.deadlines import bucket_for, resolve_due_at
from app.services.docling_parser import parse_document
from app.services.extraction import _latest_date_in
from app.services.llm import get_llm
from app.services.retrieval import rank

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


def _sentence_with_date(sentences: list[str]) -> str | None:
    """The first sentence containing a calendar date, if any."""
    for sentence in sentences:
        if _latest_date_in(sentence):
            return sentence
    return None


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

    # Split head into sentences where a terminator is followed by whitespace or end.
    # Times are written "3.10pm" in these documents, so a bare "." is not a sentence boundary.
    sentences = re.split(r"(?<=[.!?])\s+|\n+", head)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Priority 1: Time in sentence with trigger word
    trigger_sentence = _sentence_with_trigger_word(sentences)
    if trigger_sentence:
        trigger_time = _first_time_in(trigger_sentence)
        if trigger_time:
            return datetime.combine(when, trigger_time), "stated"

    # Priority 2: Time in sentence with the date
    date_sentence = _sentence_with_date(sentences)
    if date_sentence:
        date_time = _first_time_in(date_sentence)
        if date_time:
            return datetime.combine(when, date_time), "stated"

    # Priority 3: First time in the head
    first_time = _first_time_in(head)
    if first_time:
        return datetime.combine(when, first_time), "stated"

    # Priority 4: Midnight
    return datetime.combine(when, time(0, 0)), "stated"


# A case study that fits in this many characters is sent whole — an incident record
# normally does, and whole text beats retrieved passages when it is affordable.
# Past it, the batch gets the passages that match its requirements instead.
MAX_WHOLE_EVIDENCE_CHARS = 12000
EVIDENCE_TOP_K = 6
# Matching extraction's batching: the response carries one verdict per requirement,
# and a batch that overruns the output-token limit loses the whole call.
MAX_BATCH_REQUIREMENTS = 8


@dataclass
class Requirement:
    """One thing the compliance document requires, as handed to the check."""

    kind: str  # "obligation" | "deadline"
    source_id: int
    section_id: int | None
    text: str
    due_date: str | None


def load_requirements(document_id: int, db) -> list[Requirement]:
    out = [
        Requirement("obligation", row.id, row.section_id, row.text, None)
        for row in db.query(Obligation).filter(Obligation.document_id == document_id)
    ]
    out += [
        Requirement("deadline", row.id, row.section_id, row.description, row.due_date)
        for row in db.query(Deadline).filter(Deadline.document_id == document_id)
    ]
    return out


# Fallback chunk size when a case study has no line breaks to split on at all
# (OCR output, or text pasted as one block) — still small enough for rank() to
# tell one chunk from another.
_CHUNK_CHARS = 1500


def select_evidence(query: str, evidence_text: str) -> str:
    """The part of the case study this batch should be judged against."""
    if len(evidence_text) <= MAX_WHOLE_EVIDENCE_CHARS:
        return evidence_text
    paragraphs = [p.strip() for p in evidence_text.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        paragraphs = [p.strip() for p in evidence_text.split("\n") if p.strip()]
    if len(paragraphs) < 2:
        # A case study with no paragraph breaks still has to be bounded, or the
        # cap above means nothing — chunk it so there is something to rank.
        paragraphs = [
            evidence_text[i : i + _CHUNK_CHARS] for i in range(0, len(evidence_text), _CHUNK_CHARS)
        ]
    best = rank(query, paragraphs)[:EVIDENCE_TOP_K]
    # Kept in document order: a case study is a narrative, and passages shuffled
    # into relevance order read as a different sequence of events.
    selected = "\n\n".join(paragraphs[i] for i in sorted(best))
    # The backstop: whatever shape the text was split into, the result sent to
    # the prompt never exceeds the cap this function exists to enforce.
    return selected[:MAX_WHOLE_EVIDENCE_CHARS]


class CheckVerdict(BaseModel):
    index: int
    verdict: Literal["done", "not_done", "partly", "unclear"]
    evidence: str | None = None
    note: str

    @field_validator("evidence", mode="before")
    @classmethod
    def _coerce_evidence(cls, value: object) -> object:
        """The model sometimes writes the word "null" (or "none", "n/a") instead of
        the JSON value the schema asks for — the schema accepts any string, so
        nothing rejects it. Left alone, a finding with no evidence renders a
        blockquote reading "null" as though it were a quoted sentence from the
        case study."""
        if isinstance(value, str) and value.strip().lower() in ("", "null", "none", "n/a"):
            return None
        return value


class CheckBatch(BaseModel):
    verdicts: list[CheckVerdict]


CHECK_PROMPT = """You are auditing one organisation's record of what it did against \
the requirements of a compliance document.

The EVIDENCE below is the organisation's own account — an incident record, a case \
study, or a file note. The REQUIREMENTS are drawn from the compliance document.

For EACH requirement, return an object carrying that requirement's "index" and:
- "verdict": one of
  - "done" — the evidence shows this requirement was met
  - "partly" — some of it was met, or it was met late or incompletely
  - "not_done" — the evidence shows it was not met, or shows an action that \
contradicts it
  - "unclear" — the evidence does not say either way
- "evidence": the sentence from the EVIDENCE that supports your verdict, quoted \
exactly, or null when there is none
- "note": one sentence explaining the verdict, addressed to the user

Judge only from the EVIDENCE. Do not assume a requirement was met because it is \
routine, standard practice, or something the organisation would normally do. \
"unclear" is the correct answer whenever the evidence is silent — it is not a \
failure, and reporting silence as "not_done" would accuse the organisation of \
something this document does not show.

EVIDENCE:
{evidence}

REQUIREMENTS:
{requirements}"""


def _render_requirements(batch: list[Requirement]) -> str:
    lines = []
    for i, req in enumerate(batch):
        due = f" (due: {req.due_date})" if req.due_date else ""
        lines.append(f"--- Requirement index {i} ---\n{req.kind}: {req.text}{due}")
    return "\n\n".join(lines)


def _verdicts_for(batch: list[Requirement], evidence_text: str) -> dict[int, CheckVerdict]:
    """One model call for one batch; an empty dict when the call cannot be trusted."""
    query = " ".join(req.text for req in batch)
    prompt = CHECK_PROMPT.format(
        evidence=select_evidence(query, evidence_text),
        requirements=_render_requirements(batch),
    )
    structured = get_llm().with_structured_output(CheckBatch, method="json_schema")
    try:
        result = structured.invoke(prompt)
    except Exception:  # noqa: BLE001 - any provider failure looks the same here
        logger.exception("Compliance check batch failed for %s requirements", len(batch))
        return {}
    out: dict[int, CheckVerdict] = {}
    for item in result.verdicts:
        # An index the model invented or returned twice cannot be matched to a
        # requirement; dropping it leaves that requirement "unclear" rather than
        # filing another requirement's verdict against it.
        if 0 <= item.index < len(batch) and item.index not in out:
            out[item.index] = item
    return out


def run_check(check_id: int, file_path: str) -> None:
    """Background task: parse the case study, judge every requirement, store findings."""
    # ponytail: no db.close() — same as process_document, whose comment explains why.
    db = SessionLocal()
    try:
        check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    except Exception:  # noqa: BLE001 - never let a background task crash the caller
        logger.exception("Failed to fetch ComplianceCheck id=%s", check_id)
        return
    if check is None:
        return
    check.status = "processing"
    db.commit()

    try:
        sections = parse_document(file_path)
    except Exception:  # noqa: BLE001 - unrecoverable parse failure
        logger.exception("Failed to parse case study for check id=%s at %s", check_id, file_path)
        check.status = "failed"
        check.error_message = (
            "This file could not be read. It may be corrupt, password-protected, or "
            "saved in an unsupported format."
        )
        db.commit()
        return

    evidence_text = "\n\n".join(
        f"{s.heading}\n{s.raw_text}" if s.heading else s.raw_text for s in sections
    ).strip()
    if not evidence_text:
        check.status = "failed"
        check.error_message = "This document has no readable text to check against."
        db.commit()
        return

    # Everything past this point can fail in ways the two guards above can't
    # anticipate (a database error on commit, a bad row, an unexpected value in
    # resolution). Without one catch-all here, that failure escapes the background
    # task and strands the check in "processing" forever — the UI polls that status,
    # so the user is left watching a spinner with no way out.
    try:
        check.evidence_text = evidence_text
        check.incident_at, check.incident_source = find_incident_datetime(
            evidence_text, check.uploaded_at or datetime.utcnow()
        )
        db.commit()

        requirements = load_requirements(check.document_id, db)
        if not requirements:
            check.status = "failed"
            check.error_message = (
                "This compliance document has no obligations or deadlines to check against yet."
            )
            db.commit()
            return

        now = datetime.utcnow()
        for start in range(0, len(requirements), MAX_BATCH_REQUIREMENTS):
            batch = requirements[start : start + MAX_BATCH_REQUIREMENTS]
            verdicts = _verdicts_for(batch, evidence_text)
            for i, req in enumerate(batch):
                verdict = verdicts.get(i)
                due_at = resolve_due_at(req.due_date, check.incident_at) if req.kind == "deadline" else None
                db.add(CheckFinding(
                    check_id=check.id,
                    kind=req.kind,
                    source_id=req.source_id,
                    section_id=req.section_id,
                    requirement=req.text,
                    # A batch the model failed to answer leaves its requirements
                    # unjudged. That is "unclear", not "not_done" — the difference
                    # between "we have no answer" and "you did not do it".
                    verdict=verdict.verdict if verdict else "unclear",
                    evidence=verdict.evidence if verdict else None,
                    note=verdict.note if verdict else "The check could not reach a verdict for this requirement.",
                    due_at=due_at,
                    bucket=bucket_for(due_at, now) if req.kind == "deadline" else None,
                ))
            db.commit()

        check.status = "done"
        db.commit()
    except Exception:  # noqa: BLE001 - never let a background task crash the caller
        logger.exception("Compliance check id=%s failed after parsing", check_id)
        # The exception that lands here is often a failed commit or flush, which
        # leaves the session inactive — writing the failure status without rolling
        # back first raises PendingRollbackError on top of the original error,
        # right back into the "stuck in processing" state this handler exists to
        # prevent. The rollback itself can fail too (e.g. the connection is gone),
        # and that must not become the thing that escapes instead.
        try:
            db.rollback()
        except Exception:  # noqa: BLE001 - a dead connection can't be rolled back either
            logger.debug("Rollback failed for compliance check id=%s", check_id, exc_info=True)
        check.status = "failed"
        check.error_message = "This check could not be completed. Try uploading the case study again."
        db.commit()
