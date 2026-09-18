from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Deadline, User
from app.routers.documents import _get_owned_document
from app.services.deadlines import DEFAULT_STATUS, STATUSES, bucket_for, is_relative_due_date, resolve_due_at
from app.services.extraction import normalize_due_date

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


class StatusUpdate(BaseModel):
    status: str


@router.get("/{doc_id}")
def get_deadlines(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)
    rows = db.query(Deadline).filter(Deadline.document_id == doc_id).all()
    # Relative timeframes ("within 4 hours of the incident") are counted from when
    # the document was uploaded — the only moment the system knows about.
    anchor = document.uploaded_at or datetime.utcnow()
    now = datetime.utcnow()
    out = []
    for d in rows:
        # Normalise on the way out, not just at extraction time: rows stored before
        # the rule existed still hold dates that have since passed, and a date that
        # was in the future when it was extracted goes stale later on. A deadline
        # that has gone by is shown as having no date rather than as still being due.
        due_date = normalize_due_date(d.due_date)
        due_at = resolve_due_at(due_date, anchor)
        # A relative timeframe is counted from the incident, not the upload — so its
        # due_at above is only ever a stand-in, and bucketing that stand-in against
        # `now` would call it "overdue" for an incident that hasn't happened.
        bucket = "awaiting_trigger" if is_relative_due_date(due_date) else bucket_for(due_at, now)
        out.append({
            "id": d.id,
            "section_id": d.section_id,
            "description": d.description,
            "due_date": due_date,
            "due_at": f"{due_at.isoformat()}Z" if due_at else None,
            "bucket": bucket,
            "responsible_role": d.responsible_role,
            "status": d.status or DEFAULT_STATUS,
        })
    return out


@router.patch("/item/{deadline_id}")
def update_deadline_status(
    deadline_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record progress against one deadline."""
    if payload.status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of: {', '.join(STATUSES)}")
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
    if deadline is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    # Ownership lives on the document, not the row — check it before writing.
    _get_owned_document(deadline.document_id, db, user)
    deadline.status = payload.status
    db.commit()
    return {"id": deadline.id, "status": deadline.status}
