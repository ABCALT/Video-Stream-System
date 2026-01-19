from fastapi import APIRouter

router = APIRouter(prefix="/api/device", tags=["device_management"])

@router.get("/state/{id}")
async def device_state(id : int) -> dict:
    """
    
    """
    return {"id": id, "state": "active"}