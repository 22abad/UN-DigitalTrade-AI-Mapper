"""Critic Agent implementation.

Serves as the anti-hallucination validation and deterministic scoring layer.
Performs verbatim quote substring validation, offset translation, source auditing,
and runs the precise deterministic Python scoring engine.
"""

from __future__ import annotations

from typing import Any
from verification import verify_quote, find_quote_offsets
from scoring import score_indicator
from source_validator import grade_source


class CriticAgent:
    """Agent specialized in verifying evidence quality, matching exact quotes, and scoring."""

    def __init__(self):
        # The Critic is deterministic and does not require an LLM provider.
        pass

    def verify(
        self,
        quote: str,
        chunk_text: str,
    ) -> tuple[bool, int, int, str]:
        """Verify that the verbatim_quote is a literal substring within the chunk."""
        quote = quote.strip()
        if not quote:
            return False, -1, -1, "verbatim_quote is empty"

        if not verify_quote(quote, chunk_text):
            return False, -1, -1, "verbatim_quote not found in chunk shown to LLM"

        start, end = find_quote_offsets(quote, chunk_text)
        if start < 0 or end <= start:
            return False, -1, -1, "verbatim_quote matched fuzzily but exact offsets unrecoverable"

        return True, start, end, ""

    def evaluate_score(
        self,
        indicator_id: str,
        features: dict[str, Any],
    ) -> tuple[float, str]:
        """Run the deterministic Python scoring rule for the given indicator features."""
        try:
            score, justification = score_indicator(indicator_id, features)
            return float(score), justification
        except NotImplementedError:
            # Fallback for indicators whose scoring rule is not yet implemented
            return 0.5, "Scoring rules not implemented."
        except Exception as e:
            return 0.0, f"Scoring engine error: {e}"

    def audit_source(
        self,
        url: str,
        title: str,
    ) -> tuple[str, bool, list[str]]:
        """Assess the trustworthiness of the official legislation source."""
        grade_info = grade_source(url, title)
        grade = grade_info.get("grade", "C")
        reasons = grade_info.get("reasons", [])
        requires_review = grade in ("C", "D") or not url
        return grade, requires_review, reasons
