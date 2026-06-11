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
    def query(self, prompt: str, system: str = "") -> str:
        """Free-form text completion — used by the RAG query endpoint.

        Args:
            prompt: The user's full prompt (question + context).
            system: Optional system instruction override.

        Returns:
            Raw text response from the LLM.

        Raises:
            ExtractionError on failure.
        """
        ...

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

    def extract_batch(
        self,
        chunk_text: str,
        indicators: list[tuple[str, dict[str, dict[str, str]]]],
    ) -> dict[str, dict[str, Any]]:
        """Default batch extraction — loops over extract_features.

        Concrete providers that support true batching (single LLM call per
        chunk) should override this for performance. The default keeps the
        old per-indicator calling convention working for all providers.
        """
        result: dict[str, dict[str, Any]] = {}
        for indicator_id, feature_spec in indicators:
            result[indicator_id] = self.extract_features(
                chunk_text, indicator_id, feature_spec,
            )
        return result

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
            "article_clause",
            "source_legislation",
            "last_update",
            "scope",
            "coverage",
            "cluster",
            "name",
            "policy_description",
        ]
        schema_lines = ",\n".join(f'  "{k}": ...' for k in schema_keys)

        return f"""You are a UN ESCAP digital trade policy analyst extracting structured
data from legal text for the RDTII 2.1 framework.

You are evaluating ONE specific indicator: {indicator_id}.
You MUST extract the following features by reading the article below:

{feature_block}

ABSOLUTE RULES:
- Output ONLY valid JSON. No prose, no markdown fences, no explanations.
- If the text does NOT contain any policy or measure matching this indicator, you MUST return an empty "verbatim_quote" (i.e. "") and set all boolean features to false or default. DO NOT try to extract unrelated text, titles, or headers as a quote.
- "verbatim_quote" MUST be an EXACT substring of the input text.
  - FOR NON-ENGLISH TEXTS: Copy the text character-for-character including all spaces and special characters. DO NOT attempt to normalize or reformat.
- "article_clause" MUST be the specific article, clause, or section number (e.g. "Article 18", "Section 5(2)", "Paragraph 10"). Output an empty string if not explicitly mentioned in the text.
- "source_legislation" MUST be the official title of the law/regulation, EXCLUDING any article, section, or clause numbers. Format it exactly as: [Country/Economy Name] [Law Name] ([Optional Abbreviation]), [Year], [Law Number] (e.g., "Singapore Personal Data Protection Act (PDPA), 2012, No. 26", "Malaysia Personal Data Protection Act (PDPA), 2010, No. 709").
- If a feature cannot be determined from the text, set it to its type's default (false / 0 / "").
- "scope" MUST be one of: "horizontal" / "sectoral" / "unknown".
- "coverage": detailed description of the measure's coverage (e.g. 'ICT products', 'Telecommunication equipments', 'Cross-cutting').
- "cluster": high-level policy cluster — one of "Traditional trade policies", "Digital governance policies", or "Other domestic policies".
- "name": mid-level policy category (e.g. "Tariffs & trade defence", "Non-technical NTMs", "Standards & procedures", "Online sales & transactions", "Public procurement", "Foreign direct investment", "Intellectual property rights").
- "policy_description": most specific policy type (e.g. "Trade defence measures", "Import bans", "Local content requirements", "Self-certification limitations").
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

            fnames = list(feature_spec.keys())
            fields = [f'    "verbatim_quote": "exact substring",']
            fields.append('    "article_clause": "specific article, clause, or section number (e.g. Article 18), or empty string",')
            for fname in fnames:
                fields.append(f'    "{fname}": ...,')
            fields.append('    "source_legislation": "official title of the law/regulation EXCLUDING article/clause numbers, formatted exactly as: [Country/Economy] [Law Name] ([Abbreviation]), [Year], [Law Number] (e.g. Singapore Personal Data Protection Act (PDPA), 2012, No. 26)",')
            fields.append('    "scope": "horizontal|sectoral|unknown",')
            fields.append('    "coverage": "detailed coverage description (e.g. ICT products)",')
            fields.append('    "cluster": "Traditional trade policies|Digital governance policies|Other domestic policies",')
            fields.append('    "name": "mid-level policy category (e.g. Tariffs & trade defence)",')
            fields.append('    "policy_description": "specific policy type (e.g. Trade defence measures)"')
            schema_parts.append(f'  "{indicator_id}": {{')
            schema_parts.extend(fields)
            schema_parts.append('  }')

        return f"""You are a UN ESCAP digital trade policy analyst extracting structured
