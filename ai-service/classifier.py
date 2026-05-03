"""Indicator classifier — decides which RDTII indicators an article touches.

Concrete implementation lands in Commit 3. For now this stub returns the
full P6+P7 indicator list so the pipeline runs end-to-end (the deterministic
scorer will yield 0 on indicators where features are not present).

The real classifier (Commit 3) will be a small transformer or rule-based
matcher that filters the indicator set based on keyword + semantic match.
"""

from __future__ import annotations

from features import list_supported_indicators


def classify_indicator(article_text: str) -> list[str]:
    """Return the RDTII indicator IDs that this article potentially maps to.

    Stub: returns all supported indicators. The real implementation will
    short-list (e.g. by keyword: "transfer abroad" -> ["6.1", "6.4"]).
    """
    if not article_text or not article_text.strip():
        return []
    return list_supported_indicators()
