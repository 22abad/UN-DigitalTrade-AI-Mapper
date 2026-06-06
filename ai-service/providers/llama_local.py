"""Llama 3 local provider via llama-cpp-python.

This proves the "swappable to open-weight" requirement (40 pts at Stage 1+3).

Model file is loaded from LLAMA_MODEL_PATH (a .gguf file). For the prototype
we recommend Meta-Llama-3-8B-Instruct.Q4_K_M.gguf (~4.6 GB), runs on a
laptop with 16 GB RAM.

Setup:
    pip install llama-cpp-python
    export LLAMA_MODEL_PATH=/path/to/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

The provider is lazy: it only loads the model on first extract call so that
unit tests can import this module without a model file present.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .base import ExtractionError, ExtractionUsage, LLMProvider


# Local inference cost is ~0 USD; we report machine time only.
class Llama3LocalProvider(LLMProvider):
    name = "llama-3-local"

    def __init__(self, model_path: str | None = None, n_ctx: int = 4096):
        self.model_path = model_path or os.getenv("LLAMA_MODEL_PATH", "")
        self.n_ctx = n_ctx
        self._llm: Any = None  # lazy
        # Display name uses the file basename when available
        if self.model_path:
            self.name = f"llama-3-local:{os.path.basename(self.model_path)}"

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        if not self.model_path:
            raise ExtractionError(
                "LLAMA_MODEL_PATH is not set. Download a .gguf model and "
                "export LLAMA_MODEL_PATH=/path/to/model.gguf"
            )
        if not os.path.exists(self.model_path):
            raise ExtractionError(f"Model file not found: {self.model_path}")
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise ExtractionError(
                "llama-cpp-python not installed. `pip install llama-cpp-python`"
            ) from e
        self._llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            verbose=False,
        )

    def query(self, prompt: str, system: str = "") -> str:
        self._ensure_loaded()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._llm.create_chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
        except Exception as e:
            raise ExtractionError(f"Llama 3 local error: {e}") from e
        choices = resp.get("choices", []) if isinstance(resp, dict) else []
        return choices[0].get("message", {}).get("content", "") if choices else ""

    def extract_features(
        self,
        article_text: str,
        indicator_id: str,
        feature_spec: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        self._ensure_loaded()
        prompt = self.build_prompt(article_text, indicator_id, feature_spec)
        usage = ExtractionUsage()
        t0 = time.perf_counter()
        try:
            resp = self._llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Output ONLY valid JSON. No prose, no markdown fences.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise ExtractionError(f"Llama 3 local error: {e}") from e
        finally:
            usage.latency_ms = int((time.perf_counter() - t0) * 1000)

        choices = resp.get("choices", []) if isinstance(resp, dict) else []
        usage.raw_response = (
            choices[0].get("message", {}).get("content", "") if choices else ""
        )
        usage_block = resp.get("usage", {}) if isinstance(resp, dict) else {}
        usage.input_tokens = usage_block.get("prompt_tokens", 0)
        usage.output_tokens = usage_block.get("completion_tokens", 0)
        usage.cost_usd = 0.0  # Local inference; no API charge.

        self.last_usage = usage
        return self.parse_json_response(usage.raw_response)

    def estimate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0
