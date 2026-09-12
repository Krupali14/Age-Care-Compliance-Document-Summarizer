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

# Reading an upload with file.read() buffers the whole thing in memory, so the size
# has to be bounded before it is stored, not after.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "25")) * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

# The first bytes of the real formats. A ".pdf" that is actually a text file only
# fails much later, deep in the parser, with an error no user can act on — so the
# content is checked here, while there is still a request to answer.
_SIGNATURES = {".pdf": b"%PDF-", ".docx": b"PK\x03\x04"}

# Filesystems cap a single path component at 255 **bytes**, and the stored name
# carries an "{id}_" prefix on top of whatever was uploaded. A 254-character name
# therefore raised OSError deep inside the write and escaped as a 500; so would a
# 90-character name written in a script whose characters are three bytes each.
# Trimming to a byte budget keeps both cases a normal upload.
MAX_FILENAME_BYTES = 180


def _fit_filename(name: str) -> str:
    """`name`, trimmed so it fits the byte budget, keeping its extension."""
    if len(name.encode("utf-8")) <= MAX_FILENAME_BYTES:
        return name
    suffix = Path(name).suffix
    budget = MAX_FILENAME_BYTES - len(suffix.encode("utf-8"))
    # Slicing encoded bytes can cut a multi-byte character in half; "ignore" drops
    # the partial one rather than raising.
    stem = Path(name).stem.encode("utf-8")[: max(budget, 1)].decode("utf-8", "ignore")
    return f"{stem}{suffix}"


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=UploadResponse)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # ponytail: strip directory components so a crafted filename (e.g. "../../etc/x.pdf")
    # can't escape UPLOAD_DIR — Path.name discards any path segments, keeping only the basename.
    safe_filename = _fit_filename(Path(file.filename).name)
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

    # Streamed in chunks and abandoned the moment it runs over the limit, so an
    # oversized upload costs a bounded amount of memory and disk rather than its
    # full size. The partial file is removed on every failure path.
    written = 0
    try:
        with dest.open("wb") as f:
            while chunk := file.file.read(CHUNK_BYTES):
                if written == 0 and not chunk.startswith(_SIGNATURES[ext]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"This file is not a readable {ext.lstrip('.').upper()} — it may be corrupt or renamed from another format",
                    )
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
                    )
                f.write(chunk)
        if written == 0:
            raise HTTPException(status_code=400, detail="This file is empty")
    except Exception:
        # Every failure, not only the ones raised above. An OSError here — a name the
        # filesystem refuses, a full disk, a permissions problem — used to escape as
        # a 500 *and* leave the Document row behind with no file to process, so the
        # dashboard showed a document that could never finish.
        dest.unlink(missing_ok=True)
        db.delete(document)
        db.commit()
        raise

    background_tasks.add_task(process_document, document.id, str(dest))
    return {"id": document.id, "filename": document.filename, "status": document.status}
