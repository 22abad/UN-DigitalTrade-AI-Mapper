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
    if _excluded_if_gov_only(features):
        return 0.0, "Score 0: Excluded because measure applies only to government data."
        
    if bool(features.get("has_minimum_retention_period")):
        return 1.0, "Score 1: A minimum period of data retention is mandated."
        
    return 0.0, "Score 0: No retention requirement, or requirement does not specify a minimum period (e.g., 'as long as necessary')."


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
