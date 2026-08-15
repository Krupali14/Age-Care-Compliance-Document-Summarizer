from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["obligations"])


@router.get("/obligations")
def get_obligations():
    return {"status": "not_implemented", "message": "Obligation extraction is coming soon."}
