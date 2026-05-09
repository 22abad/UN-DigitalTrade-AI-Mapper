"""OpenAI-compatible provider — covers OpenAI, DeepSeek, Together, Groq, Mistral, OpenRouter, etc.

Many vendors expose an OpenAI-compatible chat-completions API; the official
`openai` Python SDK can talk to all of them by overriding `base_url`. Instead
of writing one provider class per vendor, we have one OpenAICompatibleProvider
that subclasses configure per-vendor defaults (model name, base URL, pricing).

Add a new vendor in three lines:

    class GroqProvider(OpenAICompatibleProvider):
        default_model = "llama-3.3-70b-versatile"
        default_base_url = "https://api.groq.com/openai/v1"
        api_key_env = "GROQ_API_KEY"

Or instantiate ad-hoc:
    OpenAICompatibleProvider(model="...", base_url="...", api_key_env="...")
"""

from __future__ import annotations

import os
import time
from typing import Any, ClassVar

from .base import ExtractionError, ExtractionUsage, LLMProvider


def _price_from_env(env_key: str, default: float) -> float:
    raw = os.getenv(env_key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class OpenAICompatibleProvider(LLMProvider):
    """Generic OpenAI-compatible chat provider.

    Subclass to lock in vendor-specific defaults, or pass kwargs to instantiate
    ad-hoc.
    """

    name: str = "openai-compatible"

    # Subclass overrides
    default_model: ClassVar[str] = ""
    default_base_url: ClassVar[str | None] = None
    api_key_env: ClassVar[str] = "OPENAI_API_KEY"
    input_price_env: ClassVar[str] = ""  # USD per 1M input tokens
    output_price_env: ClassVar[str] = ""  # USD per 1M output tokens
    fallback_input_price: ClassVar[float] = 0.0
    fallback_output_price: ClassVar[float] = 0.0

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
    ):
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError as e:
            raise ExtractionError(
                "openai package not installed. `pip install openai`"
            ) from e

        env_var = api_key_env or self.api_key_env
        api_key = api_key or os.getenv(env_var)
        if not api_key:
            raise ExtractionError(
                f"{env_var} is not set. Export it or pass api_key=..."
            )

        self.model_name = model or os.getenv(f"{env_var.replace('_API_KEY', '')}_MODEL") or self.default_model
        if not self.model_name:
            raise ExtractionError(
                f"No model configured. Pass model=... or set {env_var.replace('_API_KEY', '')}_MODEL"
            )

        self.base_url = base_url or self.default_base_url
        # vendor display name = either subclass.name or derived from base url
        self.name = self.model_name

        from openai import OpenAI

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = OpenAI(**client_kwargs)

        self._input_price = _price_from_env(self.input_price_env, self.fallback_input_price)
        self._output_price = _price_from_env(self.output_price_env, self.fallback_output_price)

    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        prompt = self.build_prompt(article_text, indicator_id, feature_spec)
        return self._call_llm(prompt)

    def extract_batch(
        self,
        article_text: str,
        indicators: list[tuple[str, dict[str, dict[str, str]]]],
    ) -> dict[str, dict[str, Any]]:
        """One LLM call extracts ALL indicators from the same chunk.
        
        Args:
            article_text: The legal text chunk.
            indicators: List of (indicator_id, feature_spec) pairs.
        
        Returns:
            dict mapping indicator_id -> extracted features dict.
        """
        from .base import LLMProvider as _Base
        prompt = _Base.build_batch_prompt(article_text, indicators)
        raw = self._call_llm(prompt, max_tokens=16384)
        # raw is {"6.1": {...}, "6.4": {...}, ...}
        result: dict[str, dict[str, Any]] = {}
        for indicator_id, _spec in indicators:
            if indicator_id in raw:
                result[indicator_id] = raw[indicator_id]
        return result

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> dict[str, Any]:
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Output ONLY valid JSON. No prose, no markdown fences.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise ExtractionError(f"{self.model_name} API error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        # Newer SDKs return objects; convert defensively.
        choice = resp.choices[0] if getattr(resp, "choices", None) else None
        usage.raw_response = choice.message.content if choice else ""

        meta = getattr(resp, "usage", None)
        if meta is not None:
            usage.input_tokens = getattr(meta, "prompt_tokens", 0) or 0
            usage.output_tokens = getattr(meta, "completion_tokens", 0) or 0
            usage.cost_usd = self.estimate_cost_usd(usage.input_tokens, usage.output_tokens)

        self.last_usage = usage
        return self.parse_json_response(usage.raw_response)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self._input_price / 1_000_000
            + output_tokens * self._output_price / 1_000_000
        )


