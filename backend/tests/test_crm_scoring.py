"""Lead scoring tests (SPEC-015)."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from modules.crm.controller.scoring import calculate_score, recalculate_all_scores
from tests.conftest import login_user, register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_scoring"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_calculate_score_hot_referral_sql_assigned():
    obj = SimpleNamespace(
        temperature="hot",
        utm_source="referral",
        lifecycle_stage="sql",
        assigned_user_id=uuid.uuid4(),
    )
    assert calculate_score(obj) == 95


def test_calculate_score_cold_cold_call_low():
    obj = SimpleNamespace(
        temperature="cold",
        utm_source="cold_call",
        lifecycle_stage="lead",
        assigned_user_id=None,
    )
    assert calculate_score(obj) == 10


def test_calculate_score_rotting_malus():
    obj = SimpleNamespace(
        temperature="hot",
        utm_source="referral",
        lifecycle_stage="sql",
        assigned_user_id=uuid.uuid4(),
    )
    assert calculate_score(obj, days_in_stage=20) == 80


@pytest.mark.asyncio
async def test_recalculate_scores_endpoint_requires_superadmin(client):
    headers = await _auth_headers(client)
    resp = await client.post("/api/crm/leads/recalculate-scores", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_recalculate_scores_endpoint_superadmin(client):
    email = unique_email("crm_scoring_admin")
    headers = await _auth_headers(client, email=email)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={
            "name": "Scoring deal",
            "utm_source": "organic",
            "lifecycle_stage": "lead",
        },
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text

    me_resp = await client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    profile = me_resp.json()

    from modules.base.controller.repositories import UserRepository
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        super_ctx = RequestContext(is_superadmin=True)
        user_repo = UserRepository(session, super_ctx)
        await user_repo.update(uuid.UUID(profile["id"]), {"is_superadmin": True})
        await session.commit()

    admin_token = await login_user(client, email)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    recalc_resp = await client.post(
        "/api/crm/leads/recalculate-scores",
        headers=admin_headers,
    )
    assert recalc_resp.status_code == 200
    assert recalc_resp.json()["updated"] >= 1

    lead_get = await client.get(
        f"/api/crm/lead/{lead_resp.json()['id']}",
        headers=admin_headers,
    )
    assert lead_get.status_code == 200
    assert lead_get.json()["score"] == 15

    async with AsyncSessionFactory() as session:
        ctx = RequestContext(
            is_superadmin=True,
            tenant_id=uuid.UUID(profile["tenant_id"]),
            user_id=uuid.UUID(profile["id"]),
        )
        updated = await recalculate_all_scores(session, ctx)
        await session.commit()

    assert updated >= 1
