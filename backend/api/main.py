# """
# FastAPI 应用入口。
#
# 在这里创建 FastAPI 实例，并挂载各个子路由。
#
# 启动命令（在项目根目录 `Video-Stream-System` 下执行）：
#
#     uvicorn backend.main:app --reload
#
# """
# import sys
# module_path = "../../"
# sys.path.append(module_path)
# import asyncio
#
# from fastapi import FastAPI
# import uvicorn
#
# from backend.api.device_management.camera_operation import router as camera_operation_router
# from backend.api.device_management.camera_operation import load_cameras_from_db, save_cameras_to_db, start_cameras_healthcheck, stop_cameras_healthcheck
#
#
# def create_app() -> FastAPI:
#     """创建并配置 FastAPI 应用实例。"""
#     app = FastAPI(
#         title="视频轮播系统后端",
#         version="1.0.0",
#     )
#
#     # 注册路由
#     app.include_router(camera_operation_router)
#
#
#     return app
#
# app = create_app()
#
#
# if __name__ == '__main__':
#     asyncio.run(load_cameras_from_db())
#     asyncio.run(start_cameras_healthcheck())
#     uvicorn.run(app="main:app", host="127.0.0.1", port=8000)
#     asyncio.run(stop_cameras_healthcheck())
#     asyncio.run(save_cameras_to_db())

"""
FastAPI 应用入口
"""

import sys
module_path = "../../"
sys.path.append(module_path)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.api.device_management.camera_operation import (
    router as camera_operation_router,
    load_cameras_from_db,
    save_cameras_to_db,
    start_cameras_healthcheck,
    stop_cameras_healthcheck,
)

from backend.api.grounded_phrase.router import router as grounded_phrase_router
from backend.api.grounded_tracking.router import router as grounded_tracking_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="视频轮播系统后端",
        version="1.0.0",
    )

    # CORS for browser-based frontends.
    # NOTE: For production, restrict origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(camera_operation_router)
    app.include_router(grounded_phrase_router)
    app.include_router(grounded_tracking_router)

    @app.on_event("startup")
    async def startup_event():
        await load_cameras_from_db()
        await start_cameras_healthcheck()

    @app.on_event("shutdown")
    async def shutdown_event():
        await stop_cameras_healthcheck()
        await save_cameras_to_db()

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)