# ── Vendor presets ──────────────────────────────────────────────────────


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    default_model = "gpt-4o-mini"
    default_base_url = None  # default OpenAI host
    api_key_env = "OPENAI_API_KEY"
    input_price_env = "OPENAI_INPUT_USD_PER_MTOK"
    output_price_env = "OPENAI_OUTPUT_USD_PER_MTOK"
    fallback_input_price = 0.15
    fallback_output_price = 0.60


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek — cheap reasoning-strong Chinese vendor.

    Endpoint:  https://api.deepseek.com/v1
    Models:    deepseek-chat, deepseek-reasoner
    Set DEEPSEEK_API_KEY (and optionally DEEPSEEK_MODEL).
    """

    name = "deepseek"
    default_model = "deepseek-chat"
    default_base_url = "https://api.deepseek.com/v1"
    api_key_env = "DEEPSEEK_API_KEY"
    input_price_env = "DEEPSEEK_INPUT_USD_PER_MTOK"
    output_price_env = "DEEPSEEK_OUTPUT_USD_PER_MTOK"
    # Public pricing (May 2025): cache miss
    fallback_input_price = 0.27
    fallback_output_price = 1.10


class GroqProvider(OpenAICompatibleProvider):
    """Groq — fast inference of open-weight models (Llama 3.x, Mixtral, etc.).

    Doubles as a low-friction way to run Llama 3 without local GPU setup.
    """

    name = "groq"
    default_model = "llama-3.3-70b-versatile"
    default_base_url = "https://api.groq.com/openai/v1"
    api_key_env = "GROQ_API_KEY"
    input_price_env = "GROQ_INPUT_USD_PER_MTOK"
    output_price_env = "GROQ_OUTPUT_USD_PER_MTOK"
    fallback_input_price = 0.59
    fallback_output_price = 0.79


class TogetherProvider(OpenAICompatibleProvider):
    """Together AI — hosts many open-weight models with OpenAI-compatible API."""

    name = "together"
    default_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    default_base_url = "https://api.together.xyz/v1"
    api_key_env = "TOGETHER_API_KEY"
    input_price_env = "TOGETHER_INPUT_USD_PER_MTOK"
    output_price_env = "TOGETHER_OUTPUT_USD_PER_MTOK"
    fallback_input_price = 0.18
    fallback_output_price = 0.18


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter — meta-router across hundreds of models with one key."""

    name = "openrouter"
    default_model = "meta-llama/llama-3.1-8b-instruct"
    default_base_url = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"
    input_price_env = "OPENROUTER_INPUT_USD_PER_MTOK"
    output_price_env = "OPENROUTER_OUTPUT_USD_PER_MTOK"
    fallback_input_price = 0.0  # varies per model
    fallback_output_price = 0.0


class MistralProvider(OpenAICompatibleProvider):
    """Mistral La Plateforme — OpenAI-compatible API for Mistral models."""

    name = "mistral"
    default_model = "mistral-small-latest"
    default_base_url = "https://api.mistral.ai/v1"
    api_key_env = "MISTRAL_API_KEY"
    input_price_env = "MISTRAL_INPUT_USD_PER_MTOK"
    output_price_env = "MISTRAL_OUTPUT_USD_PER_MTOK"
    fallback_input_price = 0.20
    fallback_output_price = 0.60
