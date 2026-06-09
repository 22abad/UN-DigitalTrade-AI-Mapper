"""Ollama — local model server with OpenAI-compatible API.

Usage:
    export OLLAMA_BASE_URL=http://host.docker.internal:11434/v1  # or wherever ollama runs
    export RDTII_LLM_PROVIDER=ollama
    export OLLAMA_MODEL=qwen2.5:7b                               # model name from `ollama list`
"""

from __future__ import annotations

import os
import time

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """OpenAI-compatible client targeted at a local Ollama instance."""

    default_model = "qwen2.5-coder:7b"     # fallback if nothing is set
    api_key_env = "OLLAMA_API_KEY"         # Ollama doesn't require one by default

    def __init__(self, model: str | None = None, base_url: str | None = None):
        env_var = self.api_key_env
        self.raw_api_key = os.getenv(env_var) or ""  # allow blank key for local Ollama
        if not self.raw_api_key:
            self.raw_api_key = "ollama-local"        # dummy value so downstream code doesn't error

        self.model_name = model or os.getenv(f"{env_var.replace('_API_KEY', '').rstrip('_')}_MODEL") or self.default_model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL") or "http://host.docker.internal:11434/v1"
        self.name = self.model_name

    def query(self, prompt: str, system: str = "") -> str:
        from openai import OpenAI
        from .base import ExtractionError

        client = OpenAI(api_key=self.raw_api_key, base_url=self.base_url)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise ExtractionError(f"Ollama query failed: {e}") from e

    def extract_features(self, article_text: str, indicator_id: str, feature_spec: dict) -> dict:
        from openai import OpenAI
        from .base import ExtractionError, ExtractionUsage

        client = OpenAI(api_key=self.raw_api_key, base_url=self.base_url)
        prompt = self.build_prompt(article_text, indicator_id, feature_spec)
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        
        try:
            resp = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=2048,
            )
        except Exception as e:
            raise ExtractionError(f"Ollama request failed (base_url={self.base_url}): {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        raw_response = resp.choices[0].message.content
        usage.raw_response = raw_response or ""
        usage.input_tokens = resp.usage.prompt_tokens if resp.usage else 0
        usage.output_tokens = resp.usage.completion_tokens if resp.usage else 0
        usage.cost_usd = 0.0  # local inference

        return self.parse_json_response(raw_response)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0
