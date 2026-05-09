"""LLMProvider abstract base.

This abstraction is the cornerstone of the "swappable to open-weight" requirement.
Every provider exposes the same interface; main.py never imports a concrete provider.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionUsage:
    """Token / cost telemetry for one extract_features call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    raw_response: str = field(default="", repr=False)


class ExtractionError(Exception):
    """Raised when the provider fails or returns unparseable output."""


class LLMProvider(ABC):
    """Abstract LLM provider for RDTII feature extraction.

    Contract:
        - The provider receives an article (chunk) and a feature spec
          (which features the deterministic scorer needs).
        - It returns a flat dict whose keys match feature_spec, plus a
          mandatory `verbatim_quote` string and 0+ optional metadata keys
          (`source_legislation`, `last_update`, `scope`, `impact`).
        - The provider MUST NOT compute or return a score. Scoring is
          owned by the deterministic Python layer.
        - The provider MUST NOT paraphrase the verbatim_quote. The
          downstream verifier rejects mappings whose quote is not a
          substring of the source.
    """

    name: str = "base"
    last_usage: ExtractionUsage | None = None

    @abstractmethod
    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        """Extract features for a given (article, indicator) pair.

        Args:
            article_text: The legal text chunk (one article / clause).
            indicator_id: e.g. "6.1", "7.3".
            feature_spec: Mapping from feature_name -> {"type": "bool|int|str", "description": "..."}.

        Returns:
            dict with keys:
                - all keys from feature_spec
                - "verbatim_quote": str (mandatory)
                - optional: "source_legislation", "last_update", "scope", "impact"

        Raises:
            ExtractionError on failure (parsing, network, etc.).
        """
        ...

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        """Subclasses should override with provider-specific pricing."""
        return 0.0

    # ── Shared helpers (used by concrete providers) ──────────────────

    @staticmethod
    def build_prompt(
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> str:
        """Construct a uniform extraction prompt across all providers.

        Keeping this in the base class means provider comparisons (Gemini vs
        Llama 3 etc.) are testing the model, not the prompt.
        """
        feature_lines = []
        for fname, fmeta in feature_spec.items():
            ftype = fmeta.get("type", "bool")
            fdesc = fmeta.get("description", "")
            feature_lines.append(f'  - "{fname}" ({ftype}): {fdesc}')
        feature_block = "\n".join(feature_lines) if feature_lines else "  (none)"

        schema_keys = list(feature_spec.keys()) + [
            "verbatim_quote",
            "source_legislation",
            "last_update",
            "scope",
        ]
        schema_lines = ",\n".join(f'  "{k}": ...' for k in schema_keys)

        return f"""You are a UN ESCAP digital trade policy analyst extracting structured
data from legal text for the RDTII 2.1 framework.

You are evaluating ONE specific indicator: {indicator_id}.
You MUST extract the following features by reading the article below:

{feature_block}

ABSOLUTE RULES:
- Output ONLY valid JSON. No prose, no markdown fences, no explanations.
- "verbatim_quote" MUST be an EXACT substring of the input text — do NOT paraphrase, summarize, translate, or rephrase.
- If a feature cannot be determined from the text, set it to its type's default (false / 0 / "").
- "scope" MUST be one of: "horizontal" / "sectoral" / "unknown".
- Do NOT include a score or any RDTII pillar/indicator number — only features.

JSON schema (all keys required):
{{
{schema_lines}
}}

Input article:
\"\"\"
{article_text}
\"\"\"
"""

    @staticmethod
    def build_batch_prompt(
        article_text: str,
        indicators: list[tuple[str, dict[str, dict[str, str]]]],
    ) -> str:
        """Construct a batch prompt extracting ALL indicators in one LLM call."""
        parts: list[str] = []
        schema_parts: list[str] = []
        for indicator_id, feature_spec in indicators:
            parts.append(f"\nIndicator {indicator_id}:")
            for fname, fmeta in feature_spec.items():
                parts.append(f'  - "{fname}" ({fmeta.get("type", "bool")}): {fmeta.get("description", "")}')

            schema_parts.append(f'  "{indicator_id}": {{')
            schema_parts.append(f'    "verbatim_quote": "exact substring",')
            for fname in feature_spec.keys():
                schema_parts.append(f'    "{fname}": ...,')
            schema_parts.append(f'    "source_legislation": "...",')
            schema_parts.append(f'    "last_update": "...",')
            schema_parts.append(f'    "scope": "horizontal|sectoral|unknown"')
            schema_parts.append('  },')

        return f"""You are a UN ESCAP digital trade policy analyst extracting structured
data from legal text for the RDTII 2.1 framework.

Evaluate ALL of these indicators from the same article below:

{chr(10).join(parts)}

ABSOLUTE RULES:
- Output ONLY valid JSON. No prose, no markdown fences, no explanations.
- Each indicator MUST have a "verbatim_quote" that is an EXACT substring of the input — do NOT paraphrase.
- If a feature cannot be determined, set to its type default (false / 0 / "").
- "scope" MUST be one of: "horizontal" / "sectoral" / "unknown".
- Do NOT include scores — only features.

Return JSON:
{{
{chr(10).join(schema_parts)}
}}

Input article:
\"\"\"
{article_text}
\"\"\"
"""

    @staticmethod
    def parse_json_response(raw_text: str) -> dict[str, Any]:
        """Robustly extract a JSON object from an LLM response.

        Handles:
            - Bare JSON
            - JSON wrapped in ```json fences
            - JSON with leading prose ("Here is the result: {...}")
        """
        if not raw_text:
            raise ExtractionError("Empty response from LLM")

        # Strip code fences
        stripped = raw_text.strip()
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```\s*$", "", stripped)

        # Locate first { and last } (most permissive)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ExtractionError(f"No JSON object found in: {raw_text[:200]}")

        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as e:
            raise ExtractionError(f"Invalid JSON: {e}; raw: {raw_text[:200]}")
