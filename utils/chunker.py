import re
from typing import List

def regex_legal_chunker(text: str) -> List[str]:
    if not text:
        return []

    # 🛡️ 武器升级 1：OCR 容错装甲
    # 增加了对带点缩写 (Art., Sec., Para.) 的支持，以及中文汉字数字（一二三四）的全面匹配
    heading_tokens = r"Article|Section|Clause|Art\.?|Sec\.?|Paragraph|Para\.?|Chapter|第\s*[\d一二三四五六七八九十百千]+\s*条"

    # 🛡️ 武器升级 2：标号锁定机制
    # 强制匹配条款后面的数字或字母标号（如 Article 1A, Section 2.1），防止误切
    # (?m)^ 确保只切分在行首出现的条款，防止把句子中间的 "According to Article 5" 给切断
    pattern = re.compile(
        rf"(?m)(^\s*(?:{heading_tokens})\s*[\w\.\-]*\b[\s\S]*?)(?=^\s*(?:{heading_tokens})\s*[\w\.\-]*\b|\Z)", 
        re.IGNORECASE
    )

    # 使用 finditer 精准提取捕获组里的内容
    chunks = [m.group(1).strip() for m in pattern.finditer(text) if m.group(1).strip()]

    # 物理兜底：如果这刀切下去发现没有骨头（没匹配到任何标题），就整块返回，绝不丢弃数据
    if not chunks:
        single = text.strip()
        return [single] if single else []

    return chunks