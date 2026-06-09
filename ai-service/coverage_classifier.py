"""Coverage classifier — determines if a legal measure is horizontal or sectoral.

RDTII 2.1 coverage rules:
  - Horizontal: measure applies across ALL sectors / industries / data types
  - Sectoral: measure applies to ONE specific sector (e.g. telecom, finance, health)

Uses keyword heuristics + entity recognition in legal text.
Horizontal and sectoral differences in law:
  - Horizontal: "all sectors", "any person", "any organisation", "across all industries"
  - Sectoral: "telecommunications", "financial services", "health", "banking", etc.
"""

from __future__ import annotations

from typing import Literal

ScopeKind = Literal["horizontal", "sectoral", "unknown"]

# Keywords that strongly indicate a horizontal (cross-sectoral) measure
_HORIZONTAL_KEYWORDS: list[str] = [
    "all sectors", "across sectors", "cross-sectoral", "cross sector",
    "any person", "all persons", "any organization", "any organisation", "any entity",
    "natural person", "legal person", "data subject", "data controller",
    "personal data", "privacy", "data protection",
    "适用于所有行业", "所有行业", "对所有", "任何个人",
    "ทั่วทุกภาคส่วน", "ทุกอุตสาหกรรม",
    "semua sektor", "semua industri",
    "tất cả các ngành",
]

# Keywords that strongly indicate a sectoral (single-sector) measure
_SECTORAL_KEYWORDS: list[str] = [
    # Telecom / ICT
    "telecommunications", "telecom", "telecoms",
    "telecommunication service", "electronic communication",
    "internet service provider", "isp", "internet access",
    "broadband", "mobile network", "frequency spectrum",
    "电信", "通信", "互联网",
    # Financial
    "financial services", "banking", "insurance", "securities",
    "fintech", "payment system", "credit", "financial institution",
    "银行", "金融", "保险", "证券", "支付",
    # Health
    "health", "medical", "healthcare", "hospital", "patient data",
    "医药", "医疗", "健康",
    # Transport / logistics
    "transport", "logistics", "shipping", "aviation", "airline",
    "运输", "物流", "航空",
    # Education
    "education", "educational", "school", "university",
    "教育", "学校",
    # Energy
    "energy", "electricity", "power", "oil", "gas", "mining",
    "能源", "电力", "石油", "天然气",
    # E-commerce
    "e-commerce", "electronic commerce", "online marketplace",
    "电子商务", "电商",
]

# Data types that suggest sectoral scope
_SECTORAL_DATA_TYPES: list[str] = [
    "credit information", "credit data", "financial data",
    "medical data", "health data", "insurance data",
    "telecom data", "traffic data", "location data",
    "credit reporting",
]


def classify_coverage(
    provision_text: str = "",
    source_legislation: str = "",
    indicator_id: str = "",
) -> dict:
    """Classify whether a legal measure is horizontal or sectoral.

    Returns dict with:
      - scope: ScopeKind
      - confidence: float (0.0–1.0)
      - reasons: list[str]
    """
    combined = f"{source_legislation} {provision_text}".lower()

    result: dict = {
        "scope": "unknown",
        "confidence": 0.0,
        "reasons": [],
    }

    horizontal_score = 0
    sectoral_score = 0

    # ── Check horizontal keywords ──
    for kw in _HORIZONTAL_KEYWORDS:
        if kw in combined:
            horizontal_score += 2 if len(kw) > 5 else 1
            result["reasons"].append(f"Horizontal keyword matched: '{kw}'")
            if horizontal_score >= 3:
                break

    # ── Check sectoral keywords ──
    for kw in _SECTORAL_KEYWORDS:
        if kw in combined:
            sectoral_score += 2 if len(kw) > 5 else 1
            result["reasons"].append(f"Sectoral keyword matched: '{kw}'")
            if sectoral_score >= 3:
                break

    # ── Check sectoral data types ──
    for dtype in _SECTORAL_DATA_TYPES:
        if dtype in combined:
            sectoral_score += 1.5
            result["reasons"].append(f"Sectoral data type matched: '{dtype}'")
            break

    # ── Law title heuristics ──
    # If law title mentions a specific sector, it's likely sectoral
    for kw in _SECTORAL_KEYWORDS:
        src_lower = source_legislation.lower()
        if kw in src_lower:
            sectoral_score += 2
            result["reasons"].append(f"Law title references sector '{kw}'")
            break

    # "Act" without sector qualifier in title → more likely horizontal
    if "act" in source_legislation.lower() and sectoral_score == 0:
        horizontal_score += 0.5

    # ── Indicator-specific heuristics ──
    if indicator_id:
        # I7.1 and I7.2: if comprehensive framework exists, default horizontal
        if indicator_id in ("7.1",) and horizontal_score >= 2:
            horizontal_score += 0.5
        # I5.3 is inherently sectoral (telecom)
        if indicator_id == "5.3":
            sectoral_score += 3
            result["reasons"].append("Indicator 5.3 (telecom sector) — inherently sectoral")

    # ── Final decision ──
    if horizontal_score > sectoral_score:
        result["scope"] = "horizontal"
        result["confidence"] = min(0.5 + 0.1 * horizontal_score, 0.95)
    elif sectoral_score > horizontal_score:
        result["scope"] = "sectoral"
        result["confidence"] = min(0.5 + 0.1 * sectoral_score, 0.95)
    else:
        result["scope"] = "unknown"
        result["confidence"] = 0.3
        result["reasons"].append("Equal or no signals for horizontal/sectoral — scope unknown")

    result["confidence"] = round(result["confidence"], 2)
    return result


__all__ = ["classify_coverage", "ScopeKind"]
