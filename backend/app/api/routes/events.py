from fastapi import APIRouter

router = APIRouter(tags=["events"])

@router.get("/events")
def list_events():
    return {"items": [], "total": 0}
