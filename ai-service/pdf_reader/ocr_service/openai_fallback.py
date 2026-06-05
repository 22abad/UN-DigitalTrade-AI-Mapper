"""OpenAI Vision OCR — primary OCR path, Tesseract is the fallback."""

import base64
import os
from pathlib import Path
from typing import Union

import cv2
import numpy as np


def _to_b64_png(image: Union[np.ndarray, Path]) -> str:
    """Convert a numpy RGB array or file path to a base64-encoded PNG string."""
    if isinstance(image, np.ndarray):
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        _, buf = cv2.imencode(".png", bgr)
        return base64.b64encode(buf.tobytes()).decode()
    return base64.b64encode(Path(image).read_bytes()).decode()


def ocr_vision(image: Union[np.ndarray, Path]) -> str:
    """Send a page image to GPT-4o for OCR.

    Accepts either a numpy RGB array (from the fitz pipeline) or a file Path
    (legacy callers). Returns extracted text or empty string on failure.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        b64 = _to_b64_png(image)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all text from this document image exactly as written. "
                            "Preserve paragraph structure and line breaks. "
                            "Return only the extracted text, no commentary."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""
