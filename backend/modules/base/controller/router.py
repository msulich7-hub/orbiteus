"""Base module custom endpoints (beyond auto-CRUD)."""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth, require_superadmin

router = APIRouter(tags=["base"])

_BRANDING_KEYS = ("app.name", "app.logo_url", "app.favicon_url")
_BRANDING_DEFAULTS = {
    "app.name": "Orbiteus",
    "app.logo_url": "/branding/logo.svg",
    "app.favicon_url": "/branding/logo.svg",
}


@router.get("/branding")
async def get_branding(session: AsyncSession = Depends(get_session)) -> dict:
    """Return public branding config (no auth required)."""
    from modules.base.controller.repositories import IrConfigParamRepository
    ctx = RequestContext(is_superadmin=True)
    repo = IrConfigParamRepository(session, ctx)
    result = dict(_BRANDING_DEFAULTS)
    for key in _BRANDING_KEYS:
        try:
            items, _ = await repo.search(domain=[("key", "=", key)], limit=1)
            if items:
                result[key] = items[0].value or _BRANDING_DEFAULTS[key]
        except Exception:
            pass
    return {
        "name": result["app.name"],
        "logo_url": result["app.logo_url"],
        "favicon_url": result["app.favicon_url"],
    }


@router.get("/health", include_in_schema=True)
async def health() -> dict:
    """System health check."""
    return {"status": "ok", "service": "orbiteus-backend"}


