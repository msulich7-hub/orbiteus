"""CRM automation engine tests (SPEC-006 v1)."""
from __future__ import annotations

import pytest

from tests.conftest import register_user, unique_email


def _items(data) -> list:
    if isinstance(data, dict):
        return data.get("items", data.get("data", []))
    return data


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_auto"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_pipeline_and_stages(client, headers: dict[str, str]) -> tuple[str, str, str]:
    pipeline_resp = await client.post(
        "/api/crm/pipeline",
        json={"name": "Automation Pipeline", "is_default": True},
        headers=headers,
    )
    assert pipeline_resp.status_code in (200, 201), pipeline_resp.text
    pipeline_id = pipeline_resp.json()["id"]

    new_stage_resp = await client.post(
        "/api/crm/stage",
        json={"name": "New", "pipeline_id": pipeline_id, "sequence": 10, "probability": 5.0},
        headers=headers,
    )
    assert new_stage_resp.status_code in (200, 201), new_stage_resp.text
    new_stage_id = new_stage_resp.json()["id"]

    proposal_stage_resp = await client.post(
        "/api/crm/stage",
        json={"name": "Proposal", "pipeline_id": pipeline_id, "sequence": 30, "probability": 55.0},
        headers=headers,
    )
    assert proposal_stage_resp.status_code in (200, 201), proposal_stage_resp.text
    proposal_stage_id = proposal_stage_resp.json()["id"]

    return pipeline_id, new_stage_id, proposal_stage_id


@pytest.mark.asyncio
async def test_stage_change_triggers_create_activity_rule(client):
    """Moving a lead to Proposal runs create_activity automation."""
    headers = await _auth_headers(client)
    _, new_stage_id, proposal_stage_id = await _create_pipeline_and_stages(client, headers)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Automation Test Deal", "stage_id": new_stage_id},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    rule_resp = await client.post(
        "/api/crm/automation_rule",
        json={
            "name": "Follow up when moved to Proposal",
            "trigger_event": "crm.lead.stage_changed",
            "condition_json": {"to_stage_name": "Proposal"},
            "action_type": "create_activity",
            "action_json": {
                "subject": "Follow up on proposal",
                "activity_type": "task",
            },
            "active": True,
        },
        headers=headers,
    )
    assert rule_resp.status_code in (200, 201), rule_resp.text

    move_resp = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": proposal_stage_id},
        headers=headers,
    )
    assert move_resp.status_code == 200, move_resp.text

    activities_resp = await client.get(
        "/api/crm/activity",
        params={"limit": 500},
        headers=headers,
    )
    assert activities_resp.status_code == 200, activities_resp.text
    activities = [
        a for a in _items(activities_resp.json())
        if a.get("res_id") == lead_id
    ]
    assert len(activities) >= 1
    assert any(a["subject"] == "Follow up on proposal" for a in activities)
    assert any(a["res_id"] == lead_id for a in activities)


@pytest.mark.asyncio
async def test_stage_change_skips_rule_when_condition_not_met(client):
    """Automation does not fire when target stage does not match condition."""
    headers = await _auth_headers(client)
    pipeline_id, new_stage_id, proposal_stage_id = await _create_pipeline_and_stages(client, headers)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "No Automation Deal", "stage_id": new_stage_id},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    rule_resp = await client.post(
        "/api/crm/automation_rule",
        json={
            "name": "Proposal only",
            "trigger_event": "crm.lead.stage_changed",
            "condition_json": {"to_stage_name": "Proposal"},
            "action_type": "create_activity",
            "action_json": {"subject": "Should not appear", "activity_type": "task"},
            "active": True,
        },
        headers=headers,
    )
    assert rule_resp.status_code in (200, 201), rule_resp.text

    qualified_resp = await client.post(
        "/api/crm/stage",
        json={"name": "Qualified", "pipeline_id": pipeline_id, "sequence": 20},
        headers=headers,
    )
    assert qualified_resp.status_code in (200, 201), qualified_resp.text
    qualified_stage_id = qualified_resp.json()["id"]

    move_resp = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": qualified_stage_id},
        headers=headers,
    )
    assert move_resp.status_code == 200, move_resp.text

    activities_resp = await client.get(
        "/api/crm/activity",
        params={"limit": 500},
        headers=headers,
    )
    assert activities_resp.status_code == 200, activities_resp.text
    activities = [
        a for a in _items(activities_resp.json())
        if a.get("res_id") == lead_id
    ]
    assert not any(a["subject"] == "Should not appear" for a in activities)

    move_proposal = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": proposal_stage_id},
        headers=headers,
    )
    assert move_proposal.status_code == 200, move_proposal.text

    activities_after = await client.get(
        "/api/crm/activity",
        params={"limit": 500},
        headers=headers,
    )
    assert activities_after.status_code == 200
    activities = [
        a for a in _items(activities_after.json())
        if a.get("res_id") == lead_id
    ]
    assert any(a["subject"] == "Should not appear" for a in activities)


@pytest.mark.asyncio
async def test_inactive_rule_does_not_run(client):
    """Inactive automation rules are ignored."""
    headers = await _auth_headers(client)
    _, new_stage_id, proposal_stage_id = await _create_pipeline_and_stages(client, headers)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Inactive Rule Deal", "stage_id": new_stage_id},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    rule_resp = await client.post(
        "/api/crm/automation_rule",
        json={
            "name": "Disabled rule",
            "trigger_event": "crm.lead.stage_changed",
            "condition_json": {"to_stage_name": "Proposal"},
            "action_type": "create_activity",
            "action_json": {"subject": "Inactive rule activity", "activity_type": "task"},
            "active": False,
        },
        headers=headers,
    )
    assert rule_resp.status_code in (200, 201), rule_resp.text

    move_resp = await client.post(
        f"/api/crm/lead/{lead_id}/move",
        params={"stage_id": proposal_stage_id},
        headers=headers,
    )
    assert move_resp.status_code == 200, move_resp.text

    activities_resp = await client.get(
        "/api/crm/activity",
        params={"res_model": "crm.lead", "res_id": lead_id},
        headers=headers,
    )
    assert activities_resp.status_code == 200
    activities = _items(activities_resp.json())
    assert not any(a["subject"] == "Inactive rule activity" for a in activities)
