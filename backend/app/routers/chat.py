import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Section, User
from app.routers.documents import _get_owned_document
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Matches processing.EXTRACTABLE_MIN_CHARS: anything shorter is a contents entry or
# a stray page number, never an answer.
MIN_SECTION_CHARS = 40


class ChatRequest(BaseModel):
    question: str


def _top_sections(question: str, sections: list[Section], k: int = 3) -> list[Section]:
    """The k sections most likely to answer the question.

    partial_ratio scores on the best-matching substring, which makes a very short
    section win easily: on a 1300-section Act the top hit for "reporting obligations"
    was a 13-character contents scrap, and the three "best" sections between them
    supplied 307 characters of context. token_set_ratio compares the words actually
    shared, and contents fragments are dropped before ranking, so the model gets real
    text to answer from.
    """
    candidates = [s for s in sections if len((s.raw_text or "").strip()) >= MIN_SECTION_CHARS]
    if not candidates:
        candidates = list(sections)
    scored = sorted(
        candidates,
        key=lambda s: fuzz.token_set_ratio(question.lower(), (s.raw_text or "").lower()),
        reverse=True,
    )
    return scored[:k]


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

    top_sections = _top_sections(question, document.sections)
    context = "\n\n".join(f"## {s.heading}\n{s.raw_text}" for s in top_sections)

    prompt = (
        "Answer the question using only the document excerpts below. "
        "If the answer isn't in the excerpts, say you don't know.\n\n"
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
        "sources": [{"id": s.id, "heading": s.heading} for s in top_sections],
    }
