from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import EvalRun, User
from app.routers.documents import _get_owned_document
from app.services.eval_scoring import run_auto_eval, run_eval

router = APIRouter(prefix="/api/documents", tags=["eval"])


class EvalRequest(BaseModel):
    ground_truth: dict[str, list[str]]


def _serialize(run: EvalRun) -> dict:
    return {"id": run.id, "precision": run.precision, "recall": run.recall, "f1": run.f1, "ground_truth_ref": run.ground_truth_ref, "created_at": run.created_at}


@router.get("/{doc_id}/eval")
def get_eval_runs(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    runs = db.query(EvalRun).filter(EvalRun.document_id == doc_id).order_by(EvalRun.created_at.desc()).all()
    return [_serialize(r) for r in runs]


@router.post("/{doc_id}/eval", status_code=status.HTTP_201_CREATED)
def create_eval_run(doc_id: int, payload: EvalRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    try:
        run = run_eval(db, doc_id, payload.ground_truth, "api")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize(run)


@router.post("/{doc_id}/eval/auto", status_code=status.HTTP_201_CREATED)
def create_auto_eval_run(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Score a document against itself — no ground truth needed, so the UI can run
    this the first time someone opens a document's evaluation."""
    document = _get_owned_document(doc_id, db, user)
    if document.status != "done":
        raise HTTPException(status_code=409, detail=f"Document is {document.status}; nothing to evaluate yet")
    return _serialize(run_auto_eval(db, doc_id))
