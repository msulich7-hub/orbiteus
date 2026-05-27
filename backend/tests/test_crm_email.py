"""CRM email log stub tests (SPEC-014)."""
from __future__ import annotations

import pytest

from tests.conftest import register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_email"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_log_lead_email_post_and_get(client):
    headers = await _auth_headers(client)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Email Test Deal"},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    post_resp = await client.post(
        f"/api/crm/lead/{lead_id}/email",
        json={
            "direction": "outbound",
            "from_address": "seller@orbiteus.com",
            "to_address": "buyer@acme.com",
            "subject": "Follow-up quote",
            "body": "Please review the attached offer.",
        },
        headers=headers,
    )
    assert post_resp.status_code == 200, post_resp.text
    body = post_resp.json()
    assert body.get("created") is True
    assert body.get("id")

    get_resp = await client.get(
        f"/api/crm/lead/{lead_id}/emails",
        headers=headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    assert data["count"] >= 1
    emails = data["emails"]
    assert len(emails) >= 1
    match = next(e for e in emails if e["subject"] == "Follow-up quote")
    assert match["direction"] == "outbound"
    assert match["from_address"] == "seller@orbiteus.com"
    assert match["to_address"] == "buyer@acme.com"


@pytest.mark.asyncio
async def test_log_lead_email_rejects_bad_direction(client):
    headers = await _auth_headers(client)

    lead_resp = await client.post(
        "/api/crm/lead",
        json={"name": "Bad Direction Deal"},
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    post_resp = await client.post(
        f"/api/crm/lead/{lead_id}/email",
        json={
            "direction": "sideways",
            "from_address": "a@orbiteus.com",
            "to_address": "b@acme.com",
            "subject": "Nope",
            "body": "Invalid direction",
        },
        headers=headers,
    )
    assert post_resp.status_code in (400, 422), post_resp.text
