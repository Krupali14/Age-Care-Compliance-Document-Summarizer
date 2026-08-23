import logging

from app.database import SessionLocal
from app.models import ActionItem, Deadline, Document, Obligation, Risk, Section, Summary
from app.services.docling_parser import parse_document
from app.services.extraction import extract_section

logger = logging.getLogger(__name__)


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
    except Exception as exc:  # noqa: BLE001 - unrecoverable parse failure
        document.status = "failed"
        document.error_message = str(exc)
        db.commit()
        return

    summary_parts = []
    for parsed in parsed_sections:
        section = Section(
            document_id=document.id,
            heading=parsed.heading,
            order_idx=parsed.order_idx,
            page_ref=parsed.page_ref,
            raw_text=parsed.raw_text,
        )
        db.add(section)
        db.flush()

        try:
            extraction = extract_section(parsed)
        except Exception:  # noqa: BLE001 - one bad section shouldn't fail the doc
            logger.exception(
                "Failed to extract section id=%s heading=%r for document id=%s",
                section.id, parsed.heading, document.id,
            )
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
