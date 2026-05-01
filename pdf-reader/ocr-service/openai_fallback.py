"""OpenAI Vision fallback for pages where Tesseract fails."""

import os
from pathlib import Path

from openai import OpenAI


def ocr_vision(image_path: Path) -> str:
    """Send an image to OpenAI GPT-4o for OCR.

    Returns extracted text or empty string on failure.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)

    image_bytes = image_path.read_bytes()
    import base64
    b64 = base64.b64encode(image_bytes).decode()

    mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all text from this document image. Preserve paragraph structure. Return only the extracted text."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        max_tokens=4096,
    )

    return resp.choices[0].message.content or ""
