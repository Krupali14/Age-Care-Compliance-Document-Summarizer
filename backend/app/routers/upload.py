import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, User
from app.schemas import UploadResponse
from app.services.processing import process_document

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_TYPES = {".pdf", ".docx"}


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # ponytail: strip directory components so a crafted filename (e.g. "../../etc/x.pdf")
    # can't escape UPLOAD_DIR — Path.name discards any path segments, keeping only the basename.
    safe_filename = Path(file.filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    document = Document(
        user_id=user.id,
        filename=safe_filename,
        file_type=ext.lstrip("."),
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    upload_dir = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{document.id}_{safe_filename}"
    with dest.open("wb") as f:
        f.write(file.file.read())

    background_tasks.add_task(process_document, document.id, str(dest))
    return {"id": document.id, "filename": document.filename, "status": document.status}
