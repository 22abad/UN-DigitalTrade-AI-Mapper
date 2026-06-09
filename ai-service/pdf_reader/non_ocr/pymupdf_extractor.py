# PyMuPDF — Pure text PDF extraction with watermark filtering
import re
import fitz  # pymupdf


# ── Watermark detection helpers ───────────────────────────────────────────────

# Spans lighter than this luminance threshold are likely watermarks.
# PyMuPDF encodes color as a packed 0xRRGGBB integer (0 = black).
_LUMINANCE_THRESHOLD = 0.70   # 0–1; above this = too light to be body text

# Patterns that identify watermark-like text regardless of color.
_WATERMARK_PATTERNS = [
    re.compile(r'^https?://', re.I),
    re.compile(r'^www\.\S+\.\S+$', re.I),   # www.domain.tld
    re.compile(r'^\S+\.(com|org|gov|cm|ng|ke|gh|za|tz)(\/\S*)?$', re.I),
]


def _is_light(color_int: int) -> bool:
    """Return True if the packed RGB color is above the luminance threshold."""
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance > _LUMINANCE_THRESHOLD


def _is_watermark_text(text: str) -> bool:
    t = text.strip()
    return any(p.match(t) for p in _WATERMARK_PATTERNS)


def _extract_page_filtered(page: fitz.Page) -> str:
    """Extract body text from one page, skipping light-colored and URL-pattern spans."""
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    parts: list[str] = []
    for block in blocks:
        if block.get("type") != 0:   # 0 = text, 1 = image
            continue
        for line in block.get("lines", []):
            line_parts: list[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                color = span.get("color", 0)
                if _is_light(color):
                    continue
                if _is_watermark_text(text):
                    continue
                line_parts.append(text)
            if line_parts:
                parts.append("".join(line_parts))
    return "\n".join(parts)


# ── Repeat-across-pages watermark filter ────────────────────────────────────
# Any normalised line that appears on > threshold fraction of pages is treated
# as a structural watermark and stripped from all pages.

def _strip_repeated_lines(pages: list[str], threshold: float = 0.6) -> list[str]:
    """Remove lines that recur on more than `threshold` fraction of pages."""
    if len(pages) < 3:
        return pages
    from collections import Counter
    normalised_lines: list[list[str]] = []
    for page_text in pages:
        lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
        normalised_lines.append(lines)

    # Count how many pages each distinct line appears on
    page_count: Counter = Counter()
    for lines in normalised_lines:
        for line in set(lines):   # set: count each line once per page
            page_count[line] += 1

    n = len(pages)
    watermark_lines = {line for line, cnt in page_count.items() if cnt / n >= threshold}
    if not watermark_lines:
        return pages

    cleaned = []
    for page_text in pages:
        kept = [ln for ln in page_text.splitlines()
                if ln.strip() not in watermark_lines]
        cleaned.append("\n".join(kept))
    return cleaned


# ── Garbled-text detection ────────────────────────────────────────────────────
# Thai/CJK PDFs with custom font encodings produce Latin-like garbage characters
# instead of proper Unicode. PyMuPDF sees "enough" chars and skips OCR, but
# the text is meaningless. Detection heuristic:
#   1. No non-Latin Unicode (Thai U+0E00–U+0E7F, CJK, Arabic, etc.) present
#   2. Average "word" length far exceeds normal Latin text (>9 chars)
# Both must be true to avoid false-positives on legitimate long English words.

_COMMON_EN = frozenset({
    "the", "and", "for", "that", "this", "with", "are", "was", "not",
    "from", "have", "been", "which", "their", "they", "were", "will",
    "has", "its", "also", "but", "all", "can", "may", "law", "data",
    "act", "shall", "any", "use", "or", "of", "to", "in", "is", "it",
})

_NON_LATIN_RE = re.compile(r"[\u0E00-\u0E7F\u4E00-\u9FFF\u0600-\u06FF\u0400-\u04FF]")


def is_garbled(text: str) -> bool:
    """Return True if PyMuPDF text looks like broken font-encoding output."""
    if not text.strip():
        return False
    # If real non-Latin characters are present, encoding is working fine
    if _NON_LATIN_RE.search(text):
        return False
    words = [w for w in text.split() if len(w) >= 2]
    if not words:
        return False
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len <= 9:
        return False
    # High avg word length + no recognisable English words → garbled
    known = sum(1 for w in words if w.lower() in _COMMON_EN)
    return (known / len(words)) < 0.05


# ── Text-page confidence scoring ───────────────────────────────────────────────
# For pages extracted via PyMuPDF text layer, we compute a confidence score
# based on garbled-character ratio and known-word density.

_LATIN_START = ord("A")
_LATIN_END = ord("z")
_DIGIT_START = ord("0")
_DIGIT_END = ord("9")


def text_confidence(text: str) -> float:
    """Return 0.0–1.0 confidence that a text-layer page has clean content.

    Uses two signals:
    - Garbled char ratio: non-ASCII/non-Latin printable chars.
    - Known-word rate: proportion of words that look like real language.
    Returns 0.5 as baseline for short/empty pages.
    """
    if not text.strip():
        return 0.0
    words = [w for w in text.split() if len(w) >= 2]
    if not words:
        return 0.3

    # Signal 1: printable ASCII ratio (low = garbled)
    total_chars = sum(1 for c in text if c.isprintable())
    ascii_chars = sum(1 for c in text if c.isprintable() and ord(c) <= 0x7F)
    ascii_ratio = ascii_chars / total_chars if total_chars else 0.0

    # Signal 2: known-word rate (lower = more likely garbled)
    known = sum(1 for w in words if w.lower() in _COMMON_EN)
    known_rate = known / len(words)

    # Signal 3: average word length (extremely long = garbled)
    avg_len = sum(len(w) for w in words) / len(words)
    len_score = 1.0 - min(1.0, max(0.0, (avg_len - 9) / 15))

    conf = 0.4 * ascii_ratio + 0.35 * known_rate + 0.25 * len_score
    return max(0.0, min(1.0, conf))

def extract_text_pure(filepath: str) -> list[str]:
    """Extract text from a native-text PDF, filtering watermarks."""
    doc = fitz.open(filepath)
    pages = [_extract_page_filtered(page) for page in doc]
    doc.close()
    return _strip_repeated_lines(pages)


def is_pure_text_pdf(filepath: str, threshold: int = 50) -> bool:
    """Return True if the first page yields more than *threshold* body-text chars."""
    doc = fitz.open(filepath)
    text = _extract_page_filtered(doc[0]).strip()
    doc.close()
    return len(text) > threshold


def extract_sections_pure(filepath: str, min_section_chars: int = 100) -> list[dict]:
    """Extract sections with page metadata, watermarks removed."""
    doc = fitz.open(filepath)
    raw_pages = [_extract_page_filtered(page) for page in doc]
    doc.close()
    pages = _strip_repeated_lines(raw_pages)
    sections = []
    for i, text in enumerate(pages):
        if len(text.strip()) >= min_section_chars:
            sections.append({"page": i + 1, "text": text, "source": "pymupdf"})
    return sections
