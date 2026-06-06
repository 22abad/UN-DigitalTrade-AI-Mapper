"""Claude provider — Anthropic SDK."""

from __future__ import annotations

import os
import time
from typing import Any

from .base import ExtractionError, ExtractionUsage, LLMProvider


# Approximate prices per 1M tokens for claude-sonnet-4-5 (May 2025).
# Override via env if you use Opus / Haiku.
_INPUT_USD_PER_MTOK = float(os.getenv("CLAUDE_INPUT_USD_PER_MTOK", "3.0"))
_OUTPUT_USD_PER_MTOK = float(os.getenv("CLAUDE_OUTPUT_USD_PER_MTOK", "15.0"))


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        try:
            from anthropic import Anthropic  # noqa: F401  imported lazily
        except ImportError as e:
            raise ExtractionError(
                "anthropic package not installed. `pip install anthropic`"
            ) from e

        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ExtractionError(
                "ANTHROPIC_API_KEY is not set. Set it in env or .env file."
            )

        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.model_name = model_name or os.getenv(
            "CLAUDE_MODEL", "claude-sonnet-4-5-20250929"
        )
        self.name = self.model_name

    def query(self, prompt: str, system: str = "") -> str:
        try:
            resp = self._client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                temperature=0.3,
                system=system or "You are a UN ESCAP digital trade policy analyst specialising in the RDTII 2.1 framework.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise ExtractionError(f"Claude API error: {e}") from e
        return "".join(
            getattr(block, "text", "")
            for block in (getattr(resp, "content", []) or [])
            if getattr(block, "type", None) == "text"
        )

    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        prompt = self.build_prompt(article_text, indicator_id, feature_spec)
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            resp = self._client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                temperature=0,
                system="Output ONLY valid JSON. No prose, no markdown fences.",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            raise ExtractionError(f"Claude API error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        # The SDK returns content as list of TextBlock — concat .text from blocks
        text_chunks = []
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text_chunks.append(getattr(block, "text", ""))
        usage.raw_response = "".join(text_chunks)

        meta = getattr(resp, "usage", None)
        if meta is not None:
            usage.input_tokens = getattr(meta, "input_tokens", 0) or 0
            usage.output_tokens = getattr(meta, "output_tokens", 0) or 0
            usage.cost_usd = self.estimate_cost_usd(
                usage.input_tokens, usage.output_tokens
            )

        self.last_usage = usage

        return self.parse_json_response(usage.raw_response)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * _INPUT_USD_PER_MTOK / 1_000_000
            + output_tokens * _OUTPUT_USD_PER_MTOK / 1_000_000
        )
