"""Legal-text chunker — slices a document into article-level segments.

The chunker tracks each chunk's character offset in the original document.
This is load-bearing for the anti-hallucination kill switch: the verifier
must check that an LLM-emitted `verbatim_quote` exists in the SPECIFIC
chunk the model was given (not just somewhere in the document), and any
absolute char offsets reported to the audit UI must be accurate.

Public API:
    Chunk(text: str, start: int, end: int)
    regex_legal_chunker(text: str) -> list[Chunk]
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """A slice of legal text plus its position in the source document.

    `text` is the stripped chunk content. `start` is the character index
    in the ORIGINAL (unstripped) document where `text` begins; `end` is
    the exclusive end index. By construction: `original_text[start:end] == text`.
    """

    text: str
    start: int
    end: int


_HEADING_TOKENS = (
    r"Article|Section|Clause|Art\.?|Sec\.?|Paragraph|Para\.?|Chapter"
    r"|第\s*[\d一二三四五六七八九十百千]+\s*条" # 中文
    r"|มาตรา\s*\d+"                            # 泰语 (มาตรา = Article)
    r"|Pasal\s*\d+"                            # 印尼语 (Pasal = Article)
    r"|Điều\s*\d+"                             # 越南语 (Điều = Article)
)
_CHUNK_PATTERN = re.compile(
    rf"(?m)(^\s*(?:{_HEADING_TOKENS}).*?(?:\n(?:(?!\s*(?:{_HEADING_TOKENS})).)*)*)",
    re.IGNORECASE | re.DOTALL
)


def _strip_with_offset(raw: str, raw_start: int) -> Chunk | None:
    """Strip `raw` and adjust offsets so they index into the original doc."""
    stripped = raw.strip()
    if not stripped:
        return None
    leading_ws = len(raw) - len(raw.lstrip())
    start = raw_start + leading_ws
    end = start + len(stripped)
    return Chunk(text=stripped, start=start, end=end)


def regex_legal_chunker(text: str) -> list[Chunk]:
    """Slice `text` into article-level chunks tracking absolute offsets.

    If no heading patterns match, returns one chunk covering the whole
    (stripped) document. Empty input returns [].
    """
    if not text:
        return []

    # Lookahead split to keep the heading as part of the chunk
    pattern = rf"(?=^\s*(?:{_HEADING_TOKENS}))"
    parts = re.split(pattern, text, flags=re.MULTILINE)
    
    chunks: list[Chunk] = []
    current_pos = 0
    
    for part in parts:
        if not part.strip():
            current_pos += len(part)
            continue
            
        c = _strip_with_offset(part, current_pos)
        if c is not None:
            chunks.append(c)
        current_pos += len(part)

    return chunks if chunks else [_strip_with_offset(text, 0)] if text.strip() else []
