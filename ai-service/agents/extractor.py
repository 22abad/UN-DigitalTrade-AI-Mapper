"""Extractor Agent implementation.

Locates the relevant law/act titles, specific articles, exact verbatim quotes, and
core RDTII features from the text chunk.
"""

from __future__ import annotations

import asyncio
from typing import Any
from agents.base import Agent
from providers.base import LLMProvider, ExtractionError


class ExtractorAgent(Agent):
    """Agent specialized in extracting act titles, clauses, verbatim quotes, and features."""

    def __init__(self, provider: LLMProvider):
        system_prompt = (
            "You are a UN ESCAP digital trade policy analyst. Your job is to locate "
            "exact verbatim quotes, identify legislation titles, and extract structured "
            "features from legal texts."
        )
        super().__init__(
            role="extractor",
            system_prompt=system_prompt,
            provider=provider,
        )

    async def run(
        self,
        chunk_text: str,
        indicator_id: str,
        feature_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract features, verbatim quote, act title, and clause for a single indicator."""
        try:
            return await asyncio.to_thread(
                self.provider.extract_features,
                chunk_text,
                indicator_id,
                feature_spec,
            )
        except Exception as e:
            raise ExtractionError(f"ExtractorAgent extraction failed for indicator {indicator_id}: {e}") from e

    async def run_batch(
        self,
        chunk_text: str,
        indicators: list[tuple[str, dict[str, Any]]],
    ) -> dict[str, dict[str, Any]]:
        """Extract features for multiple indicators from a single chunk in batch."""
        try:
            return await asyncio.to_thread(
                self.provider.extract_batch,
                chunk_text,
                indicators,
            )
        except Exception as e:
            raise ExtractionError(f"ExtractorAgent batch extraction failed: {e}") from e
