"""Verbatim-quote verification — the anti-hallucination kill switch.

Every IndicatorMapping carries a `verbatim_quote`. Before the mapping is
returned to the caller, the verifier confirms the quote can be matched
against the source text. If not, the mapping is rejected — the LLM
hallucinated.

Strategy:
    1. Strict substring match after whitespace + Unicode (NFC) normalization
       on both sides.
    2. If `fuzzy=True` and strict fails: rapidfuzz `partial_ratio` >= 90 on
       the normalized strings. `partial_ratio` already performs an optimal
       sliding-window comparison of length(quote) against original_text, so
       no manual windowing is required.

`find_quote_offsets` returns indices into the ORIGINAL (un-normalized)
string. To keep that mapping straightforward, we first attempt a literal
`str.find`, and if that fails fall back to a flexible-whitespace regex
built from the quote's tokens. This avoids the index-arithmetic minefield
of normalizing and then trying to map positions back.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

_FUZZY_THRESHOLD = 90.0


def _normalize(text: str) -> str:
    """Collapse whitespace and apply NFC Unicode normalization."""
    nfc = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", nfc).strip()


def verify_quote(quote: str, original_text: str, fuzzy: bool = True) -> bool:
    """Return True if `quote` can be matched against `original_text`.

    Args:
        quote: The candidate quote (e.g. extracted by an LLM).
        original_text: The source text the quote was supposedly drawn from.
        fuzzy: If True, fall back to rapidfuzz `partial_ratio` >= 90 when
            strict substring matching fails.
    """
    if not quote or not original_text:
        return False

    norm_quote = _normalize(quote)
    norm_original = _normalize(original_text)

    if not norm_quote or not norm_original:
        return False

    # 1. Strict substring on normalized strings
    if norm_quote in norm_original:
        return True

    # 2. Fuzzy fallback — partial_ratio handles the sliding window for us
    if fuzzy:
        score = fuzz.partial_ratio(norm_quote, norm_original)
        if score >= _FUZZY_THRESHOLD:
            return True

    return False


def find_quote_offsets(quote: str, original_text: str) -> tuple[int, int]:
    """Return (start, end) char offsets within `original_text`, or (-1, -1).

    Always operates on the ORIGINAL string indices (not the normalized one).

    Strategy:
        1. Try `str.find` literally.
        2. Fall back to a flexible-whitespace regex built from the quote's
           tokens. Each token is `re.escape`'d so punctuation in the quote
           is treated literally.
    """
    if not quote or not original_text:
        return (-1, -1)

    stripped = quote.strip()
    if not stripped:
        return (-1, -1)

    # 1. Literal substring match — preserves indices trivially.
    idx = original_text.find(stripped)
    if idx != -1:
        return (idx, idx + len(stripped))

    # 2. Flexible-whitespace fallback. Split on whitespace, escape each
    # token, rejoin with `\s+`. This tolerates the quote/original differing
    # in spacing or line breaks while still matching the original indices.
    tokens = stripped.split()
    if not tokens:
        return (-1, -1)
    pattern = r"\s+".join(re.escape(tok) for tok in tokens)
    match = re.search(pattern, original_text)
    if match is None:
        return (-1, -1)
    return (match.start(), match.end())
