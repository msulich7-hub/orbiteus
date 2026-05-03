"""Provider abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Raised on provider-side failures or misconfiguration."""


@dataclass
class ChatResult:
    """Normalized provider response."""

    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage_tokens: int = 0
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    """Provider ABC. Concrete adapters live alongside in this package."""

    name: str = ""

    @abstractmethod
    async def ping(self, api_key: str) -> bool:
        """Cheap call confirming the credential works."""

    @abstractmethod
    async def chat(
        self,
        api_key: str,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ChatResult:
        """Send messages, return text + optional tool calls."""

    @abstractmethod
    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Return one vector per input text."""
