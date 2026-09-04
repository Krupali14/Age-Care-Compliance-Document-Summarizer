from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Deadline, User
from app.routers.documents import _get_owned_document
from app.services.extraction import normalize_due_date

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@router.get("/{doc_id}")
def get_deadlines(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Deadline).filter(Deadline.document_id == doc_id).all()
    # Normalise on the way out, not just at extraction time: rows stored before the
    # rule existed still hold dates that have since passed, and a date that was in
    # the future when it was extracted goes stale later on. A deadline that has gone
    # by is shown as having no date rather than as still being due.
    return [{"id": d.id, "section_id": d.section_id, "description": d.description, "due_date": normalize_due_date(d.due_date), "responsible_role": d.responsible_role} for d in rows]
