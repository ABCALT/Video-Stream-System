import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor


DEFAULT_JPEG_QUALITY = 95


@dataclass(frozen=True)
class GroundedPhraseSettings:
    florence2_model_id: str
    device: str
    use_fp16: bool


def _default_device() -> str:
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _repo_root() -> Path:
    # service.py -> grounded_phrase -> api -> backend -> Video-Stream-System
    here = Path(__file__).resolve()
    return here.parents[4]


def _resolve_model_id(model_id: str) -> str:
    """Resolve a local model folder path against stable bases.

    If `model_id` is a HuggingFace hub repo_id, we leave it unchanged.
    If it's a relative path, resolve it against:
    1) current working directory (common for local dev)
    2) `Video-Stream-System` repo root
    3) repo root's parent (monorepo root, e.g. /home/linrui/demo)
    """

    if not model_id:
        return model_id

    p = Path(model_id)
    if p.is_absolute():
        return str(p)

    # Try relative to current working directory first
    cwd_candidate = (Path.cwd() / p).resolve()
    if cwd_candidate.exists():
        return str(cwd_candidate)

    repo = _repo_root()
    for base in (repo, repo.parent):
        candidate = (base / p).resolve()
        if candidate.exists():
            return str(candidate)

    return model_id


@lru_cache(maxsize=1)
def get_settings() -> GroundedPhraseSettings:
    model_id = _resolve_model_id(os.getenv("FLORENCE2_MODEL_ID", "./Florence-2-large-no-flash-attn"))
    device = os.getenv("FLORENCE2_DEVICE", _default_device())
    use_fp16 = os.getenv("FLORENCE2_FP16", "1") == "1" and device.startswith("cuda")
    return GroundedPhraseSettings(florence2_model_id=model_id, device=device, use_fp16=use_fp16)


@lru_cache(maxsize=1)
def get_florence2() -> Tuple[Any, Any, str]:
    settings = get_settings()

    model = (
        AutoModelForCausalLM.from_pretrained(
            settings.florence2_model_id,
            trust_remote_code=True,
            torch_dtype="float32",
        )
        .eval()
        .to(settings.device)
    )
    processor = AutoProcessor.from_pretrained(settings.florence2_model_id, trust_remote_code=True)

    if settings.use_fp16:
        model = model.to(dtype=torch.float16)

    return model, processor, settings.device


def run_florence2_phrase_grounding(
    image_bgr: np.ndarray,
    prompt: str,
    task_prompt: str = "<CAPTION_TO_PHRASE_GROUNDING>",
) -> Dict[str, Any]:
    model, processor, device = get_florence2()

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)

    text = task_prompt + prompt

    inputs = processor(text=text, images=image_pil, return_tensors="pt").to(device, torch.float16)

    generated_ids = model.generate(
        input_ids=inputs["input_ids"].to(device),
        pixel_values=inputs["pixel_values"].to(device),
        max_new_tokens=1024,
        early_stopping=False,
        do_sample=False,
        num_beams=3,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        generated_text,
        task=task_prompt,
        image_size=(image_pil.width, image_pil.height),
    )
    return parsed


def draw_boxes(
    image_bgr: np.ndarray,
    boxes_xyxy: np.ndarray,
    labels: Optional[List[str]] = None,
) -> np.ndarray:
    out = image_bgr.copy()

    if labels is None:
        labels = ["obj"] * len(boxes_xyxy)

    for (x1, y1, x2, y2), label in zip(boxes_xyxy.astype(int), labels):
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if label:
            cv2.putText(
                out,
                str(label),
                (x1, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

    return out


def phrase_grounding_annotate_frame(
    frame_bgr: np.ndarray,
    prompt: str,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    parsed = run_florence2_phrase_grounding(frame_bgr, prompt)

    results = parsed.get("<CAPTION_TO_PHRASE_GROUNDING>")
    if not results:
        return frame_bgr, parsed

    bboxes = np.array(results.get("bboxes", []), dtype=np.float32)
    labels = results.get("labels", None)
    if bboxes.size == 0:
        return frame_bgr, parsed

    annotated = draw_boxes(frame_bgr, bboxes, labels=labels)
    return annotated, parsed


def read_rtsp_frame(
    rtsp_url: str,
    timeout_sec: float = 5.0,
) -> np.ndarray:
    """Open an RTSP stream and read a single frame.

    Notes:
    - Uses OpenCV `VideoCapture`, which relies on system FFmpeg/GStreamer backend.
    - Implements a simple timeout loop for the first frame.
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
            if time.monotonic() - start >= timeout_sec:
                raise TimeoutError(f"Timeout reading frame within {timeout_sec:.1f}s")
            time.sleep(0.03)

        return frame
    finally:
        cap.release()
