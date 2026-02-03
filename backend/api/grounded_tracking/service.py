import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional, Tuple

from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

from sam2.build_sam import build_sam2, build_sam2_video_predictor
from sam2.sam2_image_predictor import SAM2ImagePredictor


DEFAULT_JPEG_QUALITY = 95


@dataclass(frozen=True)
class GroundedTrackingSettings:
    sam2_checkpoint: str
    sam2_config: str
    device: str
    dino_model_id: str


def _default_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _repo_root() -> Path:
    # service.py -> grounded_tracking -> api -> backend -> Video-Stream-System
    here = Path(__file__).resolve()
    # .../Video-Stream-System/backend/api/grounded_tracking/service.py
    return here.parents[4]


def _resolve_path(p: str, *, fallback_bases: List[Path]) -> str:
    if not p:
        return p
    path = Path(p)
    if path.is_absolute() and path.exists():
        return str(path)

    # Try as-is relative to current working directory
    if not path.is_absolute():
        cwd_path = (Path.cwd() / path).resolve()
        if cwd_path.exists():
            return str(cwd_path)

    for base in fallback_bases:
        candidate = (base / path).resolve()
        if candidate.exists():
            return str(candidate)

    return str(path)


@lru_cache(maxsize=1)
def get_settings() -> GroundedTrackingSettings:
    repo = _repo_root()
    grounded_sam2_repo = repo.parent / "Grounded-SAM-2"
    # Allow running uvicorn from different working directories.
    # Try resolving relative paths against:
    # 1) Video-Stream-System repo root
    # 2) monorepo root (e.g. /home/linrui/demo)
    # 3) Grounded-SAM-2 repo (where checkpoints/configs live)
    fallback_bases = [repo, repo.parent, grounded_sam2_repo]

    sam2_checkpoint = _resolve_path(
        os.getenv("SAM2_CHECKPOINT", "checkpoints/sam2.1_hiera_large.pt"),
        fallback_bases=fallback_bases,
    )
    sam2_config = _resolve_path(
        os.getenv("SAM2_CONFIG", "sam2/configs/sam2.1/sam2.1_hiera_l.yaml"),
        fallback_bases=fallback_bases,
    )

    return GroundedTrackingSettings(
        sam2_checkpoint=sam2_checkpoint,
        sam2_config=sam2_config,
        device=os.getenv("GROUNDED_TRACKING_DEVICE", _default_device()),
        dino_model_id=os.getenv("GROUNDED_DINO_MODEL_ID", "IDEA-Research/grounding-dino-tiny"),
    )


@lru_cache(maxsize=1)
def get_models() -> Tuple[Any, Any, Any, str]:
    settings = get_settings()

    if not Path(settings.sam2_checkpoint).exists():
        raise FileNotFoundError(
            f"SAM2 checkpoint not found: {settings.sam2_checkpoint}. "
            "Set env SAM2_CHECKPOINT to an absolute path, or download checkpoints into Grounded-SAM-2/checkpoints. "
            "For example: /home/linrui/demo/Grounded-SAM-2/checkpoints/....pt"
        )
    if not Path(settings.sam2_config).exists():
        raise FileNotFoundError(
            f"SAM2 config not found: {settings.sam2_config}. "
            "Set env SAM2_CONFIG to an absolute path, or use Grounded-SAM-2 configs path."
        )

    if settings.device.startswith("cuda"):
        torch.autocast(device_type="cuda", dtype=torch.bfloat16).__enter__()
        if torch.cuda.get_device_properties(0).major >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

    video_predictor = build_sam2_video_predictor(settings.sam2_config, settings.sam2_checkpoint)

    sam2_image_model = build_sam2(settings.sam2_config, settings.sam2_checkpoint, device=settings.device)
    image_predictor = SAM2ImagePredictor(sam2_image_model)

    processor = AutoProcessor.from_pretrained(settings.dino_model_id)
    grounding_model = AutoModelForZeroShotObjectDetection.from_pretrained(settings.dino_model_id).to(settings.device)

    return video_predictor, image_predictor, (processor, grounding_model), settings.device


