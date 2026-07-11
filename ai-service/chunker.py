"""Legal-text chunker — UAX #29 sentence segmentation + token-budget merger.

Strategy:
  1. UAX #29 (uniseg) splits text into Unicode sentences — language-agnostic,
     works correctly for Thai, Vietnamese, Chinese, Arabic, etc.
  2. Sentences are merged into chunks up to CHUNK_CHAR_BUDGET characters.
  3. When a sentence looks like a structural heading (Article / Section / …),
     prefer breaking before it so headings stay at the top of their chunk.
  4. No hard chunk cap — chunk count scales with document size and budget.

Chunk.start / Chunk.end are absolute character offsets into the original
(unmodified) text — required by the anti-hallucination verifier.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from uniseg.sentencebreak import sentences as _uax29_sentences

# ~3 000 chars ≈ 750 tokens — fits comfortably in Gemini's context window
# while keeping chunks small enough for accurate verbatim-quote verification.
_BUDGET = int(os.getenv("CHUNK_CHAR_BUDGET", "3000"))
_MIN_CHARS = int(os.getenv("CHUNK_MIN_CHARS", "200"))

# Structural heading patterns — used as preferred break points, not required.
_HEADING_RE = re.compile(
    r"^\s*(?:"
    r"Article|Section|Clause|Part|Chapter|Schedule|Regulation|Annex|Appendix"
    r"|Art\.?|Sec\.?|Para\.?|Cl\.?"
    r"|第\s*[\d一二三四五六七八九十百千]+\s*条"  # Chinese
    r"|มาตรา\s*\d+"                              # Thai
    r"|Pasal\s*\d+"                              # Indonesian
    r"|Điều\s*\d+"                               # Vietnamese
    r"|(?:\d+\.){1,3}\s+[A-Z]"                  # numbered: 1.2.3 Heading
    r"|\([a-z]\)\s+[A-Z]"                        # lettered: (a) Heading
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Chunk:
    """A slice of legal text with its absolute position in the source document.

    Invariant: ``original_text[start:end] == text``
    """
    text: str
    start: int
    end: int


def regex_legal_chunker(text: str) -> list[Chunk]:
    """Segment *text* into article-level chunks tracking absolute offsets.

    Uses UAX #29 sentence boundaries as atomic units, then merges sentences
    up to CHUNK_CHAR_BUDGET chars. Structural headings act as preferred
    break points so each article starts a fresh chunk where possible.
    """
    if not text:
        return []

    sents = list(_uax29_sentences(text))
    if not sents:
        stripped = text.strip()
        if not stripped:
            return []
        lead = text.index(stripped)
        return [Chunk(text=stripped, start=lead, end=lead + len(stripped))]

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_start = 0   # absolute offset of first char in buf
    buf_chars = 0
    pos = 0         # tracks current position in original text

    def _flush() -> None:
        if not buf:
            return
        raw = "".join(buf)
        stripped = raw.strip()
        if stripped:
            lead = len(raw) - len(raw.lstrip())
            chunks.append(Chunk(
                text=stripped,
                start=buf_start + lead,
                end=buf_start + lead + len(stripped),
            ))

    for sent in sents:
        is_heading = bool(_HEADING_RE.match(sent))
        over_budget = (buf_chars + len(sent) > _BUDGET) and (buf_chars >= _MIN_CHARS)
        at_heading = is_heading

        if buf and (over_budget or at_heading):
            _flush()
            buf = []
            buf_start = pos
            buf_chars = 0

        buf.append(sent)
        buf_chars += len(sent)
        pos += len(sent)

    _flush()

    if chunks:
        return chunks
    stripped = text.strip()
    if not stripped:
        return []
    lead = text.index(stripped)
    return [Chunk(text=stripped, start=lead, end=lead + len(stripped))]