data from legal text for the RDTII 2.1 framework.

Evaluate ALL of these indicators from the same article below:

{chr(10).join(parts)}

ABSOLUTE RULES:
- Output ONLY valid JSON. No prose, no markdown fences, no explanations.
- If the text does NOT contain any policy or measure matching an indicator, you MUST return an empty "verbatim_quote" (i.e. "") and set all features to their defaults for that indicator. DO NOT extract unrelated text, titles, or headings.
- Each indicator MUST have a "verbatim_quote" that is an EXACT substring of the input — do NOT paraphrase.
- "article_clause" MUST be the specific article, clause, or section number (e.g. "Article 18", "Section 5(2)", "Paragraph 10"). Output an empty string if not explicitly mentioned in the text.
- "source_legislation" MUST be the official title of the law/regulation, EXCLUDING any article, section, or clause numbers. Format it exactly as: [Country/Economy Name] [Law Name] ([Optional Abbreviation]), [Year], [Law Number] (e.g., "Singapore Personal Data Protection Act (PDPA), 2012, No. 26", "Malaysia Personal Data Protection Act (PDPA), 2010, No. 709").
- If a feature cannot be determined, set to its type default (false / 0 / "").
- "scope" MUST be one of: "horizontal" / "sectoral" / "unknown".
- "coverage": detailed coverage description.
- "cluster": high-level policy cluster — "Traditional trade policies", "Digital governance policies", or "Other domestic policies".
- "name": mid-level policy category.
- "policy_description": specific policy type.
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
            - Bare JSON / code fences / leading prose
            - Truncated JSON (max_tokens) — closes braces
            - Missing commas between key-value pairs
            - Trailing commas
        """
        if not raw_text:
            raise ExtractionError("Empty response from LLM")

        stripped = raw_text.strip()
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```\s*$", "", stripped)

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1:
            raise ExtractionError(f"No JSON object found in: {raw_text[:200]}")

        def _last_comma_outside_string(value: str) -> int:
            """Return the last comma not enclosed in a JSON string."""
            in_string = False
            escaped = False
            last = -1
            for i, ch in enumerate(value):
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if ch == "," and not in_string:
                    last = i
            return last

        if end >= start:
            json_candidate = stripped[start : end + 1]
        else:
            json_candidate = stripped[start:]

        # Attempt 1: parse as-is
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

        # Attempt 2: common LLM JSON repairs
        repairs = [
            # Remove trailing commas before } or ]
            (r",\s*(\}|\])", r"\1"),
            # Insert missing commas: value followed by new key
            (r'(true|false|null|\d+|"[^"]*"|\}|\])\s+"', r'\1, "'),
            # Fix bare-word values that should be quoted (LLM shorthand)
            (r':\s+(true|false|null|"[^"]*")(\s*[,\}])', r': \1\2'),
        ]
        for pattern, replacement in repairs:
            repaired = re.sub(pattern, replacement, json_candidate)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                continue

        # Attempt 3: truncation repair — strip incomplete tail, close braces
        try:
            body = json_candidate
            last_comma = _last_comma_outside_string(body)
            if last_comma > 0:
                prefix = body[:last_comma]
            else:
                prefix = body
            depth = prefix.count("{") - prefix.count("}")
            if depth > 0:
                prefix += "}" * depth
            s = prefix.find("{")
            e = prefix.rfind("}")
            if s != -1 and e > s:
                return json.loads(prefix[s : e + 1])
        except json.JSONDecodeError:
            pass

        # Attempt 4: last resort — extract each indicator object individually
        try:
            result: dict[str, Any] = {}
            # Match top-level keys like "6.1" with their object values
            blocks = re.findall(
                r'"(\d+\.\d+)"\s*:\s*'
                r'(\{(?:[^{}]|\{[^{}]*\})*\})',
                json_candidate,
            )
            for key, block in blocks:
                try:
                    result[key] = json.loads(block)
                except json.JSONDecodeError:
                    continue
            if result:
                return result
        except Exception:
            pass

        raise ExtractionError(f"Unrepairable JSON: {raw_text[:300]}")
