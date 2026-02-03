"""Minimal HTTP test for grounded phrase API.

Usage (in repo root `Video-Stream-System`):

    python -m backend.api.grounded_phrase.test_grounded_phrase_http \
      --url http://127.0.0.1:8000/api/grounded-phrase/annotate \
      --image ../Grounded-SAM-2/notebooks/images/cars.jpg \
      --prompt "car"

This writes `annotated.jpg` in current directory.
"""

from __future__ import annotations

import argparse
import base64

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, required=True)
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--out", type=str, default="annotated.jpg")
    args = parser.parse_args()

    with open(args.image, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {"image_b64": image_b64, "prompt": args.prompt, "return_debug": True}
    r = requests.post(args.url, json=payload, timeout=300)
    r.raise_for_status()

    with open(args.out, "wb") as f:
        f.write(r.content)

    print("saved:", args.out)
    print("X-Florence-Keys:", r.headers.get("X-Florence-Keys"))


if __name__ == "__main__":
    main()
