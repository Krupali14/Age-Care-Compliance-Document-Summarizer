from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Summary, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/summarize", tags=["summarize"])


@router.get("/{doc_id}")
def get_summaries(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    summaries = db.query(Summary).filter(Summary.document_id == doc_id).all()
    return [{"id": s.id, "text": s.text, "model_used": s.model_used} for s in summaries]
