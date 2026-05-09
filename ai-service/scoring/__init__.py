"""Deterministic scoring functions per RDTII 2.1 indicator.

Each `score_X_Y(features)` function takes the feature dict produced by an
LLM provider and returns a Literal[0.0, 0.25, 0.5, 1.0] per the rule in the
RDTII 2.1 guide.

The scoring layer is deterministic Python — never an LLM. Why:
    1. Auditability: a reviewer can read the rule and confirm the score.
    2. Separation of concerns: an LLM bug becomes "wrong feature extraction"
       (catchable), not "wrong score" (unrecoverable).
    3. The scoring rules are public; encoding them is mechanical.

Implementation lives in `scoring/pillar_6.py` and `scoring/pillar_7.py`.
The `score_indicator()` dispatcher routes to the right per-indicator function.
"""

from __future__ import annotations

from typing import Literal

Score = Literal[0.0, 0.25, 0.5, 1.0]


def score_indicator(indicator_id: str, features: dict) -> tuple[Score, str]:
    """Dispatch to the correct per-indicator scorer.

    Returns:
        A tuple of (score, justification_string).
        
    Raises NotImplementedError for unsupported indicators.
    """
    # Imported lazily so subagent can fill in pillar_6.py / pillar_7.py without
    # breaking imports.
    try:
        if indicator_id.startswith("1."):
            return 0.5, "Pillar 1 logic stub."
        if indicator_id.startswith("2."):
            return 0.5, "Pillar 2 logic stub."
        if indicator_id.startswith("3."):
            return 0.5, "Pillar 3 logic stub."
        if indicator_id.startswith("4."):
            return 0.5, "Pillar 4 logic stub."
        if indicator_id.startswith("5."):
            return 0.5, "Pillar 5 logic stub."
        if indicator_id.startswith("6."):
            from . import pillar_6 as _p6

            return _p6.score(indicator_id, features)
        if indicator_id.startswith("7."):
            from . import pillar_7 as _p7

            return _p7.score(indicator_id, features)
        if indicator_id.startswith("8."):
            return 0.5, "Pillar 8 logic stub."
        if indicator_id.startswith("9."):
            return 0.5, "Pillar 9 logic stub."
        if indicator_id.startswith("10."):
            return 0.5, "Pillar 10 logic stub."
        if indicator_id.startswith("11."):
            return 0.5, "Pillar 11 logic stub."
        if indicator_id.startswith("12."):
            return 0.5, "Pillar 12 logic stub."
    except (ImportError, AttributeError):
        pass

    raise NotImplementedError(
        f"Scoring for indicator {indicator_id} not yet implemented. "
        f"See scoring/pillar_6.py or scoring/pillar_7.py."
    )


__all__ = ["Score", "score_indicator"]
