from __future__ import annotations

import time

from pathlib import Path
from typing import Iterator, Optional

import cv2
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .service import DEFAULT_JPEG_QUALITY, get_settings, mjpeg_tracking_annotate_frame, read_rtsp_frame
from .service import mjpeg_tracking_generator


router = APIRouter(prefix="/api/grounded-tracking", tags=["grounded_tracking"])


@router.options("/mjpeg", include_in_schema=False)
def mjpeg_options() -> Response:
    # For browser CORS preflight. If CORSMiddleware is configured globally,
    # this route is harmless; if not, it prevents 405 on OPTIONS.
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/health", summary="Healthcheck (grounded_tracking)")
def health():
    """Lightweight healthcheck.

    Notes:
    - Does NOT load SAM2/GroundingDINO weights.
    - Only validates settings paths and basic config.
    """

    s = get_settings()
    return {
        "ok": True,
        "service": "grounded_tracking",
        "device": s.device,
        "dino_model_id": s.dino_model_id,
        "sam2_checkpoint": s.sam2_checkpoint,
        "sam2_checkpoint_exists": Path(s.sam2_checkpoint).exists(),
        "sam2_config": s.sam2_config,
        "sam2_config_exists": Path(s.sam2_config).exists(),
    }


class GroundedTrackingRtspRequest(BaseModel):
    rtsp_url: str = Field(..., description="RTSP URL that can be opened by OpenCV.")
    text: str = Field(..., description="Text query for GroundingDINO. Lowercase + end with a dot, e.g. 'car.'.")
    step: int = Field(20, ge=1, le=300, description="Run detection every N frames (for this single-frame read, kept for API parity).")
    jpeg_quality: int = Field(DEFAULT_JPEG_QUALITY, ge=50, le=100, description="Output JPEG quality.")
    detection_threshold: float = Field(0.25, ge=0.0, le=1.0, description="Box score threshold")
    text_threshold: float = Field(0.25, ge=0.0, le=1.0, description="Text threshold")
    timeout_sec: float = Field(5.0, ge=0.1, le=120.0, description="RTSP read timeout seconds")
    return_debug: bool = Field(False, description="Whether to return debug info in headers.")


@router.post("/annotate_rtsp", summary="Grounded-SAM2 tracking on a single frame from an RTSP stream")
def annotate_rtsp(req: GroundedTrackingRtspRequest):
    t0 = time.monotonic()
    try:
        frame = read_rtsp_frame(req.rtsp_url, timeout_sec=req.timeout_sec)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read RTSP frame: {e}")
    t1 = time.monotonic()

    try:
        annotated, debug = mjpeg_tracking_annotate_frame(
            frame_bgr=frame,
            text=req.text,
            detection_threshold=req.detection_threshold,
            text_threshold=req.text_threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    t2 = time.monotonic()

    ok, out_jpg = cv2.imencode(
        ".jpg",
        annotated,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(req.jpeg_quality)],
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")

    headers: dict[str, str] = {}
    if req.return_debug:
        h, w = frame.shape[:2]
        headers["X-Frame-Size"] = f"{w}x{h}"
        headers["X-RTSP-Read-Ms"] = str(int((t1 - t0) * 1000))
        headers["X-Infer-Ms"] = str(int((t2 - t1) * 1000))
        if debug:
            headers["X-Tracking-Keys"] = ",".join(sorted(debug.keys()))

    return Response(content=out_jpg.tobytes(), media_type="image/jpeg", headers=headers)


@router.get("/mjpeg", summary="Grounded-SAM2 tracking MJPEG stream (RTSP input)")
def mjpeg(
    rtsp_url: str = Query(..., description="RTSP URL"),
    text: str = Query(..., description="Text query for GroundingDINO. Lowercase + end with a dot, e.g. 'car.'"),
    step: int = Query(20, ge=1, le=300, description="Run detection every N frames"),
    max_fps: float = Query(5.0, ge=0.1, le=30.0, description="Max output FPS"),
    duration_sec: Optional[float] = Query(None, ge=1.0, le=3600.0, description="Stop after duration seconds"),
    jpeg_quality: int = Query(85, ge=50, le=100, description="JPEG quality"),
    detection_threshold: float = Query(0.25, ge=0.0, le=1.0, description="Box score threshold"),
    text_threshold: float = Query(0.25, ge=0.0, le=1.0, description="Text threshold"),
    timeout_sec: float = Query(5.0, ge=0.1, le=120.0, description="RTSP read timeout seconds"),
):
    try:
        gen: Iterator[bytes] = mjpeg_tracking_generator(
            rtsp_url=rtsp_url,
            text=text,
            step=step,
            max_fps=max_fps,
            duration_sec=duration_sec,
            jpeg_quality=jpeg_quality,
            detection_threshold=detection_threshold,
            text_threshold=text_threshold,
            timeout_sec=timeout_sec,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    resp = StreamingResponse(gen, media_type="multipart/x-mixed-replace; boundary=frame")
    # Safe for demo usage; restrict in production.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
