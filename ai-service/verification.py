"""Verbatim-quote verification — anti-hallucination kill switch."""

import re
import unicodedata
from rapidfuzz import fuzz

def verify_quote(quote: str, original_text: str, fuzzy: bool = True) -> bool:
    """Return True if `quote` can be matched against `original_text`."""
    if not quote or not original_text:
        return False

    # Normalize unicode to NFC to ensure characters match structurally
    q_norm = unicodedata.normalize("NFC", quote)
    o_norm = unicodedata.normalize("NFC", original_text)

    # 1. Strict match
    if q_norm in o_norm:
        return True

    # 2. Relaxed match for Asian scripts: ignore spaces
    q_clean = "".join(q_norm.split())
    o_clean = "".join(o_norm.split())
    if q_clean in o_clean:
        return True

    # 3. Final fallback: rapidfuzz
    if fuzzy:
        return fuzz.partial_ratio(q_norm, o_norm) >= 85.0
        
    return False

def find_quote_offsets(quote: str, original_text: str) -> tuple[int, int]:
    """Find char offsets, assuming verify_quote is already True."""
    if not quote or not original_text or not quote.strip():
        return (-1, -1)

    start = original_text.find(quote)
    if start != -1:
        return start, start + len(quote)

    start = unicodedata.normalize("NFC", original_text).find(
        unicodedata.normalize("NFC", quote)
    )
    if start != -1:
        return start, start + len(quote)

    pattern = r"\s+".join(re.escape(p) for p in quote.split())
    m = re.search(pattern, original_text)
    if m:
        return m.start(), m.end()

    return (-1, -1)
