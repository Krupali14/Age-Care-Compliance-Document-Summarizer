from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import EvalRun, User
from app.routers.documents import _get_owned_document
from app.services.eval_scoring import run_eval

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
    run = run_eval(db, doc_id, payload.ground_truth, "api")
    return _serialize(run)
