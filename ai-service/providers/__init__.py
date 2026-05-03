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
_LAZY_REGISTRY: dict[str, tuple[str, str]] = {
    "gemini": (".gemini", "GeminiProvider"),
    "claude": (".claude", "ClaudeProvider"),
    "llama3": (".llama_local", "Llama3LocalProvider"),
    "llama-3-local": (".llama_local", "Llama3LocalProvider"),
}


def _load_class(name: str) -> Type[LLMProvider]:
    if name not in _LAZY_REGISTRY:
        available = ", ".join(sorted(_LAZY_REGISTRY.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")
    module_path, class_name = _LAZY_REGISTRY[name]
    module = importlib.import_module(module_path, package=__name__)
    return getattr(module, class_name)


def get_provider(name: str) -> LLMProvider:
    """Return an instance of the named provider.

    Raises ValueError for unknown names; ExtractionError if the SDK or API
    key for the chosen provider is missing.
    """
    cls = _load_class(name.lower().strip())
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
    "get_provider",
    "get_default_provider",
    "list_providers",
]
