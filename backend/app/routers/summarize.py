from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["summarize"])


@router.get("/summarize")
def get_summaries():
    return {"status": "not_implemented", "message": "Summarisation is coming soon."}
