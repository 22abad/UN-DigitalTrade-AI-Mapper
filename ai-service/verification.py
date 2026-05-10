"""Verbatim-quote verification — anti-hallucination kill switch."""

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
    # Simplified version for demo speed
    start = original_text.find(quote)
    if start == -1:
        # Fallback to normalized search
        start = unicodedata.normalize("NFC", original_text).find(
            unicodedata.normalize("NFC", quote)
        )
    return start, start + len(quote)
