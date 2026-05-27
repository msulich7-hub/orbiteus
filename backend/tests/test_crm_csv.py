"""CSV import/export tests for CRM (SPEC-012)."""
from __future__ import annotations

import csv
import io

import pytest

from modules.crm.controller.csv_io import LEAD_EXPORT_COLUMNS, PROSPECT_EXPORT_COLUMNS
from tests.conftest import register_user, unique_email


async def _auth_headers(client, email: str | None = None) -> dict[str, str]:
    tokens = await register_user(client, email=email or unique_email("crm_csv"))
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_export_leads_csv_has_headers_and_seed_row(client):
    headers = await _auth_headers(client)

    pipeline_resp = await client.post(
        "/api/crm/pipeline",
        json={"name": "CSV Pipeline", "is_default": True},
        headers=headers,
    )
    assert pipeline_resp.status_code in (200, 201), pipeline_resp.text
    pipeline_id = pipeline_resp.json()["id"]

    stage_resp = await client.post(
        "/api/crm/stage",
        json={
            "name": "CSV Stage",
            "pipeline_id": pipeline_id,
            "sequence": 10,
            "probability": 25.0,
        },
        headers=headers,
    )
    assert stage_resp.status_code in (200, 201), stage_resp.text
    stage_id = stage_resp.json()["id"]

    org_resp = await client.post(
        "/api/crm/organization",
        json={"name": "CSV Org"},
        headers=headers,
    )
    assert org_resp.status_code in (200, 201), org_resp.text
    org_id = org_resp.json()["id"]

    person_resp = await client.post(
        "/api/crm/person",
        json={"name": "CSV Person", "kind": "lead", "organization_id": org_id},
        headers=headers,
    )
    assert person_resp.status_code in (200, 201), person_resp.text
    person_id = person_resp.json()["id"]

    lead_name = "CSV Export Deal"
    lead_resp = await client.post(
        "/api/crm/lead",
        json={
            "name": lead_name,
            "pipeline_id": pipeline_id,
            "stage_id": stage_id,
            "organization_id": org_id,
            "person_id": person_id,
            "expected_revenue": 12000,
            "probability": 25.0,
        },
        headers=headers,
    )
    assert lead_resp.status_code in (200, 201), lead_resp.text
    lead_id = lead_resp.json()["id"]

    export_resp = await client.get("/api/crm/lead/export.csv", headers=headers)
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers.get("content-type", "")

    rows = list(csv.reader(io.StringIO(export_resp.text)))
    assert rows[0] == LEAD_EXPORT_COLUMNS

    data_rows = [row for row in rows[1:] if row]
    matching = next((row for row in data_rows if row[0] == lead_id), None)
    assert matching is not None, export_resp.text
    assert matching[1] == lead_name
    assert matching[2] == "CSV Org"
    assert matching[3] == "CSV Person"
    assert matching[4] == "CSV Stage"
    assert matching[5] == "CSV Pipeline"


@pytest.mark.asyncio
async def test_import_prospects_csv_counts_duplicates(client):
    headers = await _auth_headers(client)

    existing = await client.post(
        "/api/crm/prospect",
        json={"name": "Duplicate Prospect", "source": "web"},
        headers=headers,
    )
    assert existing.status_code in (200, 201), existing.text

    csv_text = (
        "name,organization_name,person_name,email,source,temperature\n"
        "Fresh Prospect A,Acme Inc,Jane Doe,jane@example.com,web,warm\n"
        "Fresh Prospect B,Beta LLC,John Smith,john@example.com,referral,cold\n"
        "Duplicate Prospect,Gamma Co,Skip Me,skip@example.com,web,hot\n"
    )

    import_resp = await client.post(
        "/api/crm/prospect/import",
        headers=headers,
        files={"file": ("prospects.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert import_resp.status_code == 200, import_resp.text
    body = import_resp.json()
    assert body["imported"] == 2
    assert body["skipped"] == 1
    assert any(err.get("message") == "duplicate name" for err in body["errors"])

    listing = await client.get(
        "/api/crm/prospect",
        headers=headers,
        params={"limit": 200},
    )
    assert listing.status_code == 200
    names = {item["name"] for item in listing.json()["items"]}
    assert "Fresh Prospect A" in names
    assert "Fresh Prospect B" in names
    assert "Duplicate Prospect" in names


@pytest.mark.asyncio
async def test_export_prospects_csv_has_headers(client):
    headers = await _auth_headers(client)

    create_resp = await client.post(
        "/api/crm/prospect",
        json={"name": "Export Me", "source": "csv-test", "temperature": "warm"},
        headers=headers,
    )
    assert create_resp.status_code in (200, 201), create_resp.text

    export_resp = await client.get("/api/crm/prospect/export.csv", headers=headers)
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers.get("content-type", "")

    rows = list(csv.reader(io.StringIO(export_resp.text)))
    assert rows[0] == PROSPECT_EXPORT_COLUMNS
    assert any(row and row[1] == "Export Me" for row in rows[1:])
