"""Gemini provider — Google Generative AI."""

from __future__ import annotations

import os
import time
from typing import Any

import google.generativeai as genai

from .base import ExtractionError, ExtractionUsage, LLMProvider


# Approximate prices per 1M tokens for Gemini 1.5 Flash (May 2025).
# Override via env if you use a different model.
_INPUT_USD_PER_MTOK = float(os.getenv("GEMINI_INPUT_USD_PER_MTOK", "0.075"))
_OUTPUT_USD_PER_MTOK = float(os.getenv("GEMINI_OUTPUT_USD_PER_MTOK", "0.30"))


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ExtractionError(
                "GEMINI_API_KEY is not set. Set it in env or .env file."
            )
        genai.configure(api_key=api_key)
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.name = self.model_name
        self._model = genai.GenerativeModel(self.model_name)

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
            resp = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            raise ExtractionError(f"Gemini API error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        usage.raw_response = getattr(resp, "text", "") or ""
        # Gemini exposes usage via resp.usage_metadata when available
        meta = getattr(resp, "usage_metadata", None)
        if meta is not None:
            usage.input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            usage.output_tokens = getattr(meta, "candidates_token_count", 0) or 0
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
