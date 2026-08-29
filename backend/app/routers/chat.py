from fastapi import APIRouter, Depends
from pydantic import BaseModel
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Section, User
from app.routers.documents import _get_owned_document
from app.services.llm import get_llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


def _top_sections(question: str, sections: list[Section], k: int = 3) -> list[Section]:
    scored = sorted(sections, key=lambda s: fuzz.partial_ratio(question, s.raw_text), reverse=True)
    return scored[:k]


@router.post("/{doc_id}")
def chat(doc_id: int, payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)
    top_sections = _top_sections(payload.question, document.sections)
    context = "\n\n".join(f"## {s.heading}\n{s.raw_text}" for s in top_sections)

    prompt = (
        "Answer the question using only the document excerpts below. "
        "If the answer isn't in the excerpts, say you don't know.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {payload.question}"
    )
    llm = get_llm()
    response = llm.invoke(prompt)
    return {
        "answer": response.content,
        "sources": [{"id": s.id, "heading": s.heading} for s in top_sections],
    }
