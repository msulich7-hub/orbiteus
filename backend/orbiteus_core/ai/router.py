"""HTTP routes for the AI layer.

- /api/ai/actions       — Command Palette resolver (RapidFuzz, no LLM)
- /api/ai/credentials   — BYOK CRUD (POST/GET/DELETE)
- /api/ai/chat          — non-streaming chat (provider tool calling)
- /api/ai/dashboard     — NL → aggregate query → chart spec
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.budget import has_budget, increment
from orbiteus_core.ai.config import ai_registry
from orbiteus_core.ai.keys import fetch_credential, store_credential
from orbiteus_core.ai.providers import ProviderError, get_provider
from orbiteus_core.ai.redaction import redact_payload
from orbiteus_core.ai.resolver import resolve as resolve_actions
from orbiteus_core.ai.tools import build_tools
from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import (
    get_current_context,
    require_auth,
    require_superadmin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Command Palette resolver (already used by admin UI, kept for back-compat).
# ---------------------------------------------------------------------------

@router.get("/actions")
async def get_actions(
    q: str = Query(default=""),
    limit: int = Query(default=8, le=20, ge=1),
    ctx: RequestContext = Depends(get_current_context),
) -> dict:
    return {"items": resolve_actions(q, ctx, limit=limit)}


# ---------------------------------------------------------------------------
# BYOK credentials CRUD
# ---------------------------------------------------------------------------

@router.post("/credentials")
async def upsert_credential(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Store or update a provider credential for the caller's tenant.

    Body: `{ "provider": "anthropic|openai|ollama",
             "secret": "<api-key>",
             "model_default": "claude-3-5-sonnet-latest",
             "monthly_token_budget": 1000000 }`
    """
    provider = (body.get("provider") or "").lower()
    secret = body.get("secret")
    if provider not in {"anthropic", "openai", "ollama"}:
        raise HTTPException(status_code=400, detail="provider must be one of anthropic|openai|ollama")
    if not secret:
        raise HTTPException(status_code=400, detail="secret is required")
    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    # Provider ping with the supplied secret; fail-fast on bad keys.
    p = get_provider(provider)
    ok = await p.ping(secret)
    if not ok:
        raise HTTPException(status_code=400, detail="provider rejected the supplied credential")

    cred_id = await store_credential(
        session,
        tenant_id=ctx.tenant_id,
        provider=provider,
        secret=secret,
        model_default=body.get("model_default"),
        monthly_token_budget=body.get("monthly_token_budget"),
    )
    await session.commit()
    return {"id": str(cred_id), "provider": provider}


