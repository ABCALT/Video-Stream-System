"""
FastAPI 应用入口。

在这里创建 FastAPI 实例，并挂载各个子路由。

启动命令（在项目根目录 `Video-Stream-System` 下执行）：

    uvicorn backend.main:app --reload

"""

from fastapi import FastAPI

from backend.api.device_management.hello_world import router as hello_world_router
from backend.api.device_management.device_ping import (
    get_ping_manager,
    router as device_ping_router,
)
from backend.api.device_management.camera_operation import router as camera_operation_router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="视频轮播系统后端",
        version="1.0.0",
    )

    # 注册路由
    app.include_router(hello_world_router)
    app.include_router(device_ping_router)
    app.include_router(camera_operation_router)

    # @app.on_event("startup")
    # async def _startup() -> None:
    #     # 启动后台定时检测（仅单进程内存版；生产多进程需改造）
    #     await get_ping_manager().start()
    #
    # @app.on_event("shutdown")
    # async def _shutdown() -> None:
    #     await get_ping_manager().stop()

    return app


app = create_app()


@app.get("/")
async def root() -> dict:
    """简单根路径，用于健康检查。"""
    return {"message": "Video Stream System Backend is running"}


