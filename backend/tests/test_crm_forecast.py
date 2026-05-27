"""Forecast endpoint tests (SPEC-010)."""
from __future__ import annotations

from datetime import date

import pytest

from tests.conftest import register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_forecast"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_pipeline_with_proposal_stage(
    client,
    headers: dict[str, str],
    *,
    probability: float = 50.0,
) -> tuple[str, str]:
    pipeline_resp = await client.post(
        "/api/crm/pipeline",
        json={"name": "Forecast Pipeline", "is_default": True},
        headers=headers,
    )
    assert pipeline_resp.status_code in (200, 201), pipeline_resp.text
    pipeline_id = pipeline_resp.json()["id"]

    proposal_stage_resp = await client.post(
        "/api/crm/stage",
        json={
            "name": "Proposal",
            "pipeline_id": pipeline_id,
            "sequence": 30,
            "probability": probability,
        },
        headers=headers,
    )
    assert proposal_stage_resp.status_code in (200, 201), proposal_stage_resp.text
    proposal_stage_id = proposal_stage_resp.json()["id"]

    return pipeline_id, proposal_stage_id


@pytest.mark.asyncio
async def test_forecast_weighted_revenue_happy_path(client):
    """Proposal 50% × 100k expected revenue = 50k weighted."""
    headers = await _auth_headers(client)
    pipeline_id, proposal_stage_id = await _create_pipeline_with_proposal_stage(
        client,
        headers,
        probability=50.0,
    )

    lead_resp = await client.post(
        "/api/crm/lead",
        json={
            "name": "Forecast Test Deal",
            "pipeline_id": pipeline_id,
            "stage_id": proposal_stage_id,
            "expected_revenue": 100_000,
            "expected_close_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text

    forecast_resp = await client.get(
        "/api/crm/leads/forecast",
        params={"pipeline_id": pipeline_id, "months_ahead": 6},
        headers=headers,
    )
    assert forecast_resp.status_code == 200, forecast_resp.text
    data = forecast_resp.json()

    assert data["pipeline_id"] == pipeline_id
    assert data["currency"] == "PLN"
    assert data["total_weighted"] == 50_000.0
    assert data["total_raw"] == 100_000.0

    month_with_deal = next((m for m in data["months"] if m["deal_count"] > 0), None)
    assert month_with_deal is not None
    assert month_with_deal["weighted_revenue"] == 50_000.0
    assert month_with_deal["raw_revenue"] == 100_000.0
    assert month_with_deal["deal_count"] == 1
    assert len(month_with_deal["by_stage"]) == 1
    assert month_with_deal["by_stage"][0]["stage_name"] == "Proposal"
    assert month_with_deal["by_stage"][0]["weighted_revenue"] == 50_000.0


@pytest.mark.asyncio
async def test_forecast_excludes_won_and_lost_stages(client):
    """Closed stages are omitted from weighted totals."""
    headers = await _auth_headers(client)
    pipeline_id, proposal_stage_id = await _create_pipeline_with_proposal_stage(
        client,
        headers,
        probability=50.0,
    )

    won_stage_resp = await client.post(
        "/api/crm/stage",
        json={
            "name": "Won",
            "pipeline_id": pipeline_id,
            "sequence": 90,
            "probability": 100.0,
            "is_won": True,
        },
        headers=headers,
    )
    assert won_stage_resp.status_code in (200, 201), won_stage_resp.text
    won_stage_id = won_stage_resp.json()["id"]

    open_lead_resp = await client.post(
        "/api/crm/lead",
        json={
            "name": "Open Deal",
            "pipeline_id": pipeline_id,
            "stage_id": proposal_stage_id,
            "expected_revenue": 100_000,
            "expected_close_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert open_lead_resp.status_code in (200, 201), open_lead_resp.text

    won_lead_resp = await client.post(
        "/api/crm/lead",
        json={
            "name": "Won Deal",
            "pipeline_id": pipeline_id,
            "stage_id": won_stage_id,
            "expected_revenue": 200_000,
            "expected_close_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert won_lead_resp.status_code in (200, 201), won_lead_resp.text

    forecast_resp = await client.get(
        "/api/crm/leads/forecast",
        params={"pipeline_id": pipeline_id},
        headers=headers,
    )
    assert forecast_resp.status_code == 200, forecast_resp.text
    data = forecast_resp.json()

    assert data["total_weighted"] == 50_000.0
    assert data["total_raw"] == 100_000.0


@pytest.mark.asyncio
async def test_forecast_requires_auth(client):
    resp = await client.get("/api/crm/leads/forecast")
    assert resp.status_code == 401
