import logging
import os
from concurrent.futures import ThreadPoolExecutor

from app.database import SessionLocal
from app.models import ActionItem, Deadline, Document, Obligation, Risk, Section, Summary
from app.services.docling_parser import ParsedSection, parse_document
from app.services.extraction import (
    SectionExtraction,
    check_relevance,
    extract_batch,
    plan_batches,
)

logger = logging.getLogger(__name__)

RETRY_BATCH_SIZES = (4, 1)

# A parsed "section" this short is a table-of-contents fragment or a stray page
# number ("ii Aged Care Act 2024", "system 77"), not content. Sending one to the
# model wastes a slot and invites it to invent a summary from the heading alone.
# The row is still stored, so the document reads complete; it just isn't extracted.
EXTRACTABLE_MIN_CHARS = 40


def process_document(document_id: int, file_path: str) -> None:
    # ponytail: no db.close() here — SessionLocal() gives each real call its own
    # session that FastAPI's background-task process just garbage-collects; tests
    # patch SessionLocal to hand back a shared session for assertions, and closing
    # it would expunge objects out from under those assertions.
    db = SessionLocal()

    # ponytail: this runs as a FastAPI BackgroundTasks callback fired after the
    # response is sent — an unhandled exception here must not escape and blow up
    # the request cycle, so fetching the row is guarded too (e.g. row not visible
    # yet/at all on this connection, id doesn't exist, DB unreachable).
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
    except Exception:  # noqa: BLE001 - never let a background task crash the caller
        logger.exception("Failed to fetch Document id=%s in background processing", document_id)
        return
    if document is None:
        return
    document.status = "processing"
    db.commit()

    try:
        parsed_sections = parse_document(file_path)
    except Exception:  # noqa: BLE001 - unrecoverable parse failure
        # The parser's own message names internal paths and library internals
        # ("File format not allowed: 19_report.pdf"), which tells a user nothing and
        # exposes how files are stored. The detail belongs in the log; the row gets
        # something a person can act on.
        logger.exception("Failed to parse document id=%s at %s", document.id, file_path)
        document.status = "failed"
        document.error_message = (
            "This file could not be read. It may be corrupt, password-protected, or "
            "saved in an unsupported format."
        )
        db.commit()
        return

    # Gate before spending any extraction calls: an out-of-scope upload should
    # come back as one warning, not a page of invented obligations and risks.
    try:
        relevance = check_relevance(document.filename, parsed_sections)
    except Exception:  # noqa: BLE001 - a failed gate must not block a valid document
        logger.exception("Relevance check failed for document id=%s", document.id)
        relevance = None
    if relevance is not None and not relevance.is_relevant:
        document.status = "unsupported"
        document.error_message = relevance.reason
        db.commit()
        return

    # Create every Section row first, then fan the LLM calls out. Extraction is
    # network-bound, so the call count is the dominant cost once parsing is fast —
    # sections are packed several to a call and the calls run concurrently.
    rows = []
    for parsed in parsed_sections:
        section = Section(
            document_id=document.id,
            heading=parsed.heading,
            order_idx=parsed.order_idx,
            page_ref=parsed.page_ref,
            raw_text=parsed.raw_text,
        )
        db.add(section)
        rows.append((section, parsed))
    db.flush()

    parsed_only = [parsed for _section, parsed in rows]
    extractable = [
        (i, parsed) for i, parsed in enumerate(parsed_only)
        if len(parsed.raw_text.strip()) >= EXTRACTABLE_MIN_CHARS
    ]
    # Extraction calls are network-bound and generate independently, so wall-clock
    # scales with how many are in flight, not with CPU. The client paces them to stay
    # under the provider's tokens-per-minute ceiling.
    max_workers = int(os.environ.get("EXTRACTION_CONCURRENCY", "16"))
    extractions: dict[int, SectionExtraction] = {}

    def run(batches: list[list[tuple[int, ParsedSection]]]) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(extract_batch, batch) for batch in batches]
            for batch, future in zip(batches, futures):
                try:
                    extractions.update(future.result())
                except Exception:  # noqa: BLE001 - one bad batch shouldn't fail the doc
                    logger.exception(
                        "Failed to extract %s section(s) starting at index %s for document id=%s",
                        len(batch), batch[0][0], document.id,
                    )

    run(plan_batches(extractable))

    # A section can go missing because its batch call failed, or because the model
    # skipped it or mislabelled it inside an otherwise-good batch. Retry those on
    # their own — a single-section call has nothing to confuse it with. Without this
    # pass, a long document silently loses whole stretches of its content.
    # Small retry batches first — few enough that the model has little to confuse,
    # but not so few that a long document pays a separate call per missed section.
    # Whatever still fails gets a call to itself, which has nothing to confuse at all.
    for size in RETRY_BATCH_SIZES:
        missing = [i for i, _ in extractable if i not in extractions]
        if not missing:
            break
        logger.info(
            "Retrying %s missed section(s) %s at a time for document id=%s",
            len(missing), size, document.id,
        )
        run([
            [(i, parsed_only[i]) for i in missing[n : n + size]]
            for n in range(0, len(missing), size)
        ])

    still_missing = [i for i, _ in extractable if i not in extractions]
    if still_missing:
        logger.error(
            "Extraction incomplete for document id=%s: %s of %s extractable sections "
            "have no result", document.id, len(still_missing), len(extractable),
        )

    # Nothing at all came back from a document that had sections worth extracting.
    # That is not a document with no obligations in it — it is a document nothing was
    # read from: the provider was unreachable, or the account's rate limit was
    # exhausted for long enough to burn every retry. Marking it "done" showed the
    # user a Ready badge over six empty tabs with no explanation, and no reason to
    # think re-uploading would help. Observed on a real run: "75 of 75 extractable
    # sections have no result", status done, not one summary row.
    if extractable and not extractions:
        logger.error(
            "Extraction produced nothing for document id=%s; marking it failed", document.id
        )
        document.status = "failed"
        document.error_message = (
            "The document was read, but nothing could be extracted from it. The "
            "AI service may be unavailable or rate limited. Try uploading it again "
            "in a few minutes."
        )
        db.commit()
        return

    summary_parts = []
    # Walking rows in order keeps summaries in document order.
    for idx, (section, parsed) in enumerate(rows):
        extraction = extractions.get(idx)
        if extraction is None:
            continue

        summary_parts.append(extraction.summary)
        for o in extraction.obligations:
            db.add(Obligation(document_id=document.id, section_id=section.id, text=o.text, responsible_role=o.responsible_role, priority=o.priority))
        for r in extraction.risks:
            db.add(Risk(document_id=document.id, section_id=section.id, text=r.text, severity=r.severity))
        for d in extraction.deadlines:
            db.add(Deadline(document_id=document.id, section_id=section.id, description=d.description, due_date=d.due_date, responsible_role=d.responsible_role))
        for a in extraction.action_items:
            db.add(ActionItem(document_id=document.id, section_id=section.id, text=a.text, responsible_role=a.responsible_role, timeframe=a.timeframe, priority=a.priority, source_section=parsed.heading))

    if summary_parts:
        db.add(Summary(document_id=document.id, text="\n\n".join(summary_parts), model_used="section-wise"))

    document.status = "done"
    db.commit()