@router.get("/audit-log")
async def list_audit_log(
    model: str | None = Query(default=None),
    record_id: uuid.UUID | None = Query(default=None),
    actor: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, le=1000, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Read the audit log (RBAC-gated; tenant-scoped unless superadmin).

    Filters:
        - model         e.g. ?model=crm.customer
        - record_id     e.g. ?record_id=<uuid>
        - actor         user | ai | system
        - operation     create | update | delete | tool_call | login | login_failed
        - user_id       filter by acting user

    Returns paginated rows ordered by `create_date DESC`.
    """
    from sqlalchemy import desc, select

    from modules.base.model.mapping import ir_audit_log_table as t

    stmt = select(t)
    if not ctx.is_superadmin and ctx.tenant_id is not None:
        stmt = stmt.where(t.c.tenant_id == ctx.tenant_id)
    if model is not None:
        stmt = stmt.where(t.c.model == model)
    if record_id is not None:
        stmt = stmt.where(t.c.record_id == record_id)
    if actor is not None:
        stmt = stmt.where(t.c.actor == actor)
    if operation is not None:
        stmt = stmt.where(t.c.operation == operation)
    if user_id is not None:
        stmt = stmt.where(t.c.user_id == user_id)

    # Total count for pagination.
    from sqlalchemy import func
    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    stmt = stmt.order_by(desc(t.c.create_date)).offset(offset).limit(limit)
    rows = (await session.execute(stmt)).mappings().all()

    return {
        "items": [
            {
                "id": str(r["id"]),
                "create_date": r["create_date"].isoformat() if r["create_date"] else None,
                "tenant_id": str(r["tenant_id"]) if r["tenant_id"] else None,
                "actor": r["actor"],
                "user_id": str(r["user_id"]) if r["user_id"] else None,
                "request_id": r["request_id"],
                "model": r["model"],
                "record_id": str(r["record_id"]) if r["record_id"] else None,
                "operation": r["operation"],
                "diff": r["diff"],
                "metadata": r["metadata"],
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Webhook subscribers (CRUD + test ping). Auto-CRUD is intentionally NOT
# used here: the conditional UI ("field_filter only meaningful when
# record.updated is in event_mask") and the secret rotation flow are too
# specific for the generic builder.
# ---------------------------------------------------------------------------

ALLOWED_EVENTS = ("record.created", "record.updated", "record.deleted")


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    secret: str | None = None  # auto-generated when missing
    event_mask: list[str] = Field(default_factory=list)
    model_filter: str | None = None
    field_filter: list[str] = Field(default_factory=list)
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    event_mask: list[str] | None = None
    model_filter: str | None = None
    field_filter: list[str] | None = None
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    is_active: bool | None = None


def _serialise_webhook(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "url": row["url"],
        "event_mask": row["event_mask"] or [],
        "model_filter": row["model_filter"],
        "field_filter": row["field_filter"] or [],
        "auth_header_name": row["auth_header_name"],
        # Never echo the auth value, secret, or HMAC key back to the
        # client. Operators can rotate them via PUT.
        "has_auth_header_value": bool(row["auth_header_value"]),
        "has_secret": bool(row["secret"]),
        "is_active": row["is_active"],
        "last_delivery_at": row["last_delivery_at"],
        "last_delivery_status": row["last_delivery_status"],
        "create_date": row["create_date"].isoformat() if row["create_date"] else None,
    }


def _validate_event_mask(mask: list[str]) -> None:
    bad = [e for e in mask if e not in ALLOWED_EVENTS]
    if bad:
        raise HTTPException(
            status_code=422,
            detail={"code": "webhook.invalid_event", "events": bad,
                    "allowed": list(ALLOWED_EVENTS)},
        )


@router.get("/webhooks")
async def list_webhooks(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Return webhook subscribers for the caller's tenant."""
    from sqlalchemy import select, desc

    from modules.base.model.mapping import ir_webhooks_table as t

    if ctx.tenant_id is None:
        return {"items": []}
    stmt = select(t).where(t.c.tenant_id == ctx.tenant_id, t.c.active == True)  # noqa: E712
    stmt = stmt.order_by(desc(t.c.create_date))
    rows = (await session.execute(stmt)).mappings().all()
    return {"items": [_serialise_webhook(r) for r in rows]}


@router.post("/webhooks", status_code=201)
async def create_webhook(
    payload: WebhookCreate,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Register a new webhook subscriber."""
    from sqlalchemy import insert, select

    from modules.base.model.mapping import ir_webhooks_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")
    _validate_event_mask(payload.event_mask)

    secret = (payload.secret or secrets.token_urlsafe(32)).strip()
    new_id = uuid.uuid4()
    await session.execute(
        insert(t).values(
            id=new_id,
            tenant_id=ctx.tenant_id,
            name=payload.name,
            url=payload.url,
            secret=secret,
            event_mask=payload.event_mask,
            model_filter=payload.model_filter or None,
            field_filter=payload.field_filter or [],
            auth_header_name=payload.auth_header_name or None,
            auth_header_value=payload.auth_header_value or None,
            is_active=payload.is_active,
            created_by_id=ctx.user_id,
            modified_by_id=ctx.user_id,
        )
    )
    await session.commit()

    row = (await session.execute(select(t).where(t.c.id == new_id))).mappings().first()
    out = _serialise_webhook(row) if row else {"id": str(new_id)}
    # Return the freshly-generated secret ONCE on create so the operator
    # can copy it. Subsequent reads only flag that a secret exists.
    out["secret"] = secret
    return out


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: uuid.UUID,
    payload: WebhookUpdate,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Update a webhook subscriber. Empty fields keep their previous value."""
    from sqlalchemy import select, update

    from modules.base.model.mapping import ir_webhooks_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    where = (t.c.id == webhook_id) & (t.c.tenant_id == ctx.tenant_id)
    existing = (await session.execute(select(t).where(where))).mappings().first()
    if existing is None:
        raise HTTPException(status_code=404, detail="webhook not found")

    values: dict = {"modified_by_id": ctx.user_id}
    if payload.name is not None:           values["name"] = payload.name
    if payload.url is not None:            values["url"] = payload.url
    if payload.secret is not None and payload.secret.strip():
                                            values["secret"] = payload.secret.strip()
    if payload.event_mask is not None:
        _validate_event_mask(payload.event_mask)
        values["event_mask"] = payload.event_mask
    if payload.model_filter is not None:
        values["model_filter"] = payload.model_filter or None
    if payload.field_filter is not None:
        values["field_filter"] = payload.field_filter
    if payload.auth_header_name is not None:
        values["auth_header_name"] = payload.auth_header_name or None
    if payload.auth_header_value is not None:
        values["auth_header_value"] = payload.auth_header_value or None
    if payload.is_active is not None:      values["is_active"] = payload.is_active

    await session.execute(update(t).where(where).values(**values))
    await session.commit()

    row = (await session.execute(select(t).where(where))).mappings().first()
    return _serialise_webhook(row) if row else {"id": str(webhook_id)}


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> None:
    """Soft-delete (active=false) so audit trail is preserved."""
    from sqlalchemy import update

    from modules.base.model.mapping import ir_webhooks_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")
    await session.execute(
        update(t)
        .where(t.c.id == webhook_id, t.c.tenant_id == ctx.tenant_id)
        .values(active=False, modified_by_id=ctx.user_id)
    )
    await session.commit()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: uuid.UUID,
    body: dict = Body(default={}),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Send a synthetic delivery so the operator can verify the receiver."""
    from sqlalchemy import select

    from modules.base.model.mapping import ir_webhooks_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")
    where = (t.c.id == webhook_id) & (t.c.tenant_id == ctx.tenant_id)
    row = (await session.execute(select(t).where(where))).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="webhook not found")

    # Direct-delivery (skip Outbox) so the operator gets immediate feedback.
    from tasks.webhook_tasks import deliver_webhook_async

    test_payload = {
        "event": "test.ping",
        "tenant_id": str(ctx.tenant_id),
        "model": row["model_filter"] or "test.ping",
        "id": "00000000-0000-0000-0000-000000000000",
        "actor": ctx.actor,
        "request_id": ctx.request_id,
        "diff": body.get("diff") or {},
    }
    try:
        await deliver_webhook_async(
            event="test.ping",
            payload=test_payload,
            webhook_id=str(webhook_id),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail={"code": "webhook.test_failed", "message": str(exc)},
        )

    fresh = (await session.execute(select(t).where(where))).mappings().first()
    return _serialise_webhook(fresh) if fresh else {"id": str(webhook_id)}


@router.get("/modules", dependencies=[Depends(require_superadmin)])
async def list_modules() -> dict:
    """List all registered modules and their load order."""
    from orbiteus_core.registry import registry

    return {
        "modules": registry.loaded_modules,
        "total": len(registry.loaded_modules),
    }


@router.get("/menus")
async def get_menu_tree(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Return the full ir_ui_menu tree for the Admin UI sidebar."""
    from modules.base.controller.repositories import IrUiMenuRepository

    repo = IrUiMenuRepository(session, ctx)
    menus, total = await repo.search(limit=500)

    menu_dict = {str(m.id): {"id": str(m.id), "name": m.name,
                               "parent_id": str(m.parent_id) if m.parent_id else None,
                               "sequence": m.sequence, "icon": m.icon,
                               "children": []} for m in menus}

    roots = []
    for menu in menu_dict.values():
        parent_id = menu["parent_id"]
        if parent_id and parent_id in menu_dict:
            menu_dict[parent_id]["children"].append(menu)
        else:
            roots.append(menu)

    return {"menus": sorted(roots, key=lambda x: x["sequence"])}


@router.get("/view")
async def get_view(
    model: str,
    type: str = "form",
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Return resolved view arch for a given model and view type.

    Applies XPath inheritance chain and returns final XML arch as a string.
    Used by frontend to render views generically without hardcoded pages.

    Query params:
      - model: e.g. crm.customer
      - type: form / list / kanban / calendar / search  (default: form)
    """
    from modules.base.controller.repositories import IrUiViewRepository
    from orbiteus_core.view_loader import resolve_arch

    repo = IrUiViewRepository(session, ctx)

    # Load base view (no inherit_id, matching model+type)
    base_views, _ = await repo.search(
        domain=[("model", "=", model), ("type", "=", type), ("active", "=", True)],
        limit=50,
    )

    if not base_views:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No view found for model={model} type={type}")

    # Split into base (inherit_id=None) and inherited
    base = next((v for v in base_views if v.inherit_id is None), None)
    if base is None:
        # All views are inherited — use the first as base
        base = base_views[0]

    inherited = [v for v in base_views if v.inherit_id is not None]
    inherited.sort(key=lambda v: v.priority)

    resolved = resolve_arch(base.arch, [v.arch for v in inherited])

    return {
        "model": model,
        "type": type,
        "name": base.name,
        "arch": resolved,
        "inherit_count": len(inherited),
    }


def _pydantic_to_ui_type(name: str, annotation: object) -> str:
    ann = str(annotation)
    if "bool" in ann:
        return "boolean"
    if "int" in ann or "float" in ann:
        return "number"
    if "UUID" in ann and name.endswith("_id"):
        return "select"
    if name == "email":
        return "email"
    if name in ("phone", "mobile"):
        return "tel"
    if name.endswith("_date") or name in ("date", "close_date"):
        return "date"
    if name in ("notes", "description") or name.endswith("_html"):
        return "textarea"
    return "text"


_SKIP_FIELDS = {"tenant_id", "company_id", "tags", "workflow_run_id"}


def _extract_schema_fields(write_schema: type) -> list[dict]:
    result = []
    for name, field_info in write_schema.model_fields.items():
        if name in _SKIP_FIELDS:
            continue
        result.append({
            "name": name,
            "type": _pydantic_to_ui_type(name, field_info.annotation),
            "required": field_info.is_required(),
            "label": name.replace("_", " ").title(),
        })
    return result


@router.get("/ui-config")
async def get_ui_config() -> dict:
    """Return full UI configuration for dynamic frontend rendering.

    Uses in-memory registry (XML views + Pydantic schema introspection) —
    no DB query needed, always consistent with the loaded modules.
    """
    from orbiteus_core.ui_config import build_ui_config
    return build_ui_config()


@router.post("/rbac/reload", dependencies=[Depends(require_superadmin)])
async def reload_rbac(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Reload RBAC cache from YAML files and re-seed to DB.

    Use after changing security/access.yaml files without restarting the server.
    Requires superadmin role.
    """
    from orbiteus_core.security import rbac
    from orbiteus_core.registry import registry

    # Clear existing cache
    rbac._model_access.clear()
    rbac._record_rules.clear()

    # Re-apply all YAML security configs
    from orbiteus_core.security_loader import apply_security_to_cache, seed_security_to_db

    reloaded = []
    for name in registry.loaded_modules:
        desc = registry.get_module(name)
        config = getattr(desc, "_security_config", None)
        if config:
            apply_security_to_cache(config)
            await seed_security_to_db(config, session, ctx)
            reloaded.append(name)

    await session.commit()

    return {
        "status": "reloaded",
        "modules": reloaded,
        "access_entries": sum(len(v) for v in rbac._model_access.values()),
        "record_rules": sum(len(v) for v in rbac._record_rules.values()),
    }
