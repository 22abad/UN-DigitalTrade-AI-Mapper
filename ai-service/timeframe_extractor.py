"""Timeframe extractor — determines legal instrument status and timeline.

RDTII 2.1 data collection format requirements:
  - Include: Month and year (came into force), time of amendments (if any)
  - Indicators about signatory status: provide when agreement came into force

Distinguishes:
  - In force
  - Amended (with date)
  - Repealed
  - Transitional
  - Not yet effective
  - Draft / consultation paper (excluded from RDTII)
"""

from __future__ import annotations

import re
from typing import Literal

TimeframeStatus = Literal[
    "in_force",
    "amended",
    "repealed",
    "transitional",
    "not_yet_effective",
    "draft",
    "unknown",
]

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
    # Chinese month abbreviations
    "一月": 1, "二月": 2, "三月": 3, "四月": 4,
    "五月": 5, "六月": 6, "七月": 7, "八月": 8,
    "九月": 9, "十月": 10, "十一月": 11, "十二月": 12,
}


def _find_date(text: str) -> str | None:
    """Extract a date string from text using regex patterns.

    Returns MM/YYYY format string when possible.
    """
    patterns = [
        # "1 January 2024"  (DD MonthName YYYY)
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
        # "January 1, 2024"  (MonthName DD, YYYY)
        r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})",
        # "June 2022"  (standalone MonthName YYYY)
        r"(?:^|\s)(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})(?:\s|$|[,.])",
        # "2024-01" (ISO year-month)
        r"(\d{4})-(\d{1,2})(?:-\d{1,2})?",
        # "2024/01" (slash year-month)
        r"(\d{4})/(\d{1,2})(?:/\d{1,2})?",
        # "2024年1月1日" (Chinese date)
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        # "2024年1月" (Chinese year-month)
        r"(\d{4})年(\d{1,2})月",
        # "B.E. 2565" (Thai Buddhist Era)
        r"B\.E\.\s*(\d{4})",
        # "since June 2022", "effective June 2022"
        r"(?:since|from|effective|enforced?)\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            groups = m.groups()

            # Case A: 3 groups — DD MonthName YYYY or MonthName DD YYYY
            if len(groups) == 3:
                a, b, c = groups
                if b.lower() in MONTH_NAMES:
                    month = MONTH_NAMES[b.lower()]
                    return f"{month:02d}/{c}"
                elif a.lower() in MONTH_NAMES:
                    month = MONTH_NAMES[a.lower()]
                    return f"{month:02d}/{c}"
                # Chinese YYYY年MM月DD日
                elif re.match(r"^\d{1,2}$", b):
                    return f"{int(b):02d}/{a}"
                else:
                    return f"{int(b):02d}/{a}"

            # Case B: 2 groups — MonthName YYYY or Chinese/ISO YYYY-MM
            if len(groups) == 2:
                a, b = groups
                if a.lower() in MONTH_NAMES:
                    month = MONTH_NAMES[a.lower()]
                    return f"{month:02d}/{b}"
                elif re.match(r"^\d{4}$", a) and re.match(r"^\d{1,2}$", b):
                    # Chinese YYYY年MM月 or ISO YYYY-MM
                    return f"{int(b):02d}/{a}"
                elif b.lower() in MONTH_NAMES:
                    month = MONTH_NAMES[b.lower()]
                    return f"{month:02d}/{a}"

            # Case C: 1 group — B.E. year
            if len(groups) == 1:
                try:
                    be_year = int(groups[0])
                    ce_year = be_year - 543
                    return f"01/{ce_year}"
                except ValueError:
                    pass

    return None


def _find_be_date(text: str) -> str | None:
    """Extract and convert Buddhist Era dates to CE."""
    m = re.search(r"B\.E\.\s*(\d{4})", text)
    if m:
        be_year = int(m.group(1))
        ce_year = be_year - 543
        return f"01/{ce_year}"
    m = re.search(r"พ\.ศ\.\s*(\d{4})", text)
    if m:
        be_year = int(m.group(1))
        ce_year = be_year - 543
        return f"01/{ce_year}"
    return None


