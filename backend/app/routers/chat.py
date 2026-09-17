import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActionItem, Deadline, Obligation, Risk, Section, User
from app.routers.documents import _get_owned_document
from app.services.llm import get_llm
from app.services.retrieval import rank, terms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Matches processing.EXTRACTABLE_MIN_CHARS: anything shorter is a contents entry or
# a stray page number, never an answer.
MIN_SECTION_CHARS = 40

# Enough passages that a question spanning several provisions still gets all of
# them, and enough characters that each arrives whole rather than as a snippet.
TOP_K = 6
MAX_CONTEXT_CHARS = 12000

# Longer than any real question and far shorter than a pasted document. Without a
# ceiling the whole body is forwarded to the model, so any signed-in user can turn
# one request into an arbitrarily large bill.
MAX_QUESTION_CHARS = 2000


class ChatRequest(BaseModel):
    question: str = Field(max_length=MAX_QUESTION_CHARS)


# A question naming one of these categories is asking for what extraction already
# filed under it, but the provisions themselves rarely use the words "risk" or
# "deadline" — so term matching alone never reaches them, and the assistant answered
# "I don't know" while the answer sat in its own database. Naming a category
# guarantees its findings a place in the context.
CATEGORY_WORDS = {
    "obligation": {"obligation", "obligations", "obliged", "comply", "compliance", "duty", "duties", "must", "requirement", "requirements"},
    "risk": {"risk", "risks", "risky", "hazard", "hazards", "danger", "dangers", "severity"},
    "deadline": {"deadline", "deadlines", "due", "timeframe", "timeframes", "timeline", "timelines", "date", "dates", "overdue"},
    "action": {"action", "actions", "actionable", "steps", "remediation", "todo"},
}

# At most this many slots go to a named category, leaving the rest for whatever the
# ranking finds — a context made only of one-line findings loses the surrounding text.
MAX_CATEGORY_PASSAGES = 3


def _findings(doc_id: int, db: Session) -> list[tuple[str, int, str]]:
    """The document's extracted obligations, risks, deadlines and actions as
    (text, section_id, category) triples, indexed alongside the sections so a
    question about them retrieves them, still cited back to its own section."""
    out: list[tuple[str, int, str]] = []
    for row in db.query(Obligation).filter(Obligation.document_id == doc_id):
        role = f" Responsible: {row.responsible_role}." if row.responsible_role else ""
        out.append((f"Obligation: {row.text}{role}", row.section_id, "obligation"))
    for row in db.query(Risk).filter(Risk.document_id == doc_id):
        out.append((f"Risk ({row.severity} severity): {row.text}", row.section_id, "risk"))
    for row in db.query(Deadline).filter(Deadline.document_id == doc_id):
        due = f" Due: {row.due_date}." if row.due_date else ""
        role = f" Responsible: {row.responsible_role}." if row.responsible_role else ""
        out.append((f"Deadline: {row.description}{due}{role}", row.section_id, "deadline"))
    for row in db.query(ActionItem).filter(ActionItem.document_id == doc_id):
        when = f" Timeframe: {row.timeframe}." if row.timeframe else ""
        out.append((f"Required action: {row.text}{when}", row.section_id, "action"))
    return [(text, section_id, kind) for text, section_id, kind in out if section_id is not None]


def _passages(doc_id: int, sections: list[Section], db: Session) -> list[tuple[str, Section, str | None]]:
    candidates = [s for s in sections if len((s.raw_text or "").strip()) >= MIN_SECTION_CHARS]
    if not candidates:
        candidates = list(sections)

    passages = [(f"{s.heading or ''}\n{s.raw_text or ''}", s, None) for s in candidates]

    by_id = {s.id: s for s in sections}
    for text, section_id, kind in _findings(doc_id, db):
        section = by_id.get(section_id)
        if section is not None:
            passages.append((f"{section.heading or ''}\n{text}", section, kind))
    return passages


def _select(question: str, passages: list[tuple[str, Section, str | None]], k: int = TOP_K):
    """The k best passages, within a character budget, and the sections to cite."""
    asked_for = {
        kind for kind, words in CATEGORY_WORDS.items() if words & set(terms(question))
    }
    ranked = rank(question, [text for text, _section, _kind in passages])

    chosen: list[tuple[str, Section]] = []
    taken: set[int] = set()
    budget = MAX_CONTEXT_CHARS

    def take(i: int) -> None:
        text, section, _kind = passages[i]
        taken.add(i)
        chosen.append((text, section))
        nonlocal budget
        budget -= len(text)

    if asked_for:
        for i in ranked:
            if len(chosen) >= MAX_CATEGORY_PASSAGES:
                break
            if passages[i][2] in asked_for:
                take(i)

    for i in ranked:
        if len(chosen) >= k:
            break
        if i in taken:
            continue
        if chosen and len(passages[i][0]) > budget:
            continue
        take(i)

    sources: list[Section] = []
    for _text, section in chosen:
        if section not in sources:
            sources.append(section)
    return chosen, sources


@router.post("/{doc_id}")
def chat(doc_id: int, payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Ask a question first")
    if not document.sections:
        raise HTTPException(
            status_code=409,
            detail="This document has no readable content to answer from",
        )

    chosen, sources = _select(question, _passages(doc_id, document.sections, db))
    context = "\n\n".join(f"## {text}" for text, _section in chosen)

    # "Answer only from the excerpts, otherwise say you don't know" was read as a
    # lookup instruction: asked to summarise, the model refused because no excerpt
    # contained a ready-made summary. The excerpts are still the only source — it
    # may now draw a conclusion from them rather than only quote one.
    prompt = (
        "You are answering questions about a compliance document. Use only the "
        "excerpts below as your source; you may summarise, combine and draw "
        "conclusions from them, but never add facts they do not support. Excerpts "
        "labelled Obligation, Risk, Deadline or Required action were extracted from "
        "this document and are part of it. Answer concisely, in Markdown. Only if "
        "the excerpts genuinely do not cover the question, say you don't know.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {question}"
    )
    # The model call is the one part of this that reaches the network, so it is also
    # the one part that fails for reasons the user cannot do anything about. A raw
    # 500 tells them nothing; this at least says to try again.
    try:
        response = get_llm().invoke(prompt)
    except Exception as exc:  # noqa: BLE001 - any provider failure looks the same here
        logger.exception("Chat model call failed for document id=%s", doc_id)
        raise HTTPException(
            status_code=503, detail="The assistant is unavailable right now. Try again shortly."
        ) from exc

    return {
        "answer": response.content,
        "sources": [{"id": s.id, "heading": s.heading} for s in sources],
    }
