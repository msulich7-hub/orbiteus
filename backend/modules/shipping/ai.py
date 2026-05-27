"""Shipping AIModuleConfig — dispatch assistant (enqueue-only tools)."""

from __future__ import annotations

from orbiteus_core.ai.config import AIModuleConfig, PromptTemplate, ai_registry

AI = AIModuleConfig(
    enabled=True,
    system_prompt=(
        "You are the logistics assistant for {{ tenant.name }}. "
        "IFS inbound rows are shipping.ifs_queue; kiosk work uses shipping.dispatch "
        "and shipping.waybill. Never call carrier APIs directly — only enqueue via actions."
    ),
    accessible_models=[
        "shipping.ifs_queue",
        "shipping.dispatch",
        "shipping.waybill",
        "shipping.shipment",
    ],
    callable_actions=[
        "shipping.ifs_queue.list",
        "shipping.carriers.status",
    ],
    embed_models=["shipping.ifs_queue"],
    suggested_prompts=[
        PromptTemplate(id="ifs_inbox", label="What is queued from IFS today?"),
        PromptTemplate(id="carrier_status", label="Which carriers are configured?"),
    ],
    dashboard=False,
)

ai_registry.register("shipping", AI)
