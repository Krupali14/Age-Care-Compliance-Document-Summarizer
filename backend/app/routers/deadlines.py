from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Deadline, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@router.get("/{doc_id}")
def get_deadlines(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Deadline).filter(Deadline.document_id == doc_id).all()
    return [{"id": d.id, "section_id": d.section_id, "description": d.description, "due_date": d.due_date, "responsible_role": d.responsible_role} for d in rows]
