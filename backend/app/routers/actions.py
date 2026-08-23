from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActionItem, User
from app.routers.documents import _get_owned_document

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/{doc_id}")
def get_action_items(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    rows = db.query(ActionItem).filter(ActionItem.document_id == doc_id).all()
    return [{"id": a.id, "section_id": a.section_id, "text": a.text, "responsible_role": a.responsible_role, "timeframe": a.timeframe, "priority": a.priority, "source_section": a.source_section} for a in rows]
