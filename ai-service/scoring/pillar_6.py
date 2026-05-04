"""Deterministic scoring for Pillar 6: Cross-border data policies.

Indicators 6.1 through 6.5, encoded from the RDTII 2.1 guide (Chapter 3,
pp. 48-55). Each function takes a feature dict (produced by the LLM provider
per `features.py`) and returns a tuple (Score, Justification).
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


def _excluded_if_gov_only(features: dict) -> bool:
    """Indicators 6.1-6.3 / 7.3 exclude government-only measures (score 0)."""
    return bool(features.get("applies_to_government_data_only"))


def _safe_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return default
    return default


# ── 6.1 Ban & local processing requirements ────────────────────────────────
def score_6_1(features: dict) -> tuple[Score, str]:
    if _excluded_if_gov_only(features):
        return 0.0, "Score 0: Excluded because measure applies only to government data."

    has_ban = bool(features.get("has_ban"))
    has_local = bool(features.get("has_local_processing"))
    if not (has_ban or has_local):
        return 0.0, "Score 0: No ban or local processing requirement identified."

    req_type = "Ban and local processing" if has_ban and has_local else ("Ban" if has_ban else "Local processing")
    
    personal = bool(features.get("personal_data"))
    horizontal = bool(features.get("horizontal_scope"))
    num_economies = _safe_int(features.get("num_economies_affected"))
    
    reasons = []
    if personal: reasons.append("covers personal data")
    if horizontal: reasons.append("applies horizontally across sectors")
    if num_economies >= 2: reasons.append(f"applies to {num_economies} economies")
    
    if reasons:
        return 1.0, f"Score 1: {req_type} requirement {' OR '.join(reasons)}."

    return 0.5, f"Score 0.5: {req_type} requirement applies to non-personal data, a specific sector, or a single economy."


# ── 6.2 Local storage requirements ─────────────────────────────────────────
def score_6_2(features: dict) -> tuple[Score, str]:
    if _excluded_if_gov_only(features):
        return 0.0, "Score 0: Excluded because measure applies only to government data."

    if not bool(features.get("has_local_storage")):
        return 0.0, "Score 0: Data permitted to be freely transferred without local storage requirements."

    personal = bool(features.get("personal_data"))
    horizontal = bool(features.get("horizontal_scope"))
    
    if personal or horizontal:
        reason = "covers personal data" if personal else "applies horizontally across sectors"
        return 1.0, f"Score 1: Local storage requirement {reason}."
        
    return 0.5, "Score 0.5: Local storage requirement applies to non-personal data or a specific sector."


# ── 6.3 Infrastructure requirements ────────────────────────────────────────
def score_6_3(features: dict) -> tuple[Score, str]:
    if _excluded_if_gov_only(features):
        return 0.0, "Score 0: Excluded because measure applies only to government data."
        
    if bool(features.get("has_infrastructure_req")):
        return 1.0, "Score 1: Infrastructure requirement (e.g., local data centre) is mandated."
        
    return 0.0, "Score 0: No local infrastructure requirement."


# ── 6.4 Conditional flow regimes ───────────────────────────────────────────
def score_6_4(features: dict) -> tuple[Score, str]:
    if not bool(features.get("has_conditional_flow")):
        return 0.0, "Score 0: No conditional requirements attached to cross-border data transfer."

    personal = bool(features.get("personal_data"))
    horizontal = bool(features.get("horizontal_scope"))
    
    if personal or horizontal:
        reason = "covers personal data" if personal else "applies horizontally across sectors"
        return 1.0, f"Score 1: Conditional flow regime {reason}."
        
    return 0.5, "Score 0.5: Conditional flow regime applies to non-personal data or a specific sector."


# ── 6.5 Not in agreement with binding commitments on data transfer ─────────
def score_6_5(features: dict) -> tuple[Score, str]:
    if bool(features.get("has_binding_agreement")):
        return 0.0, "Score 0: Economy has signed binding commitments/agreements on data transfer."
    return 1.0, "Score 1: Economy is NOT in agreement with binding commitments on data transfer."


# ── Dispatcher ─────────────────────────────────────────────────────────────
_SCORERS = {
    "6.1": score_6_1,
    "6.2": score_6_2,
    "6.3": score_6_3,
    "6.4": score_6_4,
    "6.5": score_6_5,
}


def score(indicator_id: str, features: dict) -> tuple[Score, str]:
    fn = _SCORERS.get(indicator_id)
    if fn is None:
        raise NotImplementedError(f"Pillar 6 indicator {indicator_id} not implemented")
    return fn(features)


__all__ = [
    "score",
    "score_6_1",
    "score_6_2",
    "score_6_3",
    "score_6_4",
    "score_6_5",
]
