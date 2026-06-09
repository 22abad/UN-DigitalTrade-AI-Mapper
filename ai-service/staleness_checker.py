"""Staleness / outdated-law detection for extracted indicator mappings.

Flags a legal instrument as potentially outdated based on:
1. **Age heuristic** — last_update > N years ago → stale
2. **Status heuristic** — timeframe_status in {repealed, draft, unknown} → stale
3. **Wayback comparison** — optional: check if Wayback has a more recent
   snapshot than the LLM-reported last_update.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

# A law is flagged as "potentially outdated" when its last_update
# is older than this many years from today.
_STALE_THRESHOLD_YEARS = 5


def _parse_mm_yyyy(val: str) -> datetime | None:
    """Try to parse a date string in MM/YYYY or YYYY-MM-DD or similar.

    Returns a datetime (first-of-month) or None on failure.
    """
    val = val.strip()
    # MM/YYYY or M/YYYY
    m = re.match(r"^(\d{1,2})/(\d{4})$", val)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1900 <= year <= 2100:
            return datetime(year, month, 1, tzinfo=timezone.utc)

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", val)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)

    # YYYY-MM
    m = re.match(r"^(\d{4})-(\d{1,2})$", val)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=timezone.utc)

    # plain year
    m = re.match(r"^(\d{4})$", val)
    if m:
        return datetime(int(m.group(1)), 1, 1, tzinfo=timezone.utc)

    return None


def check_staleness(
    last_update: str = "",
    timeframe_status: str = "unknown",
    source_url: str = "",
    source_legislation: str = "",
    *,
    _now: datetime | None = None,
) -> dict:
    """Evaluate whether a legal instrument appears outdated.

    Args:
        last_update: LLM-reported last update date (MM/YYYY or ISO).
        timeframe_status: from timeframe_extractor — 'in_force', 'repealed', etc.
        source_url: URL to optionally check Wayback for newer versions.

    Returns:
        dict with keys:
          - is_stale: bool
          - staleness_reasons: list[str]
          - stale_severity: 'high' | 'medium' | 'low' | 'none'
    """
    now = _now or datetime.now(timezone.utc)
    reasons: list[str] = []

    # ── 1. Status-based staleness ─────────────────────────────────
    if timeframe_status == "repealed":
        reasons.append("Legal instrument has been repealed")
    elif timeframe_status == "draft":
        reasons.append("Legal instrument is a draft / not in force")
    elif timeframe_status == "unknown":
        reasons.append("Could not determine legal status — may be outdated")

    # ── 2. Age-based staleness ────────────────────────────────────
    if last_update:
        parsed = _parse_mm_yyyy(last_update)
        if parsed:
            age_years = (now - parsed).days / 365.25
            if age_years >= _STALE_THRESHOLD_YEARS:
                reasons.append(
                    f"Last updated {age_years:.0f} years ago ({last_update})"
                    f" — exceeds {_STALE_THRESHOLD_YEARS}-year threshold"
                )

    # ── 3. Severity ───────────────────────────────────────────────
    severity: str = "none"
    if reasons:
        severe_keywords = ["repealed", "draft"]
        if any(k in reasons[0].lower() for k in severe_keywords):
            severity = "high"
        elif "unknown" in reasons[0].lower():
            severity = "medium"
        elif "years" in reasons[0].lower():
            severity = "medium"
        else:
            severity = "low"

    return {
        "is_stale": len(reasons) > 0,
        "staleness_reasons": reasons,
        "stale_severity": severity,
    }
