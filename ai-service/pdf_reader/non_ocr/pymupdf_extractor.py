# PyMuPDF — Pure text PDF extraction
import os
import fitz  # pymupdf


def extract_text_pure(filepath: str) -> list[str]:
    """Extract text from a PDF that has a native text layer.

    Returns a list of page strings.
    """
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        text = page.get_text("text")
        pages.append(text)
    doc.close()
    return pages


def is_pure_text_pdf(filepath: str, threshold: int = 50) -> bool:
    """Check if a PDF has enough extractable text to be classified as pure-text.

    Returns True if the first page yields more than *threshold* characters.
    """
    doc = fitz.open(filepath)
    first_page_text = doc[0].get_text("text").strip()
    doc.close()
    return len(first_page_text) > threshold


def extract_sections_pure(filepath: str, min_section_chars: int = 100) -> list[dict]:
    """Extract text and return section metadata.

    Each section: {page, title, text}
    """
    doc = fitz.open(filepath)
    sections = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if len(text.strip()) < min_section_chars:
            continue
        sections.append({
            "page": page_num + 1,
            "text": text,
            "source": "pymupdf",
        })
    doc.close()
    return sections
