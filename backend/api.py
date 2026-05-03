"""ERP Backend – FastAPI application entry point.

Module registration order matters – dependencies must be registered first.
ModuleRegistry handles topological sorting automatically.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orbiteus_core.config import settings
from orbiteus_core.health import router as health_router
from orbiteus_core.observability import (
    RequestIdMiddleware,
    configure_json_logging,
    metrics_endpoint,
)
from orbiteus_core.registry import registry

# Structured JSON logs with request_id correlation (docs/29-observability.md).
configure_json_logging(level="INFO" if not settings.debug else "DEBUG")
logger = logging.getLogger(__name__)

_BRANDING_DEFAULTS = [
    ("app.name", "Orbiteus", "Application display name"),
    ("app.logo_url", "/branding/logo.svg", "URL to logo image (leave empty to use text name)"),
    ("app.favicon_url", "/branding/logo.svg", "URL to favicon"),
]

_DEFAULT_SUPERADMIN_EMAIL = settings.bootstrap_admin_email
_DEFAULT_SUPERADMIN_PASSWORD = settings.bootstrap_admin_password
_DEFAULT_TENANT_NAME = settings.bootstrap_admin_tenant_name
_DEFAULT_TENANT_SLUG = settings.bootstrap_admin_tenant_slug
# Product seeds (e.g. CRM default stages) live in the module's `bootstrap.py`,
# not in the engine lifespan. See `modules/crm/bootstrap.py` (PR 9 / ADR-0008).


async def _create_tables() -> None:
    """Create all registered SQLAlchemy tables if they don't exist."""
    from orbiteus_core.db import engine, metadata

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    logger.info("Database tables created (if not exist).")


async def _seed_default_tenant() -> "uuid.UUID":  # type: ignore[name-defined]
    """Ensure at least one Tenant row exists; return its id.

    Multi-tenancy is on by default (`docs/05-rbac-multitenancy.md`); without
    a tenant the bootstrap admin gets `tenant_id = NULL`, which then breaks
    every endpoint that requires tenant context (AI BYOK, share-link issue,
    portal-scope tokens, audit attribution).
    """
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.repositories import TenantRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = TenantRepository(session, ctx)
        existing, total = await repo.search(limit=1)
        if total > 0 and existing:
            return existing[0].id

        tenant = await repo.create({
            "name": _DEFAULT_TENANT_NAME,
            "slug": _DEFAULT_TENANT_SLUG,
            "plan": "free",
            "is_active": True,
        })
        await session.commit()
        logger.info(
            "Bootstrap default tenant created: name=%s slug=%s id=%s",
            tenant.name, tenant.slug, tenant.id,
        )
        return tenant.id


async def _seed_superadmin(default_tenant_id: "uuid.UUID") -> None:  # type: ignore[name-defined]
    """Create a default superadmin user on first startup if no users exist.

    Also backfills `tenant_id` on a pre-existing admin row so installations
    that bootstrapped before the default-tenant change don't stay stuck
    without a tenant binding.
    """
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.security.passwords import hash_password
    from modules.base.controller.repositories import UserRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = UserRepository(session, ctx)
        existing, total = await repo.search(limit=1)
        if total == 0:
            if settings.environment.lower() == "production" and _DEFAULT_SUPERADMIN_PASSWORD == "admin1234":
                raise RuntimeError(
                    "Refusing to create bootstrap superadmin with default password in production."
                )
            await repo.create({
                "tenant_id": default_tenant_id,
                "email": _DEFAULT_SUPERADMIN_EMAIL,
                "name": "Administrator",
                "password_hash": hash_password(_DEFAULT_SUPERADMIN_PASSWORD),
                "is_superadmin": True,
                "is_active": True,
                "company_ids": [],
                "role_ids": [],
            })
            await session.commit()
            logger.warning(
                "Default superadmin created: email=%s password=%s tenant=%s "
                "— CHANGE THIS IN PRODUCTION!",
                _DEFAULT_SUPERADMIN_EMAIL,
                _DEFAULT_SUPERADMIN_PASSWORD,
                default_tenant_id,
            )
            return

        # Backfill: a superadmin from the pre-default-tenant era has
        # `tenant_id IS NULL`; bind it to the default tenant so AI BYOK
        # and other tenant-scoped endpoints start working without a
        # manual SQL fix.
        admin = next(
            (u for u in existing if getattr(u, "is_superadmin", False) and u.tenant_id is None),
            None,
        )
        if admin is not None:
            await repo.update(admin.id, {"tenant_id": default_tenant_id})
            await session.commit()
            logger.warning(
                "Bound legacy superadmin %s to default tenant %s "
                "(retroactive multi-tenancy fix).",
                admin.email, default_tenant_id,
            )


