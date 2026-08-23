from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Obligation, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/obligations", tags=["obligations"])


@router.get("/{doc_id}")
def get_obligations(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(Obligation).filter(Obligation.document_id == doc_id).all()
    return [{"id": o.id, "section_id": o.section_id, "text": o.text, "responsible_role": o.responsible_role, "priority": o.priority} for o in rows]
