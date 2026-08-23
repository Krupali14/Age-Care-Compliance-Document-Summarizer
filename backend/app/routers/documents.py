import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActionItem, Deadline, Document, EvalRun, Obligation, Risk, Section, Summary, User

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_owned_document(doc_id: int, db: Session, user: User) -> Document:
    document = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    return [{"id": d.id, "filename": d.filename, "status": d.status, "uploaded_at": d.uploaded_at} for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)
    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "error_message": document.error_message,
        "sections": [
            {"id": s.id, "heading": s.heading, "order_idx": s.order_idx, "page_ref": s.page_ref, "raw_text": s.raw_text}
            for s in sorted(document.sections, key=lambda s: s.order_idx)
        ],
    }


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = _get_owned_document(doc_id, db, user)

    # ponytail: no ON DELETE CASCADE on these FKs, so delete children explicitly
    # before the parent row to avoid a foreign-key violation.
    db.query(EvalRun).filter(EvalRun.document_id == doc_id).delete()
    db.query(ActionItem).filter(ActionItem.document_id == doc_id).delete()
    db.query(Deadline).filter(Deadline.document_id == doc_id).delete()
    db.query(Risk).filter(Risk.document_id == doc_id).delete()
    db.query(Obligation).filter(Obligation.document_id == doc_id).delete()
    db.query(Summary).filter(Summary.document_id == doc_id).delete()
    db.query(Section).filter(Section.document_id == doc_id).delete()

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    file_path = upload_dir / f"{document.id}_{document.filename}"
    file_path.unlink(missing_ok=True)

    db.delete(document)
    db.commit()
