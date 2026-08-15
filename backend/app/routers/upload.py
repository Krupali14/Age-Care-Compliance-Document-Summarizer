from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
def upload_document():
    return {"status": "not_implemented", "message": "Document upload is coming soon."}
