"""Deterministic scoring for Pillar 6: Cross-border data policies.

Indicators 6.1 through 6.5, encoded from the RDTII 2.1 guide (Chapter 3,
pp. 48-55). Each function takes a feature dict (produced by the LLM provider
per `features.py`) and returns a Score in {0.0, 0.5, 1.0}.

Rule semantics (verbatim from the guide, paraphrased):
    6.1 Ban / local processing: 1 if covers personal data OR horizontal OR
        affects 2+ economies; 0.5 if non-personal/specific/one economy; 0
        if no requirement. Excluded if government-data-only.
    6.2 Local storage: 1 if personal/horizontal; 0.5 if non-personal/specific;
        0 if none. Excluded if government-data-only.
    6.3 Infrastructure: 1 if any infra requirement; else 0. Excluded if
        government-data-only.
    6.4 Conditional flow: 1 if covers personal OR horizontal; 0.5 if
        non-personal/specific; 0 if no condition.
    6.5 Binding agreement: 1 if NO binding agreement (inverted); 0 if signed.
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


def _excluded_if_gov_only(features: dict) -> bool:
    """Indicators 6.1-6.3 / 7.3 exclude government-only measures (score 0)."""
    return bool(features.get("applies_to_government_data_only"))


# ── 6.1 Ban & local processing requirements ────────────────────────────────
def score_6_1(features: dict) -> Score:
    """Ban on data transfer and/or local processing requirement.

    Per the RDTII 2.1 guide (pp. 50-51), this indicator scores the cost
    of ban / local-processing measures. If neither flag is set, the
    indicator does not fire — a pure privacy law that talks about
    personal data but imposes no cross-border restriction must score 0.

    Decision tree:
        1. Government-data-only measures are excluded -> 0.
        2. If neither has_ban nor has_local_processing is set -> 0.
        3. With a requirement, the upper tier (1.0) fires when it covers
           personal data OR is horizontal across sectors OR applies to
           2+ economies.
        4. Otherwise the requirement is sectoral / single-economy / non-
           personal -> 0.5.
    """
    if _excluded_if_gov_only(features):
        return 0.0

    has_requirement = bool(features.get("has_ban")) or bool(
        features.get("has_local_processing")
    )
    if not has_requirement:
        return 0.0

    personal = bool(features.get("personal_data"))
    horizontal = bool(features.get("horizontal_scope"))
    num_economies = int(features.get("num_economies_affected") or 0)
    if personal or horizontal or num_economies >= 2:
        return 1.0

    return 0.5


# ── 6.2 Local storage requirements ─────────────────────────────────────────
def score_6_2(features: dict) -> Score:
    """Local storage requirement.

    Score 1: requirement covers personal data OR is horizontal.
    Score 0.5: requirement applies to non-personal data or specific set.
    Score 0: no requirement.
    Excluded (0): measure applies to government data only.
    """
    if _excluded_if_gov_only(features):
        return 0.0

    if not bool(features.get("has_local_storage")):
        return 0.0

    if bool(features.get("personal_data")) or bool(features.get("horizontal_scope")):
        return 1.0
    return 0.5


# ── 6.3 Infrastructure requirements ────────────────────────────────────────
def score_6_3(features: dict) -> Score:
    """Infrastructure requirement (mandate to establish a local data centre).

    Score 1: at least one infrastructure requirement.
    Score 0: otherwise.
    Excluded (0): measure applies to government data only.
    """
    if _excluded_if_gov_only(features):
        return 0.0
    return 1.0 if bool(features.get("has_infrastructure_req")) else 0.0


# ── 6.4 Conditional flow regimes ───────────────────────────────────────────
def score_6_4(features: dict) -> Score:
    """Conditional cross-border data transfer regime.

    Score 1: regime covers personal data OR applies horizontally.
    Score 0.5: regime applies to non-personal/specific data.
    Score 0: no condition.
    """
    if not bool(features.get("has_conditional_flow")):
        return 0.0

    if bool(features.get("personal_data")) or bool(features.get("horizontal_scope")):
        return 1.0
    return 0.5


# ── 6.5 Not in agreement with binding commitments on data transfer ─────────
def score_6_5(features: dict) -> Score:
    """Whether the economy is signatory to a binding data-flows agreement.

    NOTE the inversion: high score means *no* agreement (a regulatory gap).
    Score 1: economy has NOT signed any binding agreement on cross-border
        data transfer.
    Score 0: economy has signed at least one such agreement.
    """
    return 0.0 if bool(features.get("has_binding_agreement")) else 1.0


# ── Dispatcher ─────────────────────────────────────────────────────────────
_SCORERS = {
    "6.1": score_6_1,
    "6.2": score_6_2,
    "6.3": score_6_3,
    "6.4": score_6_4,
    "6.5": score_6_5,
}


def score(indicator_id: str, features: dict) -> Score:
    """Dispatch to the per-indicator Pillar 6 scorer."""
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
