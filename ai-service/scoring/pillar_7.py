"""Deterministic scoring for Pillar 7: Domestic data protection & privacy.

Indicators 7.1 through 7.5, encoded from the RDTII 2.1 guide (Chapter 3,
pp. 57-63). Each function takes a feature dict (produced by the LLM provider
per `features.py`) and returns a Score in {0.0, 0.25, 0.5, 1.0}.

Rule semantics (verbatim from the guide, paraphrased):
    7.1 Lack of comprehensive data protection framework: 1 if neither
        comprehensive nor sectoral; 0.5 if sectoral only; 0 if comprehensive.
    7.2 Lack of dedicated cybersecurity framework: 1 if neither dedicated
        nor sectoral; 0.5 if sectoral only; 0 if dedicated.
    7.3 Minimum data retention period: 1 if minimum period required; 0
        otherwise. Excluded if government-data-only.
    7.4 DPIA / DPO requirements: 1 if DPO requirement is horizontal (with or
        without DPIA); 0.5 if DPO is sectoral only; 0.25 if only DPIA (no
        DPO) — theoretical edge case from the guide; 0 if neither.
    7.5 Government access without judicial oversight: 1 if such access
        permitted; 0 otherwise.
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


def _excluded_if_gov_only(features: dict) -> bool:
    return bool(features.get("applies_to_government_data_only"))


# ── 7.1 Lack of comprehensive legal framework for data protection ──────────
def score_7_1(features: dict) -> Score:
    """High score = absence of a comprehensive framework (regulatory gap).

    Score 0: comprehensive cross-sectoral data protection law exists.
    Score 0.5: only sectoral framework exists.
    Score 1: neither comprehensive nor sectoral.
    """
    if bool(features.get("has_comprehensive_framework")):
        return 0.0
    if bool(features.get("has_sectoral_framework_only")):
        return 0.5
    return 1.0


# ── 7.2 Lack of dedicated legal framework for cybersecurity ────────────────
def score_7_2(features: dict) -> Score:
    """High score = absence of a dedicated cybersecurity framework.

    Score 0: dedicated horizontal cybersecurity law exists.
    Score 0.5: only sectoral / non-dedicated cybersecurity provisions.
    Score 1: neither.
    """
    if bool(features.get("has_dedicated_cybersecurity_law")):
        return 0.0
    if bool(features.get("has_sectoral_cybersecurity_only")):
        return 0.5
    return 1.0


# ── 7.3 Minimum period of data retention requirements ──────────────────────
def score_7_3(features: dict) -> Score:
    """Minimum period of data retention requirement.

    Score 1: a minimum retention period is mandated.
    Score 0: no requirement, or a non-specific "as long as necessary" rule.
    Excluded (0): measure applies to government data only.
    """
    if _excluded_if_gov_only(features):
        return 0.0
    return 1.0 if bool(features.get("has_minimum_retention_period")) else 0.0


# ── 7.4 DPIA / DPO requirements ────────────────────────────────────────────
def score_7_4(features: dict) -> Score:
    """Requirement to appoint a DPO and/or perform a DPIA.

    The guide focuses on the DPO requirement (DPIA usually follows DPO):
        Score 1: DPO requirement applied horizontally across all sectors
            (with or without DPIA).
        Score 0.5: DPO requirement applies only to a specific sector (with
            or without DPIA).
        Score 0.25: only DPIA is required, no DPO — theoretical edge case
            (a firm could outsource the DPIA task).
        Score 0: no requirement.
    """
    has_dpo = bool(features.get("has_dpo_requirement"))
    has_dpia = bool(features.get("has_dpia_requirement"))
    horizontal = bool(features.get("horizontal_scope"))

    if has_dpo:
        return 1.0 if horizontal else 0.5
    if has_dpia:
        return 0.25
    return 0.0


# ── 7.5 Government access to personal data ─────────────────────────────────
def score_7_5(features: dict) -> Score:
    """Government access to personal data without judicial oversight.

    Score 1: government can access personal data without explicit
        authorization from an independent judicial body.
    Score 0: no such requirement.
    """
    return (
        1.0
        if bool(features.get("has_government_access_without_judicial_oversight"))
        else 0.0
    )


# ── Dispatcher ─────────────────────────────────────────────────────────────
_SCORERS = {
    "7.1": score_7_1,
    "7.2": score_7_2,
    "7.3": score_7_3,
    "7.4": score_7_4,
    "7.5": score_7_5,
}


def score(indicator_id: str, features: dict) -> Score:
    """Dispatch to the per-indicator Pillar 7 scorer."""
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
