"""Base Agent abstraction for RDTII MAS.

All specialized agents inherit from this base class to ensure consistent
interface and telemetry tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from providers.base import LLMProvider


class Agent(ABC):
    """Abstract Base Class for all MAS Agents."""

    def __init__(
        self,
        role: str,
        system_prompt: str,
        provider: LLMProvider,
    ):
        self.role = role
        self.system_prompt = system_prompt
        self.provider = provider

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """Run the agent's core business logic asynchronously."""
        ...