async def _seed_branding() -> None:
    """Insert default branding params if not present."""
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.repositories import IrConfigParamRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = IrConfigParamRepository(session, ctx)
        for key, value, description in _BRANDING_DEFAULTS:
            existing, _ = await repo.search(domain=[("key", "=", key)], limit=1)
            if not existing:
                await repo.create({"key": key, "value": value, "description": description})
        await session.commit()


async def _reload_rbac_cache() -> None:
    """Load RBAC access entries and record rules into in-memory cache."""
    import json
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.security.rbac import reload_access_cache
    from modules.base.controller.repositories import IrModelAccessRepository, IrRuleRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        access_repo = IrModelAccessRepository(session, ctx)
        rule_repo = IrRuleRepository(session, ctx)
        access_objs, _ = await access_repo.search(limit=10000)
        rule_objs, _ = await rule_repo.search(limit=10000)

        # Convert domain objects to dicts for the RBAC cache
        access_rows = [
            {
                "role_name": getattr(a, "role_name", ""),
                "model_name": getattr(a, "model_name", ""),
                "perm_read": getattr(a, "perm_read", False),
                "perm_write": getattr(a, "perm_write", False),
                "perm_create": getattr(a, "perm_create", False),
                "perm_unlink": getattr(a, "perm_unlink", False),
            }
            for a in access_objs
        ]
        def _to_list(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return []
            return []

        rule_rows = [
            {
                "model_name": getattr(r, "model_name", ""),
                "roles": _to_list(getattr(r, "roles", [])),
                "domain": _to_list(getattr(r, "domain_force", [])),
                "global": getattr(r, "is_global", False),
            }
            for r in rule_objs
        ]
        reload_access_cache(access_rows, rule_rows)


async def _bootstrap_modules() -> None:
    """Run each module's `bootstrap.on_install()` once per fresh tenant.

    Replaces the legacy `_seed_crm_defaults` (PR 9 / ADR-0008). Modules
    declare their bootstrap path in `manifest.MANIFEST["bootstrap"]`.
    """
    import importlib

    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    ctx = RequestContext(is_superadmin=True)
    bootstrap_paths: list[str] = []
    for mod_name in registry.loaded_modules:
        try:
            manifest_mod = importlib.import_module(f"modules.{mod_name}.manifest")
        except ModuleNotFoundError:
            continue
        path = getattr(manifest_mod, "MANIFEST", {}).get("bootstrap")
        if path:
            bootstrap_paths.append(path)

    if not bootstrap_paths:
        return

    async with AsyncSessionFactory() as session:
        for path in bootstrap_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, "on_install"):
                    await module.on_install(session, ctx)
            except Exception:
                # `module` is reserved on LogRecord; use a custom key.
                logger.exception("module.bootstrap.failed", extra={"module_path": path})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    await _create_tables()
    default_tenant_id = await _seed_default_tenant()
    await _seed_superadmin(default_tenant_id)
    await _seed_branding()
    await registry.seed_security_to_db()
    await registry.seed_views_to_db()
    await _bootstrap_modules()
    await _reload_rbac_cache()
    logger.info("Startup complete — RBAC cache loaded.")
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Composable ERP Engine",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-id, access log, Prometheus counters/histograms (docs/29).
    app.add_middleware(RequestIdMiddleware)

    # IP rate limit (PR 6). Tenant/user buckets are checked deeper in the stack
    # because JWT is decoded later (security.middleware).
    from orbiteus_core.security.rate_limit_middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # Health and metrics endpoints
    app.include_router(health_router)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

    # ---------------------------------------------------------------------------
    # Register modules (order matters for depends_on – registry sorts them)
    # ---------------------------------------------------------------------------
    registry.register("base")
    registry.register("auth")
    registry.register("crm")

    # Bootstrap: load mappings, register routes, seed security
    registry.bootstrap(app)

    # Wire the outbox dispatcher onto record.* events (PR 4 / ADR-0010).
    from orbiteus_core.outbox_dispatcher import register_dispatchers
    register_dispatchers()

    # Wire the realtime publishers (PR 7 / ADR-0006, ADR-0014).
    from orbiteus_core.realtime import register_realtime_publishers
    from orbiteus_core.realtime_router import router as realtime_router
    register_realtime_publishers()
    app.include_router(realtime_router)

    # External portal (share-link exchange). PR 12 / ADR-0007.
    from orbiteus_core.portal_router import router as portal_router
    app.include_router(portal_router)

    # OpenTelemetry instrumentation (no-op unless OTEL_EXPORTER_OTLP_ENDPOINT set).
    from orbiteus_core.observability.tracing import setup_tracing
    setup_tracing(app)

    # AI-native layer — Command Palette endpoint
    from orbiteus_core.ai.router import router as ai_router
    app.include_router(ai_router)

    logger.info("Orbiteus application ready.")
    return app


app = create_app()
