from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["actions"])


@router.get("/actions")
def get_action_items():
    return {"status": "not_implemented", "message": "Action item tracking is coming soon."}
