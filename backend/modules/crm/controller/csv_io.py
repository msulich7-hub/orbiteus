"""CSV import/export for CRM leads and prospects (SPEC-012)."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

LEAD_EXPORT_COLUMNS = [
    "id",
    "name",
    "organization_name",
    "person_name",
    "stage_name",
    "pipeline_name",
    "expected_revenue",
    "probability",
    "expected_close_date",
    "assigned_user_email",
    "created_at",
    "days_in_stage",
    "is_rotting",
]

PROSPECT_EXPORT_COLUMNS = [
    "id",
    "name",
    "organization_name",
    "person_name",
    "source",
    "temperature",
    "lifecycle_stage",
    "utm_source",
    "utm_campaign",
    "is_converted",
    "created_at",
]

PROSPECT_IMPORT_OPTIONAL = [
    "organization_name",
    "person_name",
    "email",
    "source",
    "temperature",
    "notes",
    "utm_source",
    "utm_campaign",
]


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _resolve_lead_export_context(
    session: AsyncSession,
    ctx: RequestContext,
    leads,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    """Batch-resolve FK display names (expand-style) for lead CSV rows."""
    from modules.base.controller.repositories import UserRepository
    from modules.crm.controller.repositories import (
        OrganizationRepository,
        PersonRepository,
        PipelineRepository,
        StageRepository,
    )
    from modules.crm.controller.services import batch_resolve_lead_display_names

    person_names, org_names, _user_names = await batch_resolve_lead_display_names(
        session, ctx, leads
    )

    stage_ids = {lead.stage_id for lead in leads if lead.stage_id}
    pipeline_ids = {lead.pipeline_id for lead in leads if lead.pipeline_id}
    user_ids = {lead.assigned_user_id for lead in leads if lead.assigned_user_id}

    stage_names: dict[uuid.UUID, str] = {}
    stage_by_id: dict[uuid.UUID, object] = {}
    if stage_ids:
        repo = StageRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(stage_ids))],
            limit=max(len(stage_ids), 1),
        )
        stage_names = {row.id: row.name for row in rows}
        stage_by_id = {row.id: row for row in rows}

    pipeline_names: dict[uuid.UUID, str] = {}
    if pipeline_ids:
        repo = PipelineRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(pipeline_ids))],
            limit=max(len(pipeline_ids), 1),
        )
        pipeline_names = {row.id: row.name for row in rows}

    user_emails: dict[uuid.UUID, str] = {}
    if user_ids:
        repo = UserRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(user_ids))],
            limit=max(len(user_ids), 1),
        )
        user_emails = {row.id: row.email for row in rows}

    return person_names, org_names, stage_names, pipeline_names, user_emails, stage_by_id


async def _resolve_prospect_export_context(
    session: AsyncSession,
    ctx: RequestContext,
    prospects,
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    from modules.crm.controller.repositories import OrganizationRepository, PersonRepository

    person_ids = {row.person_id for row in prospects if row.person_id}
    org_ids = {row.organization_id for row in prospects if row.organization_id}

    person_names: dict[uuid.UUID, str] = {}
    org_names: dict[uuid.UUID, str] = {}

    if person_ids:
        repo = PersonRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(person_ids))],
            limit=max(len(person_ids), 1),
        )
        person_names = {row.id: row.name for row in rows}

    if org_ids:
        repo = OrganizationRepository(session, ctx)
        rows, _ = await repo.search(
            domain=[("id", "in", list(org_ids))],
            limit=max(len(org_ids), 1),
        )
        org_names = {row.id: row.name for row in rows}

    return person_names, org_names


async def export_leads_csv(session: AsyncSession, ctx: RequestContext) -> str:
    """Export tenant leads as CSV text."""
    from modules.crm.controller.repositories import LeadRepository
    from modules.crm.controller.services import evaluate_lead_rotting

    lead_repo = LeadRepository(session, ctx)
    leads, _ = await lead_repo.search(limit=5000, order_by="create_date", order_dir="desc")

    (
        person_names,
        org_names,
        stage_names,
        pipeline_names,
        user_emails,
        stage_by_id,
    ) = await _resolve_lead_export_context(session, ctx, leads)

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(LEAD_EXPORT_COLUMNS)

    now = datetime.now(timezone.utc)
    for lead in leads:
        stage = stage_by_id.get(lead.stage_id) if lead.stage_id else None
        is_rotting, days_in_stage, _reason = evaluate_lead_rotting(lead, stage, now)
        writer.writerow([
            _csv_cell(lead.id),
            _csv_cell(lead.name),
            _csv_cell(org_names.get(lead.organization_id) if lead.organization_id else ""),
            _csv_cell(person_names.get(lead.person_id) if lead.person_id else ""),
            _csv_cell(stage_names.get(lead.stage_id) if lead.stage_id else ""),
            _csv_cell(pipeline_names.get(lead.pipeline_id) if lead.pipeline_id else ""),
            _csv_cell(lead.expected_revenue),
            _csv_cell(lead.probability),
            _csv_cell(lead.expected_close_date.isoformat() if lead.expected_close_date else ""),
            _csv_cell(user_emails.get(lead.assigned_user_id) if lead.assigned_user_id else ""),
            _csv_cell(lead.create_date),
            _csv_cell(days_in_stage),
            _csv_cell(is_rotting),
        ])

    return buf.getvalue()


async def export_prospects_csv(session: AsyncSession, ctx: RequestContext) -> str:
    """Export tenant prospects as CSV text."""
    from modules.crm.controller.repositories import ProspectRepository

    prospect_repo = ProspectRepository(session, ctx)
    prospects, _ = await prospect_repo.search(
        limit=5000,
        order_by="create_date",
        order_dir="desc",
    )

    person_names, org_names = await _resolve_prospect_export_context(session, ctx, prospects)

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(PROSPECT_EXPORT_COLUMNS)

    for prospect in prospects:
        writer.writerow([
            _csv_cell(prospect.id),
            _csv_cell(prospect.name),
            _csv_cell(org_names.get(prospect.organization_id) if prospect.organization_id else ""),
            _csv_cell(person_names.get(prospect.person_id) if prospect.person_id else ""),
            _csv_cell(prospect.source),
            _csv_cell(prospect.temperature),
            _csv_cell(prospect.lifecycle_stage),
            _csv_cell(prospect.utm_source),
            _csv_cell(prospect.utm_campaign),
            _csv_cell(prospect.is_converted),
            _csv_cell(prospect.create_date),
        ])

    return buf.getvalue()


async def _find_or_create_organization(
    session: AsyncSession,
    ctx: RequestContext,
    name: str,
):
    from modules.crm.controller.repositories import OrganizationRepository

    repo = OrganizationRepository(session, ctx)
    rows, _ = await repo.search(domain=[("name", "=", name)], limit=1)
    if rows:
        return rows[0]
    return await repo.create({"name": name})


async def _find_or_create_person(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    name: str,
    email: str,
    organization_id: uuid.UUID | None,
):
    from modules.crm.controller.repositories import PersonRepository

    repo = PersonRepository(session, ctx)
    if email:
        rows, _ = await repo.search(domain=[("email", "=", email)], limit=1)
        if rows:
            return rows[0]

    rows, _ = await repo.search(domain=[("name", "=", name)], limit=1)
    if rows:
        return rows[0]

    payload: dict = {"name": name, "kind": "lead"}
    if email:
        payload["email"] = email
    if organization_id:
        payload["organization_id"] = organization_id
    return await repo.create(payload)


async def import_prospects_csv(
    session: AsyncSession,
    ctx: RequestContext,
    file_bytes: bytes,
) -> dict:
    """Import prospects from CSV bytes. Returns imported/skipped/errors summary."""
    from modules.crm.controller.repositories import ProspectRepository
    from modules.crm.model.domain import PROSPECT_TEMPERATURES

    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "name" not in reader.fieldnames:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": [{"row": 1, "message": "CSV must include a name column"}],
        }

    prospect_repo = ProspectRepository(session, ctx)
    existing_rows, _ = await prospect_repo.search(limit=5000)
    existing_names = {row.name.strip().lower() for row in existing_rows if row.name.strip()}
    seen_in_file: set[str] = set()

    imported = 0
    skipped = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        if not name:
            skipped += 1
            errors.append({"row": row_num, "message": "name is required"})
            continue

        name_key = name.lower()
        if name_key in existing_names or name_key in seen_in_file:
            skipped += 1
            errors.append({"row": row_num, "message": "duplicate name"})
            continue

        organization_id = None
        org_name = (row.get("organization_name") or "").strip()
        if org_name:
            org = await _find_or_create_organization(session, ctx, org_name)
            organization_id = org.id

        person_id = None
        person_name = (row.get("person_name") or "").strip()
        email = (row.get("email") or "").strip()
        if person_name:
            person = await _find_or_create_person(
                session,
                ctx,
                name=person_name,
                email=email,
                organization_id=organization_id,
            )
            person_id = person.id

        temperature = (row.get("temperature") or "cold").strip().lower() or "cold"
        if temperature not in PROSPECT_TEMPERATURES:
            skipped += 1
            errors.append({
                "row": row_num,
                "message": f"invalid temperature: {temperature}",
            })
            continue

        await prospect_repo.create({
            "name": name,
            "organization_id": organization_id,
            "person_id": person_id,
            "source": (row.get("source") or "").strip(),
            "temperature": temperature,
            "notes": (row.get("notes") or "").strip(),
            "utm_source": (row.get("utm_source") or "").strip(),
            "utm_campaign": (row.get("utm_campaign") or "").strip(),
            "assigned_user_id": ctx.user_id,
        })

        seen_in_file.add(name_key)
        existing_names.add(name_key)
        imported += 1

    return {"imported": imported, "skipped": skipped, "errors": errors}
