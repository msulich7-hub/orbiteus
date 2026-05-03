"""Anthropic Claude adapter."""
from __future__ import annotations

import logging
from typing import Any

from .base import ChatResult, Provider, ProviderError

logger = logging.getLogger(__name__)


class AnthropicProvider(Provider):
    name = "anthropic"
    default_chat_model = "claude-3-5-sonnet-latest"
    # Anthropic does not ship a first-party embeddings model; we delegate
    # embeddings to OpenAI / sentence-transformers as a fallback. AI layer
    # rejects embed calls on this provider unless the workflow supplies an
    # alternative.
    default_embed_model = ""

    async def ping(self, api_key: str) -> bool:
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("anthropic SDK not installed") from exc
        client = anthropic.AsyncAnthropic(api_key=api_key)
        # Minimal request that costs the least; treat any 200 as healthy.
        try:
            await client.messages.create(
                model=self.default_chat_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("anthropic.ping_failed", extra={"error": str(exc)[:200]})
            return False

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
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("anthropic SDK not installed") from exc

        client = anthropic.AsyncAnthropic(api_key=api_key)
        # Anthropic separates the `system` prompt from messages; lift it.
        system_prompt = ""
        chat_messages: list[dict[str, Any]] = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                chat_messages.append(m)

        kwargs: dict[str, Any] = {
            "model": model or self.default_chat_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools

        resp = await client.messages.create(**kwargs)
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "arguments": block.input}
                )
        return ChatResult(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage_tokens=getattr(resp.usage, "output_tokens", 0) + getattr(resp.usage, "input_tokens", 0),
            finish_reason=getattr(resp, "stop_reason", "stop") or "stop",
            raw={"id": resp.id, "model": resp.model},
        )

    async def embed(
        self,
        api_key: str,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        raise ProviderError(
            "anthropic provider does not support embeddings; configure OpenAI "
            "or local fallback for embed_models."
        )
