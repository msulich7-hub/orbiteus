"""CRM AIModuleConfig — declarative AI surface (PR 9, canonical example)."""
from orbiteus_core.ai.config import AIModuleConfig, PromptTemplate, ai_registry

AI = AIModuleConfig(
    enabled=True,
    system_prompt=(
        "You are the CRM assistant for {{ tenant.name }}. "
        "Always cite source records as `<model>.<id>` when referring to specific "
        "leads or persons. Honour RBAC; never widen access on behalf of the user."
    ),
    accessible_models=["crm.person", "crm.lead", "crm.stage", "crm.team"],
    callable_actions=[
        "crm.person.create",
        "crm.lead.create",
        "crm.lead.move_stage",
    ],
    embed_models=["crm.person", "crm.lead"],
    suggested_prompts=[
        PromptTemplate(id="hot_leads", label="Hot leads this week"),
        PromptTemplate(id="weekly_summary", label="Weekly team summary"),
        PromptTemplate(id="rotting", label="Leads stuck > 14 days"),
    ],
    dashboard=True,
)

# Register at import time so module bootstrap picks it up automatically.
ai_registry.register("crm", AI)
