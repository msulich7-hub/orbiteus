"""CRM automation engine v1 (SPEC-006).

Evaluates active rules for a trigger event and executes supported actions.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

from modules.crm.model.domain import AutomationRule, Lead, Stage

logger = logging.getLogger(__name__)

TRIGGER_LEAD_STAGE_CHANGED = "crm.lead.stage_changed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _matches_condition(condition_json: dict[str, Any], context: dict[str, Any]) -> bool:
    """All condition keys must match context values (v1 — equality only)."""
    if not condition_json:
        return True
    for key, expected in condition_json.items():
        actual = context.get(key)
        if isinstance(expected, str) and isinstance(actual, uuid.UUID):
            actual = str(actual)
        if actual != expected:
            return False
    return True


async def _execute_create_activity(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    lead_id: uuid.UUID,
    lead: Lead,
    action_json: dict[str, Any],
) -> None:
    from modules.crm.controller.repositories import ActivityRepository

    activity_repo = ActivityRepository(session, ctx)
    due_date = None
    due_days = action_json.get("due_days")
    if due_days is not None:
        due_date = _utcnow() + timedelta(days=int(due_days))

    await activity_repo.create({
        "subject": action_json.get("subject", "Follow up"),
        "activity_type": action_json.get("activity_type", "task"),
        "due_date": due_date,
        "assigned_user_id": (
            action_json.get("assigned_user_id")
            or lead.assigned_user_id
            or ctx.user_id
        ),
        "res_model": "crm.lead",
        "res_id": lead_id,
        "notes": action_json.get("notes", ""),
    })


async def _execute_notify(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    rule: AutomationRule,
    context: dict[str, Any],
) -> None:
    from orbiteus_core.outbox import enqueue

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="crm.automation.notify",
        payload={
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "trigger_event": rule.trigger_event,
            "context": {
                k: str(v) if isinstance(v, uuid.UUID) else v
                for k, v in context.items()
                if k not in ("lead", "to_stage")
            },
            **(rule.action_json or {}),
        },
        target_kind="notification",
    )


async def _execute_rule(
    session: AsyncSession,
    ctx: RequestContext,
    rule: AutomationRule,
    context: dict[str, Any],
) -> None:
    lead = context.get("lead")
    lead_id = context.get("lead_id")

    if rule.action_type == "create_activity":
        if not isinstance(lead, Lead) or lead_id is None:
            logger.warning(
                "crm.automation.skipped_missing_lead",
                extra={"rule_id": str(rule.id), "action_type": rule.action_type},
            )
            return
        await _execute_create_activity(
            session,
            ctx,
            lead_id=lead_id,
            lead=lead,
            action_json=rule.action_json or {},
        )
    elif rule.action_type == "notify":
        await _execute_notify(session, ctx, rule=rule, context=context)
    else:
        logger.warning(
            "crm.automation.unsupported_action",
            extra={"rule_id": str(rule.id), "action_type": rule.action_type},
        )


async def evaluate_automation_rules(
    session: AsyncSession,
    ctx: RequestContext,
    trigger_event: str,
    context: dict[str, Any],
) -> None:
    """Run all active rules matching trigger_event and optional conditions."""
    from modules.crm.controller.repositories import AutomationRuleRepository

    rule_repo = AutomationRuleRepository(session, ctx)
    rules, _ = await rule_repo.search(
        domain=[("trigger_event", "=", trigger_event), ("active", "=", True)],
        limit=200,
    )

    for rule in rules:
        if not _matches_condition(rule.condition_json or {}, context):
            continue
        await _execute_rule(session, ctx, rule, context)
        logger.info(
            "crm.automation.executed",
            extra={
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "trigger_event": trigger_event,
                "action_type": rule.action_type,
            },
        )


async def evaluate_lead_stage_changed(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    lead: Lead,
    lead_id: uuid.UUID,
    from_stage_id: uuid.UUID | None,
    to_stage: Stage,
) -> None:
    """Evaluate automation rules after a lead stage transition."""
    context = {
        "lead_id": lead_id,
        "lead": lead,
        "from_stage_id": from_stage_id,
        "to_stage_id": to_stage.id,
        "to_stage_name": to_stage.name,
    }
    await evaluate_automation_rules(
        session,
        ctx,
        TRIGGER_LEAD_STAGE_CHANGED,
        context,
    )
