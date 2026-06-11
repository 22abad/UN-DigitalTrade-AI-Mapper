"""
Unified PDF reader — routes to the correct extraction path.

Pure text  → PyMuPDF  (fast, no OCR)
Scanned    → pdf2pym + Tesseract  (image render → OCR)
"""

import logging
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import fitz

from .non_ocr.pymupdf_extractor import (
    _extract_page_filtered,
    _strip_repeated_lines,
    extract_sections_pure,
    is_pure_text_pdf,
    is_garbled,
)
from .ocr_service.tesseract_extractor import (
    _DPI,
    _OCR_WORKERS,
    _TESSERACT_LANGS,
    _render_page,
    _timed_ocr_page,
    extract_sections_ocr,
)
from .ocr_service.openai_fallback import ocr_vision

logger = logging.getLogger(__name__)

# Minimum characters from PyMuPDF before a page is considered "has text".
# Below this threshold the page is treated as image-only and sent to OCR.
_PAGE_TEXT_MIN = int(os.getenv("PDF_PAGE_TEXT_MIN", "80"))


def read_pdf(filepath: str, langs: str = _TESSERACT_LANGS, ocr_mode: str = "tesseract") -> list[str]:
    """Extract text from a PDF with per-page routing.

    Returns a list of strings, one per page.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    t0 = time.perf_counter()
    doc = fitz.open(str(path))
    n_pages = len(doc)
    logger.info("[PDF] read_pdf  pages=%d  file=%s", n_pages, path.name)

    # First pass: extract text layer + detect image blocks for every page.
    pymupdf_pages: list[str] = []
    has_images: list[bool] = []
    for page in doc:
        pymupdf_pages.append(_extract_page_filtered(page))
        blocks = page.get_text("dict")["blocks"]
        has_images.append(any(b["type"] == 1 for b in blocks))

    # A page needs OCR if it has image blocks (scanned content) OR if its
    # text layer yields less than the minimum threshold. Pages that are
    # purely text-layer (no images, enough chars) skip OCR entirely.
    needs_ocr: list[int] = [
        i for i in range(n_pages)
        if has_images[i]
        or len(pymupdf_pages[i].strip()) < _PAGE_TEXT_MIN
        or is_garbled(pymupdf_pages[i])
    ]
    text_count = n_pages - len(needs_ocr)
    logger.info("[PDF] pymupdf_only=%d  needs_ocr=%d  (image_pages=%d  garbled_pages=%d)",
                text_count, len(needs_ocr), sum(has_images),
                sum(1 for i in range(n_pages) if is_garbled(pymupdf_pages[i])))

    if not needs_ocr:
        # All pages have good text — skip OCR entirely.
        doc.close()
        return _strip_repeated_lines(pymupdf_pages)

    # Second pass: OCR only the pages that need it.
    ocr_results: dict[int, str] = {}
    if needs_ocr:
        pipeline_t0 = time.perf_counter()
        if ocr_mode == "openai":
            logger.info("[PDF] OCR mode: openai-vision  pages=%d", len(needs_ocr))
            for i in needs_ocr:
                arr = _render_page(doc, i, _DPI)
                ocr_results[i] = ocr_vision(arr)
        else:
            futures: list[tuple[int, Future]] = []
            with ThreadPoolExecutor(max_workers=_OCR_WORKERS) as pool:
                for i in needs_ocr:
                    arr = _render_page(doc, i, _DPI)
                    fut = pool.submit(_timed_ocr_page, i, n_pages, arr, 50, langs, pipeline_t0)
                    futures.append((i, fut))
            for i, fut in futures:
                text, _ = fut.result()
                ocr_results[i] = text

    doc.close()

    # Merge: for image pages, combine PyMuPDF text layer + OCR so neither
    # loses content (e.g. title in text layer + body in scanned image).
    merged = []
    for i in range(n_pages):
        if i not in ocr_results:
            merged.append(pymupdf_pages[i])
        else:
            ocr_text = ocr_results[i]
            pdf_text = pymupdf_pages[i].strip()
            # Prepend text-layer content only if it adds something OCR missed
            if pdf_text and pdf_text not in ocr_text:
                merged.append(pdf_text + "\n" + ocr_text)
            else:
                merged.append(ocr_text)

    elapsed = time.perf_counter() - t0
    logger.info("[PDF] done  pymupdf=%d  ocr=%d  total=%.1fs", text_count, len(needs_ocr), elapsed)
    return _strip_repeated_lines(merged)


def extract_sections(filepath: str, min_section_chars: int = 100) -> list[dict]:
    """Extract document sections with page metadata.

    Each result: {"page": int, "text": str, "source": str}
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    if is_pure_text_pdf(filepath):
        return extract_sections_pure(filepath, min_section_chars)
    else:
        return extract_sections_ocr(filepath, min_section_chars)


def get_pdf_type(filepath: str) -> str:
    """Return 'pure_text' or 'scanned' for the given PDF."""
    if is_pure_text_pdf(filepath):
        return "pure_text"
    return "scanned"
