"""Source validator — grades legal sources by hierarchy and enforceability.

RDTII 2.1 data collection requires strict source classification:
  - Primary sources: official legal instruments with legal effect
  - Secondary sources: news, commentaries, academic publications (leads only)

Heuristic scoring based on URL domain, source keywords, and text patterns.
"""

from __future__ import annotations

from typing import Literal

SourceGrade = Literal["primary", "secondary", "unknown"]

# Domains that are authoritative (official government / international org)
_AUTHORITATIVE_DOMAINS: set[str] = {
    # Singapore
    "sso.agc.gov.sg", "www.sso.gov.sg",
    "mti.gov.sg", "www.mti.gov.sg",
    "imda.gov.sg", "www.imda.gov.sg",
    "mas.gov.sg", "www.mas.gov.sg",
    "pdpc.gov.sg", "www.pdpc.gov.sg",
    "egov.gov.sg",
    # Malaysia
    "www.agc.gov.my", "agc.gov.my",
    "www.kkm.gov.my", "kkm.gov.my",
    "www.mcmc.gov.my", "mcmc.gov.my",
    "www.bnm.gov.my", "bnm.gov.my",
    "www.parlimen.gov.my", "parlimen.gov.my",
    "www.federalgazette.agc.gov.my",
    # India
    "www.indiacode.nic.in", "indiacode.nic.in",
    "www.dot.gov.in", "dot.gov.in",
    "www.trai.gov.in", "trai.gov.in",
    "www.meity.gov.in", "meity.gov.in",
    # General government
    ".gov.sg", ".gov.my", ".gov.in",
    ".go.jp", ".go.kr", ".gov.cn",
    ".gov.hk", ".gov.vn", ".gov.th",
    "unescap.org", "www.unescap.org",
    "wto.org", "www.wto.org",
    "oecd.org", "www.oecd.org",
}

_SECONDARY_DOMAINS: set[str] = {
    "wikipedia.org", "en.wikipedia.org",
    "reuters.com", "bloomberg.com",
    "law.com", "lexology.com",
    "onechambers.com",
}

_PRIMARY_KEYWORDS: list[str] = [
    "act", "statute", "code", "constitution", "decree",
    "regulation", "order", "notification",
    "law", "ordinance", "rules", "guidelines",
    "act no", "code of",
]

_SECONDARY_KEYWORDS: list[str] = [
    "news", "article", "blog", "commentary",
    "analysis", "report", "press release",
    "encyclopedia", "law firm",
]


def grade_source(url: str = "", title: str = "", text_snippet: str = "") -> dict:
    """Grade a legal source as primary / secondary / unknown.

    Returns dict with:
      - grade: SourceGrade
      - confidence: 0.0–1.0
      - reasons: list of matching signals
    """
    reasons: list[str] = []
    confidence = 0.0

    target = (url + " " + title + " " + text_snippet).lower()

    # ── Check URL domain for authoritative sources ──
    url_lower = url.lower()
    for domain in _AUTHORITATIVE_DOMAINS:
        if domain in url_lower:
            reasons.append(f"URL domain '{domain}' is an authoritative/official source")
            confidence = max(confidence, 0.95)
            break

    # ── Check for secondary source domains ──
    for domain in _SECONDARY_DOMAINS:
        if domain in url_lower:
            reasons.append(f"URL domain '{domain}' is a secondary/non-official source")
            grade = "secondary"
            confidence = max(confidence, 0.8)
            return {
                "grade": grade,
                "confidence": confidence,
                "reasons": reasons,
                "is_primary": False,
            }

    # ── Check title / text for primary source signals ──
    primary_match_count = 0
    for kw in _PRIMARY_KEYWORDS:
        if kw in target:
            primary_match_count += 1
            if primary_match_count == 1:
                reasons.append(f"Title/text contains primary source keyword: '{kw}'")
            if primary_match_count >= 3:
                break

    if primary_match_count >= 2:
        confidence = max(confidence, 0.7)
    elif primary_match_count == 1:
        confidence = max(confidence, 0.4)

    # ── Check for secondary source signals (counter-indication) ──
    secondary_match = False
    for kw in _SECONDARY_KEYWORDS:
        if kw in target:
            secondary_match = True
            reasons.append(f"Title/text contains secondary source keyword: '{kw}'")
            break

    if secondary_match and primary_match_count == 0:
        return {
            "grade": "secondary",
            "confidence": max(confidence, 0.75),
            "reasons": reasons,
            "is_primary": False,
        }

    # ── Final grade ──
    if primary_match_count >= 2 and not secondary_match:
        grade: SourceGrade = "primary"
    elif primary_match_count >= 1 and confidence >= 0.4:
        grade = "primary"
    else:
        grade = "unknown"

    return {
        "grade": grade,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "is_primary": grade == "primary",
    }


def require_primary_source(url: str = "", title: str = "", text_snippet: str = "") -> dict:
    """Validate that a source is primary; raise structured warning if not."""
    result = grade_source(url, title, text_snippet)
    if not result["is_primary"]:
        result["warning"] = (
            "This source is not a primary/official legal instrument. "
            "Record secondary sources only in the Note column as leads to primary sources. "
            "Do NOT use secondary source text to rewrite the legal meaning of the primary text."
        )
    return result


__all__ = ["grade_source", "require_primary_source", "SourceGrade"]