def _normalize_text_query(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return t
    if not t.endswith("."):
        t += "."
    return t


def _draw_boxes_and_ids(frame_bgr: np.ndarray, boxes_xyxy: np.ndarray, labels: List[str]) -> np.ndarray:
    out = frame_bgr.copy()
    for (x1, y1, x2, y2), label in zip(boxes_xyxy.astype(int), labels):
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if label:
            cv2.putText(
                out,
                label,
                (x1, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
    return out


def _overlay_mask(frame_bgr: np.ndarray, mask: np.ndarray, color: Tuple[int, int, int], alpha: float = 0.4) -> np.ndarray:
    out = frame_bgr.copy()
    if mask.dtype != np.bool_:
        mask = mask.astype(bool)
    overlay = np.zeros_like(out, dtype=np.uint8)
    overlay[mask] = np.array(color, dtype=np.uint8)
    return cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0)


def read_rtsp_frame(rtsp_url: str, timeout_sec: float = 5.0) -> np.ndarray:
    """Open an RTSP stream and read a single frame.

    Mirrors grounded_phrase.read_rtsp_frame behavior so routers can share error semantics.
    """

    start = time.monotonic()
    cap = cv2.VideoCapture(rtsp_url)
    try:
        if not cap.isOpened():
            raise RuntimeError("Failed to open RTSP stream")

        frame = None
        while True:
            ok, fr = cap.read()
            if ok and fr is not None and fr.size > 0:
                frame = fr
                break
            if time.monotonic() - start >= float(timeout_sec):
                raise TimeoutError(f"Timeout reading frame within {float(timeout_sec):.1f}s")
            time.sleep(0.03)

        return frame
    finally:
        cap.release()


def mjpeg_tracking_annotate_frame(
    frame_bgr: np.ndarray,
    text: str,
    detection_threshold: float = 0.25,
    text_threshold: float = 0.25,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Annotate a single frame using GroundingDINO + SAM2 image predictor.

    Returns:
    - annotated frame (BGR)
    - debug dict (lightweight)
    """

    _video_predictor, image_predictor, dino_pack, device = get_models()
    dino_processor, grounding_model = dino_pack

    query = _normalize_text_query(text)
    if not query:
        raise ValueError("text is required")

    h, w = frame_bgr.shape[:2]
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image_rgb)

    inputs = dino_processor(images=image, text=query, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = grounding_model(**inputs)

    results = dino_processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        threshold=float(detection_threshold),
        text_threshold=float(text_threshold),
        target_sizes=[(h, w)],
    )

    input_boxes = results[0].get("boxes")
    obj_labels = results[0].get("labels") or []

    debug: Dict[str, Any] = {
        "query": query,
        "num_boxes": int(getattr(input_boxes, "shape", [0])[0]) if input_boxes is not None else 0,
    }

    if input_boxes is None or getattr(input_boxes, "shape", None) is None or input_boxes.shape[0] == 0:
        return frame_bgr, debug

    image_predictor.set_image(image_rgb)
    masks, _scores, _logits = image_predictor.predict(
        point_coords=None,
        point_labels=None,
        box=input_boxes,
        multimask_output=False,
    )
    if masks.ndim == 2:
        masks = masks[None]
    elif masks.ndim == 4:
        masks = masks.squeeze(1)

    annotated = frame_bgr.copy()
    for i in range(min(masks.shape[0], 20)):
        color = (0, 255, 0) if i % 2 == 0 else (255, 0, 0)
        annotated = _overlay_mask(annotated, masks[i], color=color, alpha=0.35)

    boxes_np = input_boxes.detach().cpu().numpy() if torch.is_tensor(input_boxes) else np.asarray(input_boxes)
    labels = [str(x) for x in obj_labels]
    if len(labels) != boxes_np.shape[0]:
        labels = ["obj"] * boxes_np.shape[0]
    annotated = _draw_boxes_and_ids(annotated, boxes_np, labels)

    return annotated, debug


def mjpeg_tracking_generator(
    rtsp_url: str,
    text: str,
    step: int = 20,
    max_fps: float = 5.0,
    duration_sec: Optional[float] = None,
    jpeg_quality: int = 85,
    detection_threshold: float = 0.25,
    text_threshold: float = 0.25,
    timeout_sec: float = 5.0,
) -> Iterator[bytes]:
    video_predictor, image_predictor, dino_pack, device = get_models()
    dino_processor, grounding_model = dino_pack

    query = _normalize_text_query(text)
    if not query:
        raise ValueError("text is required")

    if timeout_sec <= 0:
        timeout_sec = 5.0

    boundary = b"frame"
    start_time = time.monotonic()

    frame_idx = 0
    tracked_boxes: Optional[np.ndarray] = None
    tracked_labels: Optional[List[str]] = None
    last_frame_rgb: Optional[np.ndarray] = None

    # Keep it simple (same style as grounded_phrase.read_rtsp_frame)
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        raise RuntimeError("Failed to open RTSP stream")

    # For live RTSP, reads can temporarily fail; use a simple timeout window
    last_ok_time = time.monotonic()

    try:
        while True:
            if duration_sec is not None and (time.monotonic() - start_time) > duration_sec:
                break

            ok, frame_bgr = cap.read()
            now = time.monotonic()
            if ok and frame_bgr is not None:
                last_ok_time = now
            else:
                if (now - last_ok_time) >= float(timeout_sec):
                    raise TimeoutError(f"Timeout reading frame within {float(timeout_sec):.1f}s")
                time.sleep(0.03)
                continue

            h, w = frame_bgr.shape[:2]

            if frame_idx % max(1, int(step)) == 0:
                image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                last_frame_rgb = image_rgb
                image = Image.fromarray(image_rgb)

                inputs = dino_processor(images=image, text=query, return_tensors="pt").to(device)
                with torch.no_grad():
                    outputs = grounding_model(**inputs)

                results = dino_processor.post_process_grounded_object_detection(
                    outputs,
                    inputs.input_ids,
                    threshold=float(detection_threshold),
                    text_threshold=float(text_threshold),
                    target_sizes=[(h, w)],
                )

                input_boxes = results[0]["boxes"]
                obj_labels = results[0]["labels"]

                if input_boxes is not None and getattr(input_boxes, "shape", None) is not None and input_boxes.shape[0] > 0:
                    image_predictor.set_image(image_rgb)
                    masks, _scores, _logits = image_predictor.predict(
                        point_coords=None,
                        point_labels=None,
                        box=input_boxes,
                        multimask_output=False,
                    )
                    if masks.ndim == 2:
                        masks = masks[None]
                    elif masks.ndim == 4:
                        masks = masks.squeeze(1)

                    # NOTE: The original demo registers masks into the SAM2 video predictor.
                    # In this lightweight RTSP version, we keep the latest masks/boxes and overlay them on subsequent frames.
                    tracked_boxes = input_boxes.detach().cpu().numpy() if torch.is_tensor(input_boxes) else np.asarray(input_boxes)
                    tracked_labels = [str(x) for x in obj_labels]

                    # Optional: overlay masks on keyframes
                    for i in range(min(masks.shape[0], 5)):
                        color = (0, 255, 0) if i % 2 == 0 else (255, 0, 0)
                        frame_bgr = _overlay_mask(frame_bgr, masks[i], color=color, alpha=0.35)

            if tracked_boxes is not None and tracked_labels is not None:
                labels = tracked_labels
                if len(labels) != tracked_boxes.shape[0]:
                    labels = ["obj"] * tracked_boxes.shape[0]
                frame_bgr = _draw_boxes_and_ids(frame_bgr, tracked_boxes, labels)

            ok2, jpg = cv2.imencode(
                ".jpg",
                frame_bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
            )
            if not ok2:
                continue

            payload = jpg.tobytes()
            yield (
                b"--" + boundary + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
                + payload
                + b"\r\n"
            )

            frame_idx += 1
            if max_fps and max_fps > 0:
                time.sleep(max(0.0, 1.0 / float(max_fps)))
    finally:
        cap.release()
