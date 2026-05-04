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
# Chat (non-streaming MVP — streaming variant planned for PR 11)
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """One-shot chat with the tenant's configured provider.

    Body: `{ "messages": [...], "scope": "module:crm" | "global", "model": optional }`
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

    # PII redaction before remote call.
    messages = redact_payload(body.get("messages") or [])
    tools = build_tools(ctx, scope=body.get("scope") or "all")

    p = get_provider(provider_name)
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

    # Audit every tool call the model invoked (DoD §4.3 — `actor=ai`).
    # Tool arguments may carry the user's free-text prompt fragments,
    # so we rely on `redact_payload` (via `write_audit(redact=True)`)
    # to scrub passwords/secrets/PII before persisting.
    if result.tool_calls:
        from orbiteus_core.audit import write_audit

        for tool_call in result.tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else None
            tool_args = tool_call.get("arguments") if isinstance(tool_call, dict) else None
            tool_id = tool_call.get("id") if isinstance(tool_call, dict) else None
            await write_audit(
                session,
                actor="ai",
                operation="tool_call",
                model="ai.tool",
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                diff={
                    "name": tool_name,
                    "arguments": tool_args,
                    "tool_call_id": tool_id,
                },
                metadata={
                    "provider": provider_name,
                    "ai_model": body.get("model") or cred.get("model_default"),
                    "scope": body.get("scope") or "all",
                    "usage_tokens": result.usage_tokens,
                },
            )
        await session.commit()

    return {
        "text": result.text,
        "tool_calls": result.tool_calls,
        "usage_tokens": result.usage_tokens,
        "finish_reason": result.finish_reason,
    }


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
