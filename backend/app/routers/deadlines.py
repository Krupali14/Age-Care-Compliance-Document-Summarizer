from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["deadlines"])


@router.get("/deadlines")
def get_deadlines():
    return {"status": "not_implemented", "message": "Deadline tracking is coming soon."}
