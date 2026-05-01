import re
from typing import List

def regex_legal_chunker(text: str) -> List[str]:
    if not text:
        return []
    heading_tokens = r"Article|Section|Clause|Art\.?|Sec\.?|Paragraph|Para\.?|Chapter|第\s*[\d一二三四五六七八九十百千]+\s*条"
    pattern = re.compile(
        rf"(?m)(^\s*(?:{heading_tokens})\s*[\w\.\-]*\b[\s\S]*?)(?=^\s*(?:{heading_tokens})\s*[\w\.\-]*\b|\Z)", 
        re.IGNORECASE
    )
    chunks = [m.group(1).strip() for m in pattern.finditer(text) if m.group(1).strip()]
    return chunks if chunks else [text.strip()]