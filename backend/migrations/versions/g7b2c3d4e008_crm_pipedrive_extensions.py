"""CRM Pipedrive-class extensions (SPEC-001..005).

Adds: organizations, pipelines, prospects, activities, stage histories.
Extends: persons, stages, leads with B2B + multi-pipeline + rotting fields.

Revision ID: g7b2c3d4e008
Revises: f6a1b2c3d007
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g7b2c3d4e008"
down_revision: Union[str, None] = "f6a1b2c3d007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("custom_fields", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("modified_by_id", sa.UUID(), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "crm_organizations",
        *_base_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("vat", sa.String(length=50), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=5), server_default="PL", nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("assigned_team_id", sa.UUID(), nullable=True),
        sa.Column("tags", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_organizations_tenant_id", "crm_organizations", ["tenant_id"])

    op.create_table(
        "crm_pipelines",
        *_base_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_pipelines_tenant_id", "crm_pipelines", ["tenant_id"])

    op.add_column(
        "crm_persons",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_crm_persons_organization_id",
        "crm_persons",
        "crm_organizations",
        ["organization_id"],
        ["id"],
    )

    op.add_column(
        "crm_stages",
        sa.Column("pipeline_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "crm_stages",
        sa.Column("rotting_days", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_crm_stages_pipeline_id",
        "crm_stages",
        "crm_pipelines",
        ["pipeline_id"],
        ["id"],
    )

    op.add_column(
        "crm_leads",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "crm_leads",
        sa.Column("pipeline_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "crm_leads",
        sa.Column("stage_entered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_leads",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_crm_leads_organization_id",
        "crm_leads",
        "crm_organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_crm_leads_pipeline_id",
        "crm_leads",
        "crm_pipelines",
        ["pipeline_id"],
        ["id"],
    )

    op.create_table(
        "crm_prospects",
        *_base_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("temperature", sa.String(length=20), server_default="cold", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_converted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("converted_lead_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["crm_persons.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"]),
        sa.ForeignKeyConstraint(["converted_lead_id"], ["crm_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_prospects_tenant_id", "crm_prospects", ["tenant_id"])

    op.create_table(
        "crm_activities",
        *_base_columns(),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("activity_type", sa.String(length=32), server_default="task", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("res_model", sa.String(length=64), nullable=True),
        sa.Column("res_id", sa.UUID(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_activities_tenant_id", "crm_activities", ["tenant_id"])
    op.create_index("ix_crm_activities_res", "crm_activities", ["res_model", "res_id"])

    op.create_table(
        "crm_stage_histories",
        *_base_columns(),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("from_stage_id", sa.UUID(), nullable=True),
        sa.Column("to_stage_id", sa.UUID(), nullable=False),
        sa.Column("changed_by_id", sa.UUID(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_leads.id"]),
        sa.ForeignKeyConstraint(["from_stage_id"], ["crm_stages.id"]),
        sa.ForeignKeyConstraint(["to_stage_id"], ["crm_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_stage_histories_lead_id", "crm_stage_histories", ["lead_id"])


def downgrade() -> None:
    op.drop_table("crm_stage_histories")
    op.drop_table("crm_activities")
    op.drop_table("crm_prospects")

    op.drop_constraint("fk_crm_leads_pipeline_id", "crm_leads", type_="foreignkey")
    op.drop_constraint("fk_crm_leads_organization_id", "crm_leads", type_="foreignkey")
    op.drop_column("crm_leads", "last_activity_at")
    op.drop_column("crm_leads", "stage_entered_at")
    op.drop_column("crm_leads", "pipeline_id")
    op.drop_column("crm_leads", "organization_id")

    op.drop_constraint("fk_crm_stages_pipeline_id", "crm_stages", type_="foreignkey")
    op.drop_column("crm_stages", "rotting_days")
    op.drop_column("crm_stages", "pipeline_id")

    op.drop_constraint("fk_crm_persons_organization_id", "crm_persons", type_="foreignkey")
    op.drop_column("crm_persons", "organization_id")

    op.drop_table("crm_pipelines")
    op.drop_table("crm_organizations")
