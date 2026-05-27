"""CRM stage exit blueprint — required_fields_json on leave (SPEC)."""
from __future__ import annotations

import pytest

from modules.crm.controller.services import missing_required_exit_fields
from modules.crm.model.domain import Lead, Stage
from tests.conftest import register_user, unique_email


def test_missing_required_exit_fields_empty_date():
    lead = Lead(expected_close_date=None)
    stage = Stage(required_fields_json=["expected_close_date"])
    assert missing_required_exit_fields(lead, stage) == ["expected_close_date"]


def test_missing_required_exit_fields_satisfied():
    from datetime import date

    lead = Lead(expected_close_date=date(2026, 6, 1))
    stage = Stage(required_fields_json=["expected_close_date"])
    assert missing_required_exit_fields(lead, stage) == []


def test_bootstrap_proposal_stage_seeds_exit_rule():
    from modules.crm.bootstrap import _DEFAULT_STAGES

    proposal = next(s for s in _DEFAULT_STAGES if s["name"] == "Proposal")
    assert proposal["required_fields_json"] == ["expected_close_date"]


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_blueprint"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_pipeline_with_exit_rule(client, headers: dict[str, str]) -> tuple[str, str, str]:
    pipeline_resp = await client.post(
        "/api/crm/pipeline",
        json={"name": "Blueprint Pipeline", "is_default": True},
        headers=headers,
    )
    assert pipeline_resp.status_code in (200, 201), pipeline_resp.text
    pipeline_id = pipeline_resp.json()["id"]

    source_resp = await client.post(
        "/api/crm/stage",
        json={
            "name": "Needs Close Date",
            "pipeline_id": pipeline_id,
            "sequence": 10,
            "probability": 20.0,
            "required_fields_json": ["expected_close_date"],
        },
        headers=headers,
    )
    assert source_resp.status_code in (200, 201), source_resp.text
    source_stage_id = source_resp.json()["id"]

    target_resp = await client.post(
        "/api/crm/stage",
        json={
            "name": "Next",
            "pipeline_id": pipeline_id,
            "sequence": 20,
            "probability": 40.0,
        },
        headers=headers,
    )
    assert target_resp.status_code in (200, 201), target_resp.text
    target_stage_id = target_resp.json()["id"]

    return pipeline_id, source_stage_id, target_stage_id


@pytest.mark.asyncio
async def test_move_blocked_when_exit_fields_missing(client):
    """Leaving a stage with blueprint fails with structured 400."""
    headers = await _auth_headers(client)
    _, source_stage_id, target_stage_id = await _create_pipeline_with_exit_rule(client, headers)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Blueprint Deal", "stage_id": source_stage_id},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    move_resp = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": target_stage_id},
        headers=headers,
    )
    assert move_resp.status_code == 400, move_resp.text
    detail = move_resp.json()["detail"]
    assert detail["code"] == "missing_required_fields"
    assert "expected_close_date" in detail["missing_fields"]


@pytest.mark.asyncio
async def test_move_allowed_when_exit_fields_present(client):
    """Move succeeds once required exit fields are filled."""
    headers = await _auth_headers(client)
    _, source_stage_id, target_stage_id = await _create_pipeline_with_exit_rule(client, headers)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Ready Deal", "stage_id": source_stage_id},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    patch_resp = await client.put(
        f"/api/crm/lead/{lead_id}",
        json={"expected_close_date": "2026-06-15"},
        headers=headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text

    move_resp = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": target_stage_id},
        headers=headers,
    )
    assert move_resp.status_code == 200, move_resp.text

    lead_get = await client.get(f"/api/crm/lead/{lead_id}", headers=headers)
    assert lead_get.status_code == 200
    assert lead_get.json()["stage_id"] == target_stage_id

