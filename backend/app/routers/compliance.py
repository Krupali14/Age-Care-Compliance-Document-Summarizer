import os
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CheckFinding, ComplianceCheck, User
from app.routers.documents import _get_owned_document
from app.routers.upload import ALLOWED_TYPES, _fit_filename, save_upload
from app.services.compliance_check import run_check

router = APIRouter(prefix="/api/compliance-checks", tags=["compliance-checks"])


def _get_owned_check(check_id: int, db: Session, user: User) -> ComplianceCheck:
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")
    # A check has no owner of its own; it belongs to whoever owns the document it
    # was run against, and _get_owned_document raises 404 for anyone else.
    _get_owned_document(check.document_id, db, user)
    return check


def _counts(findings: list[CheckFinding]) -> dict[str, int]:
    tally = Counter(f.verdict for f in findings)
    return {verdict: tally.get(verdict, 0) for verdict in ("done", "partly", "not_done", "unclear")}


@router.post("/{doc_id}", status_code=status.HTTP_201_CREATED)
def create_check(
    doc_id: int,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_document(doc_id, db, user)

    safe_filename = _fit_filename(Path(file.filename).name)
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    check = ComplianceCheck(
        document_id=doc_id,
        filename=safe_filename,
        file_type=ext.lstrip("."),
        status="pending",
    )
    db.add(check)
    db.commit()
    db.refresh(check)

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    try:
        dest, _name = save_upload(file, upload_dir, f"check{check.id}")
    except Exception:
        # The row exists only to hold the file being written.
        db.delete(check)
        db.commit()
        raise

    background_tasks.add_task(run_check, check.id, str(dest))
    return {"id": check.id, "filename": check.filename, "status": check.status}


@router.get("/{doc_id}")
def list_checks(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_document(doc_id, db, user)
    checks = (
        db.query(ComplianceCheck)
        .filter(ComplianceCheck.document_id == doc_id)
        .order_by(ComplianceCheck.id.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "filename": c.filename,
            "status": c.status,
            "error_message": c.error_message,
            "uploaded_at": c.uploaded_at,
            "incident_at": c.incident_at,
            "incident_source": c.incident_source,
            "counts": _counts(c.findings),
        }
        for c in checks
    ]


@router.get("/item/{check_id}")
def get_check(check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check = _get_owned_check(check_id, db, user)
    return {
        "id": check.id,
        "document_id": check.document_id,
        "filename": check.filename,
        "status": check.status,
        "error_message": check.error_message,
        "uploaded_at": check.uploaded_at,
        "incident_at": check.incident_at,
        "incident_source": check.incident_source,
        "counts": _counts(check.findings),
        "findings": [
            {
                "id": f.id,
                "kind": f.kind,
                "section_id": f.section_id,
                "requirement": f.requirement,
                "verdict": f.verdict,
                "evidence": f.evidence,
                "note": f.note,
                "due_at": f.due_at.isoformat() if f.due_at else None,
                "bucket": f.bucket,
            }
            for f in check.findings
        ],
    }


@router.delete("/item/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(check_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check = _get_owned_check(check_id, db, user)
    db.delete(check)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
