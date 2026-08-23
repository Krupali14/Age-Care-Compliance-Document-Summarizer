from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Risk, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/risks", tags=["risks"])


@router.get("/{doc_id}")
def get_risks(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Risk).filter(Risk.document_id == doc_id).all()
    return [{"id": r.id, "section_id": r.section_id, "text": r.text, "severity": r.severity} for r in rows]
