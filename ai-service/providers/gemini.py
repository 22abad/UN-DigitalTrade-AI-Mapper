"""Gemini provider — google-genai SDK (replaces deprecated google-generativeai)."""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

from .base import ExtractionError, ExtractionUsage, LLMProvider

logger = logging.getLogger(__name__)

_INPUT_USD_PER_MTOK = float(os.getenv("GEMINI_INPUT_USD_PER_MTOK", "0.075"))
_OUTPUT_USD_PER_MTOK = float(os.getenv("GEMINI_OUTPUT_USD_PER_MTOK", "0.30"))
_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "4"))
_RETRY_BASE_S = float(os.getenv("GEMINI_RETRY_BASE_S", "2.0"))


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc)
    return "503" in msg or "429" in msg or "UNAVAILABLE" in msg or "RESOURCE_EXHAUSTED" in msg


def _call_with_retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs) with exponential backoff on 503/429."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if attempt == _MAX_RETRIES or not _is_retryable(exc):
                raise
            wait = _RETRY_BASE_S * (2 ** attempt) + random.uniform(0, 1)
            logger.warning("[Gemini] retryable error (attempt %d/%d), waiting %.1fs: %s",
                           attempt + 1, _MAX_RETRIES, wait, exc)
            time.sleep(wait)
    raise ExtractionError("unreachable")


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        try:
            from google import genai  # noqa: F401
        except ImportError as e:
            raise ExtractionError(
                "google-genai package not installed. `pip install google-genai`"
            ) from e

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ExtractionError("GEMINI_API_KEY is not set.")

        from google import genai
        from google.genai import types as _types

        self._client = genai.Client(api_key=api_key)
        self._types = _types
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.name = self.model_name

    def query(self, prompt: str, system: str = "") -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            resp = _call_with_retry(
                self._client.models.generate_content,
                model=self.model_name,
                contents=full_prompt,
                config=self._types.GenerateContentConfig(temperature=0.3),
            )
        except Exception as e:
            raise ExtractionError(f"Gemini API error: {e}") from e
        return resp.text or ""

    def extract_batch(
        self,
        chunk_text: str,
        indicators: list[tuple[str, dict[str, dict[str, str]]]],
    ) -> dict[str, dict]:
        prompt = self.build_batch_prompt(chunk_text, indicators)
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            resp = _call_with_retry(
                self._client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            raise ExtractionError(f"Gemini batch API error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        usage.raw_response = resp.text or ""
        self.last_usage = usage
        return self.parse_json_response(usage.raw_response)

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
            resp = _call_with_retry(
                self._client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            raise ExtractionError(f"Gemini API error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        usage.raw_response = resp.text or ""
        meta = getattr(resp, "usage_metadata", None)
        if meta is not None:
            usage.input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            usage.output_tokens = getattr(meta, "candidates_token_count", 0) or 0
            usage.cost_usd = self.estimate_cost_usd(usage.input_tokens, usage.output_tokens)

        self.last_usage = usage
        return self.parse_json_response(usage.raw_response)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * _INPUT_USD_PER_MTOK / 1_000_000
            + output_tokens * _OUTPUT_USD_PER_MTOK / 1_000_000
        )
