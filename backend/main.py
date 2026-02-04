"""
FastAPI 应用入口。

在这里创建 FastAPI 实例，并挂载各个子路由。

启动命令（在项目根目录 `Video-Stream-System` 下执行）：

    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 设备管理模块
from backend.api.device_management.hello_world import router as hello_world_router
from backend.api.device_management.device_state import router as device_state_router
from backend.api.device_management.device_monitor import router as device_monitor_router

# 视频流模块
from backend.api.video_stream.monitor_stream import router as monitor_stream_router
from backend.api.video_stream.multi_preview import router as multi_preview_router
from backend.api.video_stream.rtsp_manager import router as rtsp_manager_router

# 视觉理解/标注模块
from backend.api.grounded_phrase.router import router as grounded_phrase_router
from backend.api.grounded_tracking.router import router as grounded_tracking_router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="视频轮播系统后端",
        version="1.0.0",
    )

    # CORS: allow browser-based frontends to call the API.
    # NOTE: In production, set BACKEND_CORS_ORIGINS to a comma-separated allowlist.
    cors_origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由 - 设备管理
    app.include_router(hello_world_router)
    app.include_router(device_state_router)
    app.include_router(device_monitor_router)

    # 注册路由 - 视频流
    app.include_router(monitor_stream_router)
    app.include_router(multi_preview_router)
    app.include_router(rtsp_manager_router)

    # 注册路由 - 视觉理解/标注
    app.include_router(grounded_phrase_router)
    app.include_router(grounded_tracking_router)

    return app


app = create_app()


@app.on_event("startup")
def preload_models_on_startup() -> None:
    """Optionally warm up heavy vision models at process startup.

    Motivation: first-request cold start for Florence-2 / Grounded-SAM2 can be very slow.

    Environment variables:
    - `PRELOAD_GROUNDED_PHRASE`  : "1" to preload grounded_phrase (default: 1)
    - `PRELOAD_GROUNDED_TRACKING`: "1" to preload grounded_tracking (default: 1)
    - `PRELOAD_STRICT`           : "1" to fail startup when preload fails (default: 0)
    """

    strict = os.getenv("PRELOAD_STRICT", "0") == "1"

    def _maybe_raise(e: Exception) -> None:
        if strict:
            raise
        print(f"[startup] preload skipped/failed ({type(e).__name__}): {e}")

    if os.getenv("PRELOAD_GROUNDED_TRACKING", "1") == "1":
        try:
            from backend.api.grounded_tracking.service import get_models as grounded_tracking_get_models

            grounded_tracking_get_models()
            print("[startup] grounded_tracking models preloaded")
        except Exception as e:
            _maybe_raise(e)

    if os.getenv("PRELOAD_GROUNDED_PHRASE", "1") == "1":
        try:
            from backend.api.grounded_phrase.service import get_florence2 as grounded_phrase_get_florence2

            grounded_phrase_get_florence2()
            print("[startup] grounded_phrase models preloaded")
        except Exception as e:
            _maybe_raise(e)


@app.get("/")
async def root() -> dict:
    """简单根路径，用于健康检查。"""
    return {"message": "Video Stream System Backend is running"}

