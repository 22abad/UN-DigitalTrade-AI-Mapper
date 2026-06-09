"""Deterministic scoring for Pillar 7: Domestic data protection & privacy.

Indicators 7.1 through 7.5, encoded from the RDTII 2.1 guide (Chapter 3,
pp. 57-63). Each function takes a feature dict (produced by the LLM provider
per `features.py`) and returns a tuple (Score, Justification).
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


def _excluded_if_gov_only(features: dict) -> bool:
    return bool(features.get("applies_to_government_data_only"))


# ── 7.1 Lack of comprehensive legal framework for data protection ──────────
def score_7_1(features: dict) -> tuple[Score, str]:
    if bool(features.get("has_comprehensive_framework")):
        return 0.0, "Score 0: A comprehensive data protection legal framework exists."
    if bool(features.get("has_sectoral_framework_only")):
        return 0.5, "Score 0.5: Only a sectoral data protection framework exists."
    return 1.0, "Score 1: Lack of a comprehensive data protection legal framework."


# ── 7.2 Lack of dedicated legal framework for cybersecurity ────────────────
def score_7_2(features: dict) -> tuple[Score, str]:
    if bool(features.get("has_dedicated_cybersecurity_law")):
        return 0.0, "Score 0: A dedicated cybersecurity legal framework applies across all sectors."
    if bool(features.get("has_sectoral_cybersecurity_only")):
        return 0.5, "Score 0.5: A non-dedicated or sector-specific cybersecurity legal framework exists."
    return 1.0, "Score 1: Lack of a dedicated cybersecurity legal framework."


# ── 7.3 Minimum period of data retention requirements ──────────────────────
def score_7_3(features: dict) -> tuple[Score, str]:
    """Distinguish I7.3 (minimum retention) from data minimisation rules.

    RDTII 2.1: Score 1 only when a law mandates that electronic transaction /
    commercial records MUST be retained for a SPECIFIED MINIMUM PERIOD
    (e.g. 'not less than 5 years', 'at least 3 years').

    Do NOT score 1 for mere data minimisation provisions like
    "do not retain longer than necessary" — those are scoring-irrelevant for I7.3.
    
    Heuristic rules:
      - "minimum period", "not less than X [years/months/days]",
        "at least X", "shall be kept for at least" → has_minimum_retention_period=True
      - "as long as necessary", "do not retain longer", "不得过长保留",
        "数据最小化", "data minimisation" → retention_type="minimisation" (NOT I7.3)
      - explicit "must retain" with time → retention_type="minimum"
    """
    if _excluded_if_gov_only(features):
        return 0.0, "Score 0: Excluded because measure applies only to government data."

    # Explicit feature flag from LLM features (preferred signal)
    has_min_period = bool(features.get("has_minimum_retention_period"))
    retention_type = (features.get("retention_type") or "").strip().lower()

    # If LLM flagged explicit minimum → score 1
    if has_min_period:
        min_val = features.get("min_retention_value")
        unit = features.get("min_retention_unit", "")
        unit_label = f" ({min_val} {unit})" if (min_val and unit) else ""
        return 1.0, f"Score 1: A minimum period of data retention is mandated{unit_label}."

    # If LLM says retention_type is "minimisation" → it's NOT a minimum retention rule
    if retention_type == "minimisation":
        return 0.0, ("Score 0: Provision is a data minimisation / 'do not retain longer than necessary' "
                      "rule, not a minimum retention mandate.")

    # Heuristic fallback: check text snippets for distinguishing signals
    text_snippets = features.get("text_snippets", "") or ""
    has_min_signals = any(kw in text_snippets.lower() for kw in [
        "not less than", "at least", "shall keep", "must retain",
        "不得低于", "不少于", "至少保存", "保留期限不少于",
    ])
    has_min_unit = bool(features.get("min_retention_value")) and bool(features.get("min_retention_unit"))

    if has_min_signals or has_min_unit:
        ret_desc = f"{features['min_retention_value']} {features['min_retention_unit']}" if has_min_unit else "specified minimum period"
        return 1.0, f"Score 1: Text contains signals of a minimum retention mandate ({ret_desc})."

    # Check for data minimisation signals in text
    has_minimisation_signals = any(kw in text_snippets.lower() for kw in [
        "as long as necessary", "necessary for a period",
        "不得保存过长期限", "保留期限不得超过", "数据最小化原则",
        "do not retain longer than", "may be retained only",
    ])
    if has_minimisation_signals:
        return 0.0, ("Score 0: Only data minimisation / time-limiting provision found "
                      "('retain no longer than...'), not a mandatory minimum retention period.")

    return 0.0, "Score 0: No minimum retention requirement identified; any retention rule is either absent or does not specify a mandated minimum."


# ── 7.4 DPIA / DPO requirements ────────────────────────────────────────────
def score_7_4(features: dict) -> tuple[Score, str]:
    has_dpo = bool(features.get("has_dpo_requirement"))
    has_dpia = bool(features.get("has_dpia_requirement"))
    horizontal = bool(features.get("horizontal_scope"))

    if has_dpo:
        if horizontal:
            return 1.0, "Score 1: Requirement for the appointment of a DPO applies horizontally across all sectors."
        return 0.5, "Score 0.5: Requirements for having a DPO are applied only to a specific sector."
        
    if has_dpia:
        return 0.25, "Score 0.25: Only a Data Protection Impact Assessment (DPIA) is required, without a DPO."
        
    return 0.0, "Score 0: No requirement for DPO or DPIA."


# ── 7.5 Government access to personal data ─────────────────────────────────
def score_7_5(features: dict) -> tuple[Score, str]:
    if bool(features.get("has_government_access_without_judicial_oversight")):
        return 1.0, "Score 1: Government can access personal data without explicit authorization from an independent judicial body."
    return 0.0, "Score 0: No requirement allowing government access without judicial oversight."


# ── Dispatcher ─────────────────────────────────────────────────────────────
_SCORERS = {
    "7.1": score_7_1,
    "7.2": score_7_2,
    "7.3": score_7_3,
    "7.4": score_7_4,
    "7.5": score_7_5,
}


def score(indicator_id: str, features: dict) -> tuple[Score, str]:
    fn = _SCORERS.get(indicator_id)
    if fn is None:
        raise NotImplementedError(f"Pillar 7 indicator {indicator_id} not implemented")
    return fn(features)


__all__ = [
    "score",
    "score_7_1",
    "score_7_2",
    "score_7_3",
    "score_7_4",
    "score_7_5",
]
