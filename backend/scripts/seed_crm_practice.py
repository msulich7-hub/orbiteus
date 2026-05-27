"""Seed realistic CRM practice data for hands-on training (SPEC-001..005).

Creates Polish B2B demo: organizations, contacts, prospects, deals,
activities — including one rotting deal and overdue tasks.

Usage (stack running, migrations applied):
  cd backend
  python -m scripts.seed_crm_practice

Inside Docker:
  docker compose exec backend python -m scripts.seed_crm_practice

Idempotent: skips if demo org "Acme Polska Sp. z o.o." already exists.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import api  # noqa: F401 — bootstrap registry + mappings

from modules.base.controller.repositories import TenantRepository, UserRepository
from modules.crm.controller.scoring import calculate_score
from modules.crm.bootstrap import on_install as crm_bootstrap
from modules.crm.controller.repositories import (
    ActivityRepository,
    LeadRepository,
    OrganizationRepository,
    PersonRepository,
    PipelineRepository,
    ProspectRepository,
    StageRepository,
)
from orbiteus_core.context import RequestContext
from orbiteus_core.db import AsyncSessionFactory

DEMO_ORG_NAME = "Acme Polska Sp. z o.o."
MARKER_KEY = "crm.practice_seeded"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _persist_score(repo, obj, *, days_in_stage: int | None = None) -> None:
    now = _utcnow()
    score = calculate_score(obj, days_in_stage=days_in_stage)
    await repo.update(obj.id, {"score": score, "score_updated_at": now})
    obj.score = score
    obj.score_updated_at = now


async def _refresh_practice_scores(session, ctx: RequestContext) -> None:
    """Recalculate demo lead/prospect scores after seed reruns."""
    from modules.crm.controller.repositories import LeadRepository, ProspectRepository, StageRepository
    from modules.crm.controller.services import evaluate_lead_rotting

    lead_repo = LeadRepository(session, ctx)
    prospect_repo = ProspectRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)
    now = _utcnow()

    stages, _ = await stage_repo.search(limit=50)
    stage_by_id = {s.id: s for s in stages}

    leads, _ = await lead_repo.search(limit=50)
    for lead in leads:
        stage = stage_by_id.get(lead.stage_id) if lead.stage_id else None
        _, days_in_stage, _ = evaluate_lead_rotting(lead, stage, now)
        await _persist_score(lead_repo, lead, days_in_stage=days_in_stage)

    prospects, _ = await prospect_repo.search(limit=50)
    for prospect in prospects:
        days_in_stage = None
        if prospect.create_date is not None:
            days_in_stage = (now - prospect.create_date).days
        await _persist_score(prospect_repo, prospect, days_in_stage=days_in_stage)


async def _refresh_practice_activities(
    session,
    ctx: RequestContext,
    user_id: uuid.UUID | None,
) -> None:
    """Re-open demo activities so E2E / today queue stays populated after reruns."""
    if not user_id:
        return

    activity_repo = ActivityRepository(session, ctx)
    lead_repo = LeadRepository(session, ctx)
    now = _utcnow()

    leads, _ = await lead_repo.search(limit=20)
    lead1 = next((l for l in leads if l.name == "Acme — modernizacja linii A"), None)

    templates: list[tuple[str, str, datetime, uuid.UUID | None]] = [
        (
            "Telefon — doprecyzowanie scope Acme",
            "call",
            now.replace(hour=10, minute=0, second=0, microsecond=0),
            lead1.id if lead1 else None,
        ),
        (
            "Spotkanie online z Beta",
            "meeting",
            now.replace(hour=14, minute=30, second=0, microsecond=0),
            lead1.id if lead1 else None,
        ),
        (
            "Wyślij ofertę PDF — Gamma",
            "task",
            now - timedelta(days=1),
            lead1.id if lead1 else None,
        ),
    ]

    for subject, activity_type, due_date, res_id in templates:
        existing, _ = await activity_repo.search(domain=[("subject", "=", subject)], limit=1)
        payload = {
            "done": False,
            "done_at": None,
            "due_date": due_date,
            "assigned_user_id": user_id,
            "activity_type": activity_type,
        }
        if existing:
            await activity_repo.update(existing[0].id, payload)
        elif res_id:
            await activity_repo.create({
                **payload,
                "subject": subject,
                "res_model": "crm.lead",
                "res_id": res_id,
            })


async def _resolve_tenant_and_user(session, root_ctx: RequestContext) -> tuple[uuid.UUID, uuid.UUID | None]:
    tenant_repo = TenantRepository(session, root_ctx)
    tenants, _ = await tenant_repo.search(limit=10)
    if not tenants:
        raise RuntimeError("No tenant found — start the stack first (docker compose up).")
    tenant = next((t for t in tenants if t.slug == "orbiteus"), tenants[0])

    user_repo = UserRepository(session, root_ctx)
    users, _ = await user_repo.search(limit=50)
    admin = next(
        (u for u in users if getattr(u, "email", "") == os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")),
        users[0] if users else None,
    )
    return tenant.id, admin.id if admin else None


async def _run() -> None:
    async with AsyncSessionFactory() as session:
        root_ctx = RequestContext(is_superadmin=True)
        tenant_id, user_id = await _resolve_tenant_and_user(session, root_ctx)
        ctx = RequestContext(is_superadmin=True, tenant_id=tenant_id, user_id=user_id)

        await crm_bootstrap(session, root_ctx)

        org_repo = OrganizationRepository(session, ctx)
        existing, _ = await org_repo.search(domain=[("name", "=", DEMO_ORG_NAME)], limit=1)
        if existing:
            await _refresh_practice_activities(session, ctx, user_id)
            await _refresh_practice_scores(session, ctx)
            print(f"SKIP: practice data already present ({DEMO_ORG_NAME}).")
            print("  Activities refreshed for E2E (open due today / overdue).")
            print("  Lead/prospect scores recalculated.")
            print("  Reset: docker compose down -v  &&  docker compose up --build")
            await session.commit()
            return

        pipeline_repo = PipelineRepository(session, ctx)
        stage_repo = StageRepository(session, ctx)
        person_repo = PersonRepository(session, ctx)
        prospect_repo = ProspectRepository(session, ctx)
        lead_repo = LeadRepository(session, ctx)
        activity_repo = ActivityRepository(session, ctx)

        pipelines, _ = await pipeline_repo.search(limit=10)
        pipeline = next((p for p in pipelines if p.is_default), pipelines[0])
        stages, _ = await stage_repo.search(limit=50)
        pipeline_stages = sorted(
            [s for s in stages if s.pipeline_id == pipeline.id],
            key=lambda s: s.sequence,
        )
        stage_by_name = {s.name: s for s in pipeline_stages}
        now = _utcnow()

        # --- Organizations ---
        org_acme = await org_repo.create({
            "name": DEMO_ORG_NAME,
            "vat": "5250000001",
            "website": "https://acme-polska.example.com",
            "city": "Warszawa",
            "industry": "Produkcja",
            "assigned_user_id": user_id,
            "tags": ["demo", "tier-a"],
        })
        org_beta = await org_repo.create({
            "name": "Beta Logistics Sp. z o.o.",
            "vat": "5250000002",
            "city": "Kraków",
            "industry": "Logistyka",
            "assigned_user_id": user_id,
            "tags": ["demo"],
        })
        org_gamma = await org_repo.create({
            "name": "Gamma Software S.A.",
            "vat": "5250000003",
            "city": "Wrocław",
            "industry": "IT",
            "assigned_user_id": user_id,
        })

        # --- Contacts ---
        person_anna = await person_repo.create({
            "name": "Anna Kowalska",
            "email": "anna.kowalska@acme-polska.example.com",
            "phone": "+48 500 100 200",
            "kind": "contact",
            "organization_id": org_acme.id,
            "assigned_user_id": user_id,
            "source": "referral",
        })
        person_piotr = await person_repo.create({
            "name": "Piotr Nowak",
            "email": "piotr.nowak@beta-logistics.example.com",
            "mobile": "+48 600 300 400",
            "kind": "contact",
            "organization_id": org_beta.id,
            "assigned_user_id": user_id,
            "source": "website",
        })
        person_maria = await person_repo.create({
            "name": "Maria Wiśniewska",
            "email": "maria@gamma-software.example.com",
            "kind": "contact",
            "organization_id": org_gamma.id,
            "assigned_user_id": user_id,
            "source": "event",
        })

        # --- Prospects (inbox) ---
        prospect1 = await prospect_repo.create({
            "name": "Zapytanie — linia pakująca 2026",
            "organization_id": org_acme.id,
            "person_id": person_anna.id,
            "assigned_user_id": user_id,
            "source": "website",
            "temperature": "warm",
            "notes": "Formularz www, budżet ~120k PLN",
        })
        await _persist_score(prospect_repo, prospect1)

        prospect2 = await prospect_repo.create({
            "name": "Cold outreach — TMS dla floty",
            "organization_id": org_beta.id,
            "person_id": person_piotr.id,
            "assigned_user_id": user_id,
            "source": "cold_call",
            "temperature": "cold",
            "utm_source": "cold_call",
        })
        await _persist_score(prospect_repo, prospect2)

        prospect3 = await prospect_repo.create({
            "name": "Demo po targach IT",
            "organization_id": org_gamma.id,
            "person_id": person_maria.id,
            "assigned_user_id": user_id,
            "source": "event",
            "temperature": "hot",
            "notes": "Chcą wdrożenie Q3",
            "utm_source": "referral",
            "lifecycle_stage": "sql",
        })
        await _persist_score(prospect_repo, prospect3)

        # --- Deals ---
        stage_new = stage_by_name["New"]
        stage_qual = stage_by_name["Qualified"]
        stage_prop = stage_by_name["Proposal"]
        stage_nego = stage_by_name["Negotiation"]

        lead1 = await lead_repo.create({
            "name": "Acme — modernizacja linii A",
            "organization_id": org_acme.id,
            "person_id": person_anna.id,
            "pipeline_id": pipeline.id,
            "stage_id": stage_prop.id,
            "assigned_user_id": user_id,
            "expected_revenue": 185000.0,
            "probability": stage_prop.probability,
            "expected_close_date": (now + timedelta(days=21)).date(),
            "stage_entered_at": now - timedelta(days=3),
            "last_activity_at": now - timedelta(days=1),
            "tags": ["strategic"],
            "utm_source": "referral",
            "lifecycle_stage": "sql",
        })
        await _persist_score(lead_repo, lead1, days_in_stage=3)

        # Rotting deal — stuck in Qualified > rotting_days (14)
        lead2 = await lead_repo.create({
            "name": "Beta — integracja WMS",
            "organization_id": org_beta.id,
            "person_id": person_piotr.id,
            "pipeline_id": pipeline.id,
            "stage_id": stage_qual.id,
            "assigned_user_id": user_id,
            "expected_revenue": 95000.0,
            "probability": stage_qual.probability,
            "stage_entered_at": now - timedelta(days=20),
            "last_activity_at": now - timedelta(days=18),
            "tags": ["rotting-demo"],
        })
        await _persist_score(lead_repo, lead2, days_in_stage=20)

        lead3 = await lead_repo.create({
            "name": "Gamma — licencje + wdrożenie",
            "organization_id": org_gamma.id,
            "person_id": person_maria.id,
            "pipeline_id": pipeline.id,
            "stage_id": stage_nego.id,
            "assigned_user_id": user_id,
            "expected_revenue": 240000.0,
            "probability": stage_nego.probability,
            "stage_entered_at": now - timedelta(days=5),
            "last_activity_at": now - timedelta(hours=6),
        })
        await _persist_score(lead_repo, lead3, days_in_stage=5)

        lead4 = await lead_repo.create({
            "name": "Acme — serwis roczny",
            "organization_id": org_acme.id,
            "person_id": person_anna.id,
            "pipeline_id": pipeline.id,
            "stage_id": stage_new.id,
            "assigned_user_id": user_id,
            "expected_revenue": 45000.0,
            "probability": stage_new.probability,
            "stage_entered_at": now - timedelta(days=1),
        })
        await _persist_score(lead_repo, lead4, days_in_stage=1)

        # --- Activities ---
        await activity_repo.create({
            "subject": "Telefon — doprecyzowanie scope Acme",
            "activity_type": "call",
            "due_date": now.replace(hour=10, minute=0, second=0, microsecond=0),
            "assigned_user_id": user_id,
            "res_model": "crm.lead",
            "res_id": lead1.id,
        })
        await activity_repo.create({
            "subject": "Spotkanie online z Beta",
            "activity_type": "meeting",
            "due_date": now.replace(hour=14, minute=30, second=0, microsecond=0),
            "assigned_user_id": user_id,
            "res_model": "crm.lead",
            "res_id": lead1.id,
        })
        await activity_repo.create({
            "subject": "Wyślij ofertę PDF — Gamma",
            "activity_type": "task",
            "due_date": now - timedelta(days=1),
            "assigned_user_id": user_id,
            "res_model": "crm.lead",
            "res_id": lead1.id,
            "notes": "Przeterminowane — ćwiczenie kolejki today",
        })
        await activity_repo.create({
            "subject": "Follow-up po konwersji prospectu",
            "activity_type": "task",
            "due_date": now + timedelta(days=2),
            "assigned_user_id": user_id,
            "res_model": "crm.prospect",
            "res_id": None,
        })

        await session.commit()

    print("")
    print("=== CRM Practice data seeded ===")
    print("")
    print("Admin UI:  http://localhost:3000")
    print("API docs:  http://localhost:8000/api/docs")
    print("Login:     admin@example.com / admin1234")
    print("")
    print("Demo includes:")
    print("  - 3 organizations, 3 contacts")
    print("  - 3 prospects in inbox (convert one via API or UI)")
    print("  - 4 deals (1 rotting in Qualified)")
    print("  - 4 activities (1 overdue for /activities/today)")
    print("")
    print("Quick API checks (after login token):")
    print("  GET  /api/crm/leads/kanban")
    print("  GET  /api/crm/leads/rotting")
    print("  GET  /api/crm/activities/today")
    print("  GET  /api/crm/stats")
    print("  POST /api/crm/prospect/{id}/convert")
    print("")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
