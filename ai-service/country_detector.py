"""Country detection from legal text, URL, or document content.

Heuristics ranked by reliability:
  1. URL domain TLD (.th, .in, .gov.cn, .sg, .au, .ph)
  2. Legal instrument name keywords ("DPDP Act 2023" → India, "PIPL" → China)
  3. Language script (Thai → Thailand, Chinese → China/Singapore)
  4. Jurisdiction-specific terms ("data fiduciary" → India, "adequate decision" → EU)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# ── ISO 3166-1 alpha-3 country codes supported by the frontend ──────────
KNOWN_COUNTRIES: dict[str, str] = {
    "CHN": "China",
    "IND": "India",
    "SGP": "Singapore",
    "THA": "Thailand",
    "AUS": "Australia",
    "PHL": "Philippines",
    "JPN": "Japan",
    "KOR": "South Korea",
    "IDN": "Indonesia",
    "MYS": "Malaysia",
    "VNM": "Vietnam",
    "BRN": "Brunei",
    "KHM": "Cambodia",
    "LAO": "Laos",
    "MMR": "Myanmar",
    "NPL": "Nepal",
    "BGD": "Bangladesh",
    "PAK": "Pakistan",
    "LKA": "Sri Lanka",
    "MNG": "Mongolia",
    "KAZ": "Kazakhstan",
    "UZB": "Uzbekistan",
    "NZL": "New Zealand",
    "FJI": "Fiji",
}

# ── URL TLD → country mapping ──────────────────────────────────────────
_TLD_MAP: dict[str, str] = {
    "cn": "CHN",
    "hk": "CHN",
    "mo": "CHN",
    "in": "IND",
    "sg": "SGP",
    "th": "THA",
    "au": "AUS",
    "ph": "PHL",
    "jp": "JPN",
    "kr": "KOR",
    "id": "IDN",
    "my": "MYS",
    "vn": "VNM",
    "bn": "BRN",
    "kh": "KHM",
    "la": "LAO",
    "mm": "MMR",
    "np": "NPL",
    "bd": "BGD",
    "pk": "PAK",
    "lk": "LKA",
    "mn": "MNG",
    "kz": "KAZ",
    "uz": "UZB",
    "nz": "NZL",
    "fj": "FJI",
}

# ── Known legal instrument keywords → country ───────────────────────────
# Matched against combined text + source_legislation + URL
_LAW_KEYWORDS: list[tuple[str, str, float]] = [
    # India
    (r"\bDPDP\s*(?:Act|Bill|Rules)?\b", "IND", 0.95),
    (r"Digital Personal Data Protection", "IND", 0.95),
    (r"data\s+fiduciar", "IND", 0.85),
    (r"data\s+principal", "IND", 0.85),
    (r"IT\s*\(?Amendment\)?\s*Act", "IND", 0.80),
    (r"Information Technology Act.*2000", "IND", 0.80),
    (r"SPDI\s*Rules?", "IND", 0.80),
    (r"MeitY?", "IND", 0.70),
    # China
    (r"个人信息保护法", "CHN", 0.95),
    (r"Personal Information Protection Law", "CHN", 0.95),
    (r"PIPL", "CHN", 0.95),
    (r"数据安全法", "CHN", 0.95),
    (r"Data Security Law", "CHN", 0.90),
    (r"网络安全法", "CHN", 0.90),
    (r"Cybersecurity Law", "CHN", 0.90),
    (r"个人信息", "CHN", 0.60),
    (r"跨境数据流动安全评估", "CHN", 0.80),
    (r"Security Assessment.*Cross.?Border", "CHN", 0.70),
    # Singapore
    (r"Personal Data Protection Act 2012", "SGP", 0.95),
    (r"PDPA[.\s]*2012", "SGP", 0.90),
    (r"Personal Data Protection Commission", "SGP", 0.90),
    (r"PDPC", "SGP", 0.70),
    (r"Do Not Call\s*Register", "SGP", 0.80),
    # Thailand
    (r"Personal Data Protection Act B\.?E\.?\s*2562", "THA", 0.95),
    (r"PDPA[.\s]*B\.?E\.?", "THA", 0.90),
    (r"พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล", "THA", 0.95),
    (r"พ\.?ร\.?บ\.?คุ้มครองข้อมูลส่วนบุคคล", "THA", 0.95),
    (r"สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล", "THA", 0.90),
    # Australia
    (r"Privacy Act 1988", "AUS", 0.95),
    (r"Australian Privacy Principles", "AUS", 0.90),
    (r"OAIC", "AUS", 0.80),
    (r"Notifiable Data Breaches", "AUS", 0.80),
    (r"Consumer Data Right", "AUS", 0.80),
    # Philippines
    (r"Republic Act\s*(?:No\.\s*)?10173", "PHL", 0.95),
    (r"Data Privacy Act of 2012", "PHL", 0.95),
    (r"National Privacy Commission", "PHL", 0.90),
    (r"NPC\b.*(?:Circular|Advisory)", "PHL", 0.75),
    # Japan
    (r"Act on Protection of Personal Information", "JPN", 0.90),
    (r"APPI", "JPN", 0.90),
    (r"個人情報保護法", "JPN", 0.90),
    (r"PPC\b.*Japan", "JPN", 0.70),
    # South Korea
    (r"Personal Information Protection Act", "KOR", 0.85),
    (r"PIPA", "KOR", 0.85),
    (r"정보통신망법", "KOR", 0.80),
    # Indonesia
    (r"Law\s*(?:No\.\s*)?27 of 2022", "IDN", 0.85),
    (r"Undang.?Undang Perlindungan Data Pribadi", "IDN", 0.90),
    (r"UU PDP", "IDN", 0.85),
    # Vietnam
    (r"Decree.*13/2023", "VNM", 0.85),
    (r"Personal Data Protection.*Decree", "VNM", 0.85),
    (r"Nghị định.*bảo vệ dữ liệu", "VNM", 0.85),
    # Malaysia
    (r"Personal Data Protection Act 2010", "MYS", 0.90),
    (r"PDPA 2010", "MYS", 0.85),
    # EU/GDPR (generic — may overlap with many countries)
    (r"GDPR", "CHN", 0.30),  # low confidence, many countries cite GDPR
]

# ── Language script → country heuristics ────────────────────────────────
_SCRIPT_THAI = re.compile(r"[\u0E00-\u0E7F]")
_SCRIPT_CHINESE = re.compile(r"[\u4E00-\u9FFF]")
_SCRIPT_KOREAN = re.compile(r"[\uAC00-\uD7AF]")
_SCRIPT_JAPANESE_KANA = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")

# ── Domain-specific government domains → country ───────────────────────
_GOV_DOMAIN_MAP: dict[str, str] = {
    "gov.cn": "CHN",
    "nic.in": "IND",
    "gov.sg": "SGP",
    "go.th": "THA",
    "gov.au": "AUS",
    "gov.ph": "PHL",
    "go.jp": "JPN",
    "go.kr": "KOR",
    "go.id": "IDN",
    "gov.my": "MYS",
    "gov.vn": "VNM",
}


def detect_country_from_url(url: str) -> dict:
    """Detect country from URL domain analysis.

    Returns {"code": "THA", "name": "Thailand", "confidence": 0.95, "source": "url_tld"}
    or {"code": None, "confidence": 0.0, "source": "none"} on failure.
    """
    if not url:
        return {"code": None, "confidence": 0.0, "source": "none"}
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except Exception:
        return {"code": None, "confidence": 0.0, "source": "none"}

    # Exact domain match (gov.cn, nic.in, etc.)
    for gov_domain, code in _GOV_DOMAIN_MAP.items():
        if domain.endswith(gov_domain):
            return {
                "code": code,
                "name": KNOWN_COUNTRIES.get(code, code),
                "confidence": 0.95,
                "source": "url_gov_domain",
            }

    # TLD match
    if "." in domain:
        tld = domain.rsplit(".", 1)[-1]
        code = _TLD_MAP.get(tld)
        if code:
            return {
                "code": code,
                "name": KNOWN_COUNTRIES.get(code, code),
                "confidence": 0.85,
                "source": "url_tld",
            }

    return {"code": None, "confidence": 0.0, "source": "none"}


def detect_country_from_text(text: str, source_legislation: str = "") -> dict:
    """Detect country from legal text keywords and language script.

    Returns highest-confidence match across all signals.
    """
    combined = f"{source_legislation} {text}".lower()
    results: list[dict] = []

    # Signal 1: legal instrument keywords
    for pattern, code, conf in _LAW_KEYWORDS:
        if re.search(pattern, combined, re.IGNORECASE):
            results.append({
                "code": code,
                "name": KNOWN_COUNTRIES.get(code, code),
                "confidence": conf,
                "source": f"keyword: {pattern[:40]}",
            })

    # Signal 2: language script
    thai_chars = len(_SCRIPT_THAI.findall(text))
    chinese_chars = len(_SCRIPT_CHINESE.findall(text))
    korean_chars = len(_SCRIPT_KOREAN.findall(text))
    japanese_chars = len(_SCRIPT_JAPANESE_KANA.findall(text))

    total_chars = max(len(text.strip()), 1)
    thai_ratio = thai_chars / total_chars
    chinese_ratio = chinese_chars / total_chars

    if thai_ratio > 0.05:
        results.append({
            "code": "THA",
            "name": "Thailand",
            "confidence": min(0.7 + thai_ratio, 0.95),
            "source": "thai_script",
        })
    if chinese_ratio > 0.10:
        # Chinese could be China or Singapore — can't tell from script alone
        results.append({
            "code": "CHN",
            "name": "China",
            "confidence": min(0.5 + chinese_ratio * 0.5, 0.7),
            "source": "chinese_script",
        })

    if not results:
        return {"code": None, "confidence": 0.0, "source": "none"}

    best = max(results, key=lambda r: r["confidence"])
    return best


def detect_country(
    text: str = "",
    source_url: str = "",
    source_legislation: str = "",
) -> dict:
    """Two-stage country detection: URL first, then text keywords/script.

    Returns:
        {"code": "IND", "name": "India", "confidence": 0.95,
         "source": "keyword: DPDP Act", "detected": True}

    When detection fails:
        {"code": None, "confidence": 0.0, "source": "none", "detected": False}
    """
    # Stage 1: URL domain (highest precision)
    if source_url:
        result = detect_country_from_url(source_url)
        if result["code"]:
            result["detected"] = True
            return result

    # Stage 2: text keywords + language script
    result = detect_country_from_text(text, source_legislation)
    if result["code"]:
        result["detected"] = True
        return result

    return {"code": None, "confidence": 0.0, "source": "none", "detected": False}
