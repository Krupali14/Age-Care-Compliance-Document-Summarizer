from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["risks"])


@router.get("/risks")
def get_risks():
    return {"status": "not_implemented", "message": "Risk extraction is coming soon."}
