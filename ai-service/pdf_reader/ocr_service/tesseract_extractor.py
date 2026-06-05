# pdf2image + Tesseract — Scanned / hybrid PDF extraction
#
# Pipeline: fitz renders each page → immediately submitted to OCR thread pool
# → no temp files, no blocking wait for all renders to finish first.
import logging
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor

import cv2
import numpy as np
import pytesseract

from .openai_fallback import ocr_vision

logger = logging.getLogger(__name__)

_OCR_WORKERS = int(os.getenv("OCR_WORKERS", str(min(os.cpu_count() or 4, 8))))
_TESSERACT_LANGS = os.getenv("TESSERACT_LANGS", "eng")
_DPI = int(os.getenv("OCR_DPI", "150"))
_SLOW_PAGE_THRESHOLD = float(os.getenv("OCR_SLOW_PAGE_S", "5.0"))


# ── Low-level OCR helpers ─────────────────────────────────────────────────────

def _ocr_array(img_array: np.ndarray, langs: str = _TESSERACT_LANGS) -> str:
    """Preprocess a RGB numpy array and run Tesseract OCR."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.fastNlMeansDenoising(thresh)
    return pytesseract.image_to_string(denoised, lang=langs, config="--psm 3").strip()



def _ocr_array_with_fallback(
    img_array: np.ndarray,
    min_chars: int = 50,
    langs: str = _TESSERACT_LANGS,
) -> tuple[str, str]:
    """Tesseract first (local, free); OpenAI Vision fallback if result too short."""
    text = _ocr_array(img_array, langs=langs)
    if len(text) >= min_chars:
        return text, "tesseract"
    vision_text = ocr_vision(img_array)
    if vision_text and len(vision_text) >= min_chars:
        return vision_text, "openai"
    return "", "none"


def _timed_ocr_page(
    page_num: int,
    n_pages: int,
    img_array: np.ndarray,
    min_chars: int,
    langs: str,
    pipeline_t0: float,
) -> tuple[str, str]:
    """OCR one page and emit a per-page INFO log line as soon as it completes."""
    t_page = time.perf_counter()
    text, source = _ocr_array_with_fallback(img_array, min_chars, langs)
    page_s = time.perf_counter() - t_page
    total_s = time.perf_counter() - pipeline_t0

    tag = f"[OCR] page {page_num + 1:>3}/{n_pages}"
    detail = f"src={source:<10}  chars={len(text):<5d}  page={page_s:5.1f}s  elapsed={total_s:6.1f}s"

    if source == "openai":
        logger.info("%s  %s  (tesseract returned too little)", tag, detail)
    elif page_s >= _SLOW_PAGE_THRESHOLD:
        logger.warning("%s  %s  *** slow page ***", tag, detail)
    else:
        logger.info("%s  %s", tag, detail)

    return text, source


# ── fitz page renderer ────────────────────────────────────────────────────────

def _render_page(doc, page_num: int, dpi: int) -> np.ndarray:
    """Render one PDF page to an RGB numpy array using PyMuPDF."""
    import fitz  # lazy — only needed on the scanned path
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    pix = doc[page_num].get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return arr.copy()  # copy before pix is GC'd


# ── Public API ────────────────────────────────────────────────────────────────

def extract_text_ocr(filepath: str, langs: str = _TESSERACT_LANGS) -> list[str]:
    """Extract text from a scanned PDF — pipelined fitz render + parallel Tesseract.

    fitz renders each page and immediately submits it to the OCR thread pool,
    so rendering and OCR overlap instead of running sequentially.
    No temp files are written — pages stay as numpy arrays in memory.
    """
    import fitz

    t0 = time.perf_counter()
    doc = fitz.open(filepath)
    n_pages = len(doc)
    logger.info("[OCR] start  pages=%d  workers=%d  dpi=%d  slow_threshold=%.0fs",
                n_pages, _OCR_WORKERS, _DPI, _SLOW_PAGE_THRESHOLD)

    # Render all pages first (single-threaded fitz), then submit OCR jobs.
    # We log render time separately so we can distinguish fitz vs Tesseract cost.
    t_render = time.perf_counter()
    futures: list[Future] = []
    with ThreadPoolExecutor(max_workers=_OCR_WORKERS) as pool:
        for i in range(n_pages):
            arr = _render_page(doc, i, _DPI)
            futures.append(pool.submit(_timed_ocr_page, i, n_pages, arr, 50, langs, t0))

    render_s = time.perf_counter() - t_render
    logger.info("[OCR] all pages submitted to thread pool  render=%.1fs", render_s)

    # Collect in page order — _timed_ocr_page already logged each page as it finished.
    results = [f.result() for f in futures]

    pages = [text for text, _ in results]
    sources = [src for _, src in results]
    none_count = sources.count("none")
    openai_count = sources.count("openai")
    tesseract_count = sources.count("tesseract")
    total_chars = sum(len(p) for p in pages)
    total_s = time.perf_counter() - t0
    avg_s = total_s / n_pages if n_pages else 0

    logger.info(
        "[OCR] done  pages=%d  chars=%d  tesseract=%d  openai=%d  empty=%d  "
        "total=%.1fs  avg=%.2fs/page",
        n_pages, total_chars, tesseract_count, openai_count, none_count,
        total_s, avg_s,
    )
    return pages


def extract_sections_ocr(
    filepath: str,
    min_section_chars: int = 100,
    langs: str = _TESSERACT_LANGS,
) -> list[dict]:
    """Extract text per page with section metadata — pipelined fitz + Tesseract."""
    import fitz

    t0 = time.perf_counter()
    doc = fitz.open(filepath)
    n_pages = len(doc)
    logger.info("[OCR] sections start  pages=%d  workers=%d  dpi=%d",
                n_pages, _OCR_WORKERS, _DPI)

    futures: list[tuple[int, Future]] = []
    with ThreadPoolExecutor(max_workers=_OCR_WORKERS) as pool:
        for i in range(n_pages):
            arr = _render_page(doc, i, _DPI)
            fut = pool.submit(_timed_ocr_page, i, n_pages, arr, min_section_chars, langs, t0)
            futures.append((i, fut))

    sections = []
    for i, fut in futures:
        text, source = fut.result()
        if len(text) >= min_section_chars:
            sections.append({"page": i + 1, "text": text, "source": source})

    logger.info("[OCR] sections done  kept=%d/%d  total=%.1fs",
                len(sections), n_pages, time.perf_counter() - t0)
    return sections


# ── Legacy helpers (kept for any direct callers) ──────────────────────────────

def render_pages(filepath: str, dpi: int = _DPI):
    """Kept for backward compatibility — prefer extract_text_ocr directly."""
    import fitz
    from pathlib import Path
    import tempfile
    doc = fitz.open(filepath)
    tmpdir = tempfile.mkdtemp(prefix="pdf_reader_")
    t0 = time.perf_counter()
    paths = []
    for i in range(len(doc)):
        arr = _render_page(doc, i, dpi)
        p = Path(tmpdir) / f"page_{i:04d}.png"
        cv2.imwrite(str(p), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        paths.append(p)
    logger.info("[fitz] rendered %d pages  %.1fs", len(paths), time.perf_counter() - t0)
    return paths


def preprocess_image(image_path, langs: str = _TESSERACT_LANGS) -> str:
    """Kept for backward compatibility."""
    import cv2 as _cv2
    img = _cv2.imread(str(image_path))
    return _ocr_array(_cv2.cvtColor(img, _cv2.COLOR_BGR2RGB), langs)


def ocr_with_fallback(image_path, min_chars: int = 50, langs: str = _TESSERACT_LANGS):
    """Kept for backward compatibility."""
    import cv2 as _cv2
    img = _cv2.imread(str(image_path))
    arr = _cv2.cvtColor(img, _cv2.COLOR_BGR2RGB)
    return _ocr_array_with_fallback(arr, min_chars, langs)