@router.get("/credentials")
async def list_credentials(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """List configured providers for the tenant — never returns secrets."""
    from sqlalchemy import select

    from modules.base.model.mapping import ir_ai_credentials_table as t

    if ctx.tenant_id is None:
        return {"items": []}

    rows = (
        await session.execute(
            select(
                t.c.id,
                t.c.provider,
                t.c.model_default,
                t.c.is_active,
                t.c.monthly_token_budget,
                t.c.usage_tokens,
            ).where(t.c.tenant_id == ctx.tenant_id)
        )
    ).all()
    return {
        "items": [
            {
                "id": str(r[0]),
                "provider": r[1],
                "model_default": r[2],
                "is_active": r[3],
                "monthly_token_budget": r[4],
                "usage_tokens": r[5],
            }
            for r in rows
        ]
    }


@router.delete("/credentials/{provider}")
async def delete_credential(
    provider: str,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    from sqlalchemy import delete

    from modules.base.model.mapping import ir_ai_credentials_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")
    await session.execute(
        delete(t).where(t.c.tenant_id == ctx.tenant_id, t.c.provider == provider.lower())
    )
    await session.commit()
    return {"deleted": provider}


# ---------------------------------------------------------------------------
# Chat — non-streaming + streaming (DoD §8.8)
# ---------------------------------------------------------------------------

async def _resolve_chat_inputs(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
) -> tuple[Any, dict, list, list, str]:
    """Shared validation for both chat endpoints.

    Returns ``(provider, credential, messages, tools, provider_name)``.
    Raises ``HTTPException`` on missing tenant, missing credential, or
    exhausted budget — same shape both endpoints used to encode inline.
    """
    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    provider_name = (body.get("provider") or "anthropic").lower()
    cred = await fetch_credential(session, tenant_id=ctx.tenant_id, provider=provider_name)
    if cred is None:
        raise HTTPException(
            status_code=412,
            detail={
                "code": "ai.no_credential",
                "message": f"No active {provider_name} credential for this tenant. "
                           "POST /api/ai/credentials first.",
            },
        )

    if not await has_budget(ctx.tenant_id, cred.get("monthly_token_budget")):
        raise HTTPException(
            status_code=429,
            detail={"code": "ai.budget_exceeded", "message": "Monthly AI token budget exceeded"},
            headers={"Retry-After": "3600"},
        )

    messages = redact_payload(body.get("messages") or [])
    tools = build_tools(ctx, scope=body.get("scope") or "all")
    p = get_provider(provider_name)
    return p, cred, messages, tools, provider_name


async def _audit_tool_calls(
    session: AsyncSession,
    ctx: RequestContext,
    tool_calls: list[dict[str, Any]],
    *,
    provider_name: str,
    body: dict,
    cred: dict,
    usage_tokens: int,
) -> None:
    """Append one `actor=ai, operation=tool_call` row per invocation."""
    if not tool_calls:
        return
    from orbiteus_core.audit import write_audit

    for tool_call in tool_calls:
        await write_audit(
            session,
            actor="ai",
            operation="tool_call",
            model="ai.tool",
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            diff={
                "name": tool_call.get("name"),
                "arguments": tool_call.get("arguments"),
                "tool_call_id": tool_call.get("id"),
            },
            metadata={
                "provider": provider_name,
                "ai_model": body.get("model") or cred.get("model_default"),
                "scope": body.get("scope") or "all",
                "usage_tokens": usage_tokens,
            },
        )
    await session.commit()


@router.post("/chat")
async def chat(
    body: dict = Body(...),
    stream: int = Query(0, description="Pass 1 for SSE streaming response"),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> Any:
    """Chat with the tenant's configured provider.

    Body: `{ "messages": [...], "scope": "module:crm" | "global", "model": optional }`

    With ``?stream=1`` the response is `text/event-stream` (SSE):

      event: text          → {"delta": "..."}
      event: tool_call     → {"id": ..., "name": ..., "arguments": {...}}
      event: done          → {"usage_tokens": int, "finish_reason": "..."}

    Otherwise it's a regular JSON response — see schema below.
    """
    if stream:
        return await _chat_stream(body, session, ctx)
    return await _chat_oneshot(body, session, ctx)


async def _chat_oneshot(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
) -> dict:
    """Original non-streaming chat. Body is the same as `/chat`."""
    p, cred, messages, tools, provider_name = await _resolve_chat_inputs(body, session, ctx)
    try:
        result = await p.chat(
            cred["secret"],
            messages=messages,
            tools=tools,
            model=body.get("model") or cred.get("model_default"),
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if result.usage_tokens:
        await increment(ctx.tenant_id, result.usage_tokens)

    await _audit_tool_calls(
        session, ctx, result.tool_calls,
        provider_name=provider_name, body=body, cred=cred,
        usage_tokens=result.usage_tokens,
    )

    return {
        "text": result.text,
        "tool_calls": result.tool_calls,
        "usage_tokens": result.usage_tokens,
        "finish_reason": result.finish_reason,
    }


async def _chat_stream(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
):
    """Streaming variant — returns a `text/event-stream` `StreamingResponse`."""
    import json as _json

    from fastapi.responses import StreamingResponse

    p, cred, messages, tools, provider_name = await _resolve_chat_inputs(body, session, ctx)

    async def _sse() -> Any:
        accumulated_tool_calls: list[dict[str, Any]] = []
        usage_tokens = 0
        finish_reason = "stop"
        try:
            async for event in p.chat_stream(
                cred["secret"],
                messages=messages,
                tools=tools,
                model=body.get("model") or cred.get("model_default"),
            ):
                yield (
                    f"event: {event.kind}\n"
                    f"data: {_json.dumps(event.data)}\n\n"
                ).encode("utf-8")

                if event.kind == "tool_call":
                    accumulated_tool_calls.append(event.data)
                elif event.kind == "done":
                    usage_tokens = int(event.data.get("usage_tokens", 0) or 0)
                    finish_reason = str(event.data.get("finish_reason") or "stop")
        except ProviderError as exc:
            yield (
                "event: error\n"
                f"data: {_json.dumps({'detail': str(exc)})}\n\n"
            ).encode("utf-8")
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai.chat_stream.failed")
            yield (
                "event: error\n"
                f"data: {_json.dumps({'detail': 'internal error', 'kind': type(exc).__name__})}\n\n"
            ).encode("utf-8")
            return

        # After the SSE stream finishes, persist usage + audit.
        if usage_tokens:
            try:
                await increment(ctx.tenant_id, usage_tokens)
            except Exception:  # noqa: BLE001
                logger.exception("ai.chat_stream.budget_increment_failed")
        try:
            await _audit_tool_calls(
                session, ctx, accumulated_tool_calls,
                provider_name=provider_name, body=body, cred=cred,
                usage_tokens=usage_tokens,
            )
        except Exception:  # noqa: BLE001
            logger.exception("ai.chat_stream.audit_failed")

    return StreamingResponse(_sse(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Dashboard generator (NL → aggregate spec)
# ---------------------------------------------------------------------------

@router.post("/dashboard")
async def dashboard(
    body: dict = Body(...),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Return a chart spec built from a natural-language prompt.

    For MVP the front-end is responsible for executing the aggregate query
    that the AI returned (so we never grant AI direct DB access). The
    response shape is stable so the UI can render with recharts.
    """
    if not ai_registry.accessible_models():
        raise HTTPException(status_code=412, detail="No AI module configured for this tenant")

    prompt = body.get("prompt") or ""
    return {
        "title": prompt[:80] or "AI dashboard",
        "chart_type": "bar",
        "x_axis": "group",
        "y_axis": "value",
        "data": [],
        "note": "MVP placeholder — PR 11 wires AI provider call to /api/base/aggregate",
    }
