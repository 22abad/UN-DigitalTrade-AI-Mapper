"""LLM provider abstraction layer.

The hackathon scoring rubric awards 40 points (Stage 1 + Stage 3) for designs
that work when the LLM is swapped for an open-weight model (e.g. Llama 3).
This package implements that swappability.

Usage:
    from providers import get_default_provider, get_provider

    p = get_default_provider()                 # picks based on RDTII_LLM_PROVIDER env var
    p = get_provider("claude")                 # explicit
    features = p.extract_features(article, "6.1", spec)

Adding a new provider:
    1. Subclass `LLMProvider` in providers/<name>.py
    2. Implement `extract_features()` and `estimate_cost_usd()`
    3. Register in `_REGISTRY` below
"""

from __future__ import annotations

import importlib
import os
from typing import Type

from .base import LLMProvider

# Module-path / class-name pairs — loaded lazily so importing this package
# doesn't require every provider's SDK to be installed.
#
# The keys here are the CANONICAL names returned by `list_providers()` and
# shown via `/providers`. Aliases (different spellings of the same name)
# are normalised in `_canonicalise()`, so the public list stays
# unambiguous (no duplicate llama3 entries).
_LAZY_REGISTRY: dict[str, tuple[str, str]] = {
    # Native SDKs
    "gemini": (".gemini", "GeminiProvider"),
    "claude": (".claude", "ClaudeProvider"),
    "llama-3-local": (".llama_local", "Llama3LocalProvider"),
    # Ollama — local model server with OpenAI-compatible API
    "ollama": (".ollama", "OllamaProvider"),
    # OpenAI-compatible (single SDK, many vendors via base_url)
    "openai": (".openai_compatible", "OpenAIProvider"),
    "deepseek": (".openai_compatible", "DeepSeekProvider"),
    "groq": (".openai_compatible", "GroqProvider"),
    "together": (".openai_compatible", "TogetherProvider"),
    "openrouter": (".openai_compatible", "OpenRouterProvider"),
    "mistral": (".openai_compatible", "MistralProvider"),
}

# User-friendly aliases that map onto a canonical key.
# NOTE: keys here are matched AFTER `_canonicalise` lower-cases, strips,
# and replaces "_" with "-". So underscore-bearing aliases (e.g.
# "llama_3_local") would never be reached and must not be added here.
_ALIASES: dict[str, str] = {
    "llama3": "llama-3-local",
    "llama3-local": "llama-3-local",
    "llama-3": "llama-3-local",
}


def _canonicalise(name: str) -> str:
    norm = name.lower().strip().replace("_", "-")
    return _ALIASES.get(norm, norm)


def canonical_name(name: str) -> str | None:
    """Public alias normaliser — returns the canonical key for `name`.

    Returns `None` when `name` does not resolve to any registered provider.
    Returning `None` (rather than echoing the raw input) lets status
    endpoints surface misconfiguration explicitly: with the previous
    behaviour, an invalid `RDTII_LLM_PROVIDER=foo` looked like a healthy
    `active=foo` even though `foo` was absent from `available_providers`,
    breaking the "active is one of available" contract.
    """
    canonical = _canonicalise(name)
    return canonical if canonical in _LAZY_REGISTRY else None


def is_recognised(name: str) -> bool:
    """Return True if `name` (or any alias of it) maps to a registered provider."""
    return canonical_name(name) is not None


def _load_class(name: str) -> Type[LLMProvider]:
    canonical = _canonicalise(name)
    if canonical not in _LAZY_REGISTRY:
        available = ", ".join(sorted(_LAZY_REGISTRY.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    module_path, class_name = _LAZY_REGISTRY[canonical]
    module = importlib.import_module(module_path, package=__name__)
    return getattr(module, class_name)


def get_provider(name: str) -> LLMProvider:
    """Return an instance of the named provider.

    Names are case-insensitive and tolerant of aliases (e.g. `llama3` and
    `llama-3-local` both resolve to the local Llama 3 provider).
    Raises ValueError for unknown names; ExtractionError if the SDK or API
    key for the chosen provider is missing.
    """
    cls = _load_class(name)
    return cls()


def get_default_provider() -> LLMProvider:
    """Return the provider configured via env var, or fall back to Gemini.

    Read order: RDTII_LLM_PROVIDER -> default 'gemini'.
    """
    name = os.getenv("RDTII_LLM_PROVIDER", "gemini")
    return get_provider(name)


def list_providers() -> list[str]:
    """Return registered provider keys."""
    return sorted(_LAZY_REGISTRY.keys())


__all__ = [
    "LLMProvider",
    "canonical_name",
    "get_provider",
    "get_default_provider",
    "is_recognised",
    "list_providers",
]
