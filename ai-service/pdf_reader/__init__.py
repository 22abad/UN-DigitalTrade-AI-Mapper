"""
Unified PDF reader — routes to the correct extraction path.

Pure text  → PyMuPDF  (fast, no OCR)
Scanned    → pdf2pym + Tesseract  (image render → OCR)
"""

from pathlib import Path

from .non_ocr.pymupdf_extractor import extract_text_pure, extract_sections_pure, is_pure_text_pdf
from .ocr_service.tesseract_extractor import extract_text_ocr, extract_sections_ocr


def read_pdf(filepath: str) -> list[str]:
    """Extract text from a PDF, auto-detecting the best method.

    Returns a list of strings, one per page.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    if is_pure_text_pdf(filepath):
        return extract_text_pure(filepath)
    else:
        return extract_text_ocr(filepath)


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
