# pdf2pym + Tesseract — Scanned / hybrid PDF extraction
import os
import tempfile
from pathlib import Path

import cv2
import pytesseract
from pdf2image import convert_from_path

from ocr_service.openai_fallback import ocr_vision


def render_pages(filepath: str, dpi: int = 300) -> list[Path]:
    """Render each page of a PDF to a PNG image at *dpi* resolution.

    Returns list of temporary image file paths.
    """
    tmpdir = tempfile.mkdtemp(prefix="pdf_reader_")
    images = convert_from_path(filepath, dpi=dpi, output_folder=tmpdir, fmt="png")
    return [Path(img.filename) for img in images]


def preprocess_image(image_path: Path, langs: str = "eng+tha+chi_sim+vie+ind") -> str:
    """Preprocess an image and run Tesseract OCR.

    Steps: grayscale → threshold → denoise → OCR
    """
    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.fastNlMeansDenoising(thresh)

    text = pytesseract.image_to_string(denoised, lang=langs, config="--psm 3")
    return text.strip()


def ocr_with_fallback(image_path: Path, min_chars: int = 50, langs: str = "eng+tha+chi_sim+vie+ind") -> tuple[str, str]:
    """Run Tesseract first; fall back to OpenAI Vision if insufficient.

    Returns (text, source) where source is 'tesseract' or 'openai'.
    """
    text = preprocess_image(image_path, langs=langs)
    if len(text) > min_chars:
        return text, "tesseract"

    # Tesseract insufficient — try OpenAI Vision
    vision_text = ocr_vision(image_path)
    if vision_text and len(vision_text) > min_chars:
        return vision_text, "openai"

    return "", "none"


def extract_text_ocr(filepath: str, langs: str = "eng+tha+chi_sim+vie+ind") -> list[str]:
    """Extract text from a scanned PDF using pdf2pym + Tesseract (→ OpenAI fallback).

    Returns a list of page strings.
    """
    images = render_pages(filepath)
    pages = []
    for img_path in images:
        text, _ = ocr_with_fallback(img_path, langs=langs)
        pages.append(text)
    # Cleanup temp images
    for img in images:
        img.unlink(missing_ok=True)
    return pages


def extract_sections_ocr(filepath: str, min_section_chars: int = 100, langs: str = "eng+tha+chi_sim+vie+ind") -> list[dict]:
    """Extract text per page and return section metadata.

    Each section: {page, text, source}
    """
    images = render_pages(filepath)
    sections = []
    for i, img_path in enumerate(images):
        text, source = ocr_with_fallback(img_path, min_chars=min_section_chars, langs=langs)
        if len(text) < min_section_chars:
            continue
        sections.append({
            "page": i + 1,
            "text": text,
            "source": source,
        })
    # Cleanup
    for img in images:
        img.unlink(missing_ok=True)
    return sections
