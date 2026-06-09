"""Deterministic scoring for Pillar 5: Telecommunications regulations.

Indicators 5.1, 5.2, 5.3 encoded from the RDTII 2.1 guide (Chapter 3).

I5.3 — Government ownership/holding in telecom operators (>50% threshold).
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


# ── 5.1 Telecom competition ────────────────────────────────
def score_5_1(features: dict) -> tuple[Score, str]:
    if bool(features.get("has_competition")):
        return 0.0, "Score 0: Competitive telecom market exists."
    if bool(features.get("has_market_barrier")):
        return 1.0, "Score 1: Barriers to entry in telecom market identified."
    if bool(features.get("no_license_needed")):
        return 0.5, "Score 0.5: No license required for telecom services."
    return 0.0, "Score 0: No competitive barrier or licensing issue identified."


# ── 5.3 Government equity in telecom operators (>50%) ───
def score_5_3(features: dict) -> tuple[Score, str]:
    """Government holds >50% equity in at least one domestic telecom operator."""
    gov_equity_pct = features.get("government_equity_percentage")
    if isinstance(gov_equity_pct, (int, float)):
        if gov_equity_pct > 50:
            return 1.0, f"Score 1: Government holds {gov_equity_pct}% equity in a domestic telecom operator (>50% threshold)."
        elif gov_equity_pct == 50:
            return 0.5, "Score 0.5: Government holds exactly 50% equity (boundary case) in a domestic telecom operator."

    has_gov_owned = bool(features.get("has_government_owned_operator"))
    if has_gov_owned:
        has_majority = bool(features.get("government_has_majority_stake"))
        if has_majority:
            return 1.0, "Score 1: Government holds majority equity (>50%) in at least one domestic telecom operator."
        reason_parts = []
        if features.get("partial_stake_desc"):
            reason_parts.append(f"stake described as: {features['partial_stake_desc']}")
        stake_str = (features.get("stake_percentage_raw") or "undetermined")
        return 0.5, f"Score 0.5: Government equity in telecom operator is partial or unspecified. {' '.join(reason_parts)} Stake reference: {stake_str}."

    has_state_enterprise = bool(features.get("has_state_enterprise_role"))
    if has_state_enterprise:
        return 0.25, "Score 0.25: State-owned enterprise operates in telecom but equity stake is not clearly majority (>50%)."

    return 0.0, "Score 0: No evidence of government holding >50% equity in any domestic telecom operator."


# ── Dispatcher ───────────────────────────────────────────
_SCORERS = {
    "5.1": score_5_1,
    "5.3": score_5_3,
}


def score(indicator_id: str, features: dict) -> tuple[Score, str]:
    fn = _SCORERS.get(indicator_id)
    if fn is None:
        raise NotImplementedError(f"Pillar 5 indicator {indicator_id} not implemented")
    return fn(features)


__all__ = [
    "score",
    "score_5_1",
    "score_5_3",
]
