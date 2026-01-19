from fastapi import APIRouter

router = APIRouter(prefix="/api/device", tags=["device_management"])


@router.get("/hello")
async def hello_world() -> dict:
    """
    简单示例：接收前端请求并返回 hello world。
    """
    return {"message": "hello world"}


