"""Verbatim-quote verification — the anti-hallucination kill switch.

Concrete implementation lands in Commit 3. For now this stub provides a
permissive substring check so the pipeline is testable end-to-end.

Why this matters:
    Every IndicatorMapping carries a `verbatim_quote`. Before the mapping
    is returned to the caller, the verifier confirms the quote is a literal
    substring of the source text. If not, the mapping is rejected — the
    LLM hallucinated.
"""

from __future__ import annotations


def verify_quote(quote: str, original_text: str) -> bool:
    """Return True if `quote` is a substring of `original_text`.

    The strict version (Commit 3) will:
        - normalise whitespace / unicode
        - tolerate small OCR-induced character substitutions via fuzzy match
        - compute character offsets

    For now: simple stripped-substring check.
    """
    if not quote or not original_text:
        return False
    return quote.strip() in original_text


def find_quote_offsets(quote: str, original_text: str) -> tuple[int, int]:
    """Return (start, end) offsets for `quote` in `original_text`, or (-1, -1) if not found."""
    if not quote or not original_text:
        return (-1, -1)
    start = original_text.find(quote.strip())
    if start == -1:
        return (-1, -1)
    return (start, start + len(quote.strip()))
