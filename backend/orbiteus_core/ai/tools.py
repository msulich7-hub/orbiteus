"""Build the tool list for an AI chat session.

Three sources (docs/15-ai-layer.md):
  1. `Action` registry — callable navigations / mutations.
  2. `QueryTool` per accessible model — read via BaseRepository.
  3. `semantic_search` — pgvector similarity (when embeddings exist).

Tools returned here are provider-agnostic: a list of `{name, description,
parameters}` dicts. Each provider adapter (anthropic / openai / ollama)
shapes them to its own function-calling format.
"""
from __future__ import annotations

import json
from typing import Any

from orbiteus_core.ai.config import ai_registry
from orbiteus_core.ai.registry import action_registry
from orbiteus_core.context import RequestContext


def _query_tool_for(model: str) -> dict[str, Any]:
    safe_name = model.replace(".", "_")
    return {
        "name": f"read_{safe_name}",
        "description": (
            f"Read records from the {model} model. Returns a paginated list. "
            "RBAC and tenant isolation are enforced server-side."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {"type": "object", "description": "Optional Odoo-style domain dict"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 25},
            },
            "required": [],
        },
    }


def _action_tool_for(action) -> dict[str, Any]:
    return {
        "name": action.id.replace(".", "_"),
        "description": action.description or action.label,
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Optional record id"},
            },
            "required": [],
        },
    }


def build_tools(ctx: RequestContext, scope: str = "all") -> list[dict[str, Any]]:
    """Build tool list scoped to the user's RBAC and the registered AI configs.

    `scope` is reserved for narrower scopes (e.g. "module:crm" — only emit
    tools from that module). Default emits everything declared.
    """
    tools: list[dict[str, Any]] = []
    accessible = ai_registry.accessible_models()
    callable_actions = ai_registry.callable_actions()

    # 1) Per-model read tools.
    for model in sorted(accessible):
        tools.append(_query_tool_for(model))

    # 2) Action tools (filtered by RBAC).
    actions = action_registry.get_all()
    for action in actions:
        if action.id not in callable_actions:
            continue
        tools.append(_action_tool_for(action))

    # 3) Semantic search if any module declares embeddings.
    if ai_registry.embed_models():
        tools.append(
            {
                "name": "semantic_search",
                "description": (
                    "Semantic search across embedded records the caller can read."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                    },
                    "required": ["model", "query"],
                },
            }
        )

    return tools
