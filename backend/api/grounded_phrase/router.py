from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .service import DEFAULT_JPEG_QUALITY, phrase_grounding_annotate_frame, read_rtsp_frame
from .service import get_settings


router = APIRouter(prefix="/api/grounded-phrase", tags=["grounded_phrase"])


@router.get("/health", summary="Healthcheck (grounded_phrase)")
async def health():
    """Lightweight healthcheck.

    Notes:
    - Does NOT load Florence-2 model weights.
    - Only validates config/env and basic import availability.
    """

    # Mirror service-side resolution so the health output is accurate.
    settings = get_settings()
    model_id = settings.florence2_model_id
    path_exists = Path(model_id).exists()

    return {
        "ok": True,
        "service": "grounded_phrase",
        "florence2_model_id": model_id,
        "florence2_model_path_exists": path_exists,
    }


class GroundedPhraseRequest(BaseModel):
    image_b64: str = Field(..., description="Base64 of an image (JPEG/PNG).")
    prompt: str = Field(..., description="Single phrase prompt used for grounding.")
    return_debug: bool = Field(False, description="Whether to return Florence parsed result in headers.")


class GroundedPhraseRtspRequest(BaseModel):
    rtsp_url: str = Field(..., description="RTSP URL that can be opened by OpenCV.")
    prompt: str = Field(..., description="Single phrase prompt used for grounding.")
    timeout_sec: float = Field(5.0, ge=0.5, le=60.0, description="Timeout for opening/reading a frame.")
    jpeg_quality: int = Field(DEFAULT_JPEG_QUALITY, ge=50, le=100, description="Output JPEG quality.")
    return_debug: bool = Field(False, description="Whether to return debug info in headers.")


@router.post("/annotate", summary="Phrase grounding on a single frame")
async def annotate(req: GroundedPhraseRequest):
    try:
        image_bytes = base64.b64decode(req.image_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}")

    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")

    annotated, parsed = phrase_grounding_annotate_frame(frame, req.prompt)

    ok, out_jpg = cv2.imencode(
        ".jpg",
        annotated,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(DEFAULT_JPEG_QUALITY)],
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")

    headers = {}
    if req.return_debug:
        headers["X-Florence-Keys"] = ",".join(parsed.keys())

    return Response(content=out_jpg.tobytes(), media_type="image/jpeg", headers=headers)


@router.post("/annotate_rtsp", summary="Phrase grounding on a single frame from an RTSP stream")
async def annotate_rtsp(req: GroundedPhraseRtspRequest):
    import time

    t0 = time.monotonic()
    try:
        frame = read_rtsp_frame(req.rtsp_url, timeout_sec=req.timeout_sec)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read RTSP frame: {e}")

    t1 = time.monotonic()
    annotated, parsed = phrase_grounding_annotate_frame(frame, req.prompt)
    t2 = time.monotonic()

    ok, out_jpg = cv2.imencode(
        ".jpg",
        annotated,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(req.jpeg_quality)],
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")

    headers = {}
    if req.return_debug:
        h, w = frame.shape[:2]
        headers["X-Frame-Size"] = f"{w}x{h}"
        headers["X-RTSP-Read-Ms"] = str(int((t1 - t0) * 1000))
        headers["X-Infer-Ms"] = str(int((t2 - t1) * 1000))
        headers["X-Florence-Keys"] = ",".join(parsed.keys())

    return Response(content=out_jpg.tobytes(), media_type="image/jpeg", headers=headers)
