"""AI provider adapters (ADR-0009).

All providers implement `Provider` ABC. Engine code never imports vendor
SDKs directly — always through `get_provider(name)`.
"""
from __future__ import annotations

from .base import ChatResult, Provider, ProviderError

__all__ = ["ChatResult", "Provider", "ProviderError", "get_provider"]


def get_provider(name: str) -> Provider:
    """Return a provider instance by name.

    Lazy imports so the engine starts without all SDKs installed.
    """
    name = name.lower()
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider()
    if name == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider()
    raise ProviderError(f"unknown provider: {name}")