_STATUS_PATTERNS: dict[TimeframeStatus, list[str]] = {
    "draft": [
        "draft", "consultation paper", "white paper", "green paper",
        "for public consultation", "for comment", "proposed",
        "草案", "征求意见稿", "送审稿",
    ],
    "repealed": [
        "repealed", "repeal", "superseded", "replaced by",
        "废除", "废止", "取代",
    ],
    "amended": [
        "amended", "amendment", "amending",
        "修正", "修订", "修正案",
    ],
    "not_yet_effective": [
        "not yet effective", "not in force", "尚未生效", "未生效",
    ],
    "transitional": [
        "transitional", "transition", "过渡期", "过渡",
    ],
    "in_force": [
        "in force", "enters into force", "effective", "enforced",
        "promulgated", "adopted", "enacted",
        "生效", "施行", "实施", "通过", "公布",
    ],
}


def extract_timeframe(
    text: str = "",
    source_legislation: str = "",
    source_url: str = "",
) -> dict:
    """Extract timeframe status and dates from legal text.

    Returns dict with:
      - status: TimeframeStatus
      - in_force_date: str (MM/YYYY or None)
      - last_amended_date: str (MM/YYYY or None)
      - repealed_date: str (MM/YYYY or None)
      - confidence: float (0.0–1.0)
      - status_evidence: list[str]
    """
    combined = f"{source_legislation} {text} {source_url}"
    combined_lower = combined.lower()

    result: dict = {
        "status": "unknown",
        "in_force_date": None,
        "last_amended_date": None,
        "repealed_date": None,
        "confidence": 0.0,
        "status_evidence": [],
    }

    # Step 1: Detect status keywords
    status_matches: list[tuple[TimeframeStatus, int]] = []
    for status, keywords in _STATUS_PATTERNS.items():
        for kw in keywords:
            if kw in combined_lower:
                status_matches.append((status, 1))
                result["status_evidence"].append(f"Keyword '{kw}' suggests status '{status}'")

    if status_matches:
        # Score by status
        status_scores: dict[str, float] = {}
        for status, weight in status_matches:
            status_scores[status] = status_scores.get(status, 0) + weight

        # Higher score = more likely
        best_status = max(status_scores, key=status_scores.get)
        result["status"] = best_status
        result["confidence"] = min(0.5 + 0.1 * status_scores[best_status], 0.95)

    # Step 2: Extract dates
    be_date = _find_be_date(combined)
    date = _find_date(combined)

    if be_date:
        result["in_force_date"] = be_date
    elif date:
        result["in_force_date"] = date

    # Step 3: Check for amendment date
    amend_patterns = [
        r"amended\s+(?:as of|on|in|by)\s+(\w+\s+\d{4})",
        r"last amended\s+(\w+\s+\d{4})",
        r"修订[于于]?\s*(\d{4})年",
        r"修正[于于]?\s*(\d{4})年",
    ]
    for pat in amend_patterns:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            amend_date_text = m.group(1)
            amend_parsed = _find_date(amend_date_text)
            if not amend_parsed:
                # maybe just a year
                ym = re.search(r"\b(\d{4})\b", amend_date_text)
                if ym:
                    amend_parsed = f"01/{ym.group(1)}"
            if amend_parsed:
                result["last_amended_date"] = amend_parsed
                break

    # Step 4: Check for draft indicators (suppress "in_force" if draft)
    if result["status"] == "draft":
        result["in_force_date"] = None
        result["confidence"] = max(result["confidence"], 0.8)

    return result


def build_timeframe_column(
    status: TimeframeStatus,
    in_force_date: str | None,
    last_amended_date: str | None,
    repealed_date: str | None = None,
) -> str:
    """Build the RDTII-format Timeframe column value."""
    parts = []
    if status == "draft":
        return "Draft / Not yet in force"
    if status == "not_yet_effective":
        return f"Not yet effective (signed {in_force_date or 'date unknown'})"
    if status == "repealed":
        return f"Repealed (was in force until {repealed_date or 'unknown'})"

    if in_force_date:
        parts.append(f"In force since {in_force_date}")
    else:
        parts.append("In force")

    if status == "amended" and last_amended_date:
        parts.append(f"last amended {last_amended_date}")

    if status == "transitional":
        parts.append("transitional provisions apply")

    return "; ".join(parts) if parts else "In force (date unknown)"


__all__ = ["extract_timeframe", "build_timeframe_column", "TimeframeStatus"]
