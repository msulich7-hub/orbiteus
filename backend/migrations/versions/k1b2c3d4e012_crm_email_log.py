"""CRM email log stub (SPEC-014).

Adds crm_email_logs for manual email logging on leads/prospects.

Revision ID: k1b2c3d4e012
Revises: j0a1b2c3d011
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k1b2c3d4e012"
down_revision: Union[str, tuple[str, ...], None] = "j0a1b2c3d011"
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
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("crm_email_logs"):
        return
    op.create_table(
        "crm_email_logs",
        *_base_columns(),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("prospect_id", sa.UUID(), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("from_address", sa.String(length=255), nullable=False),
        sa.Column("to_address", sa.String(length=255), nullable=False),
        sa.Column("cc", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(length=500), server_default="", nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["crm_leads.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["crm_prospects.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["base_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_email_logs_tenant_lead",
        "crm_email_logs",
        ["tenant_id", "lead_id"],
    )
    op.create_index(
        "ix_crm_email_logs_tenant_prospect",
        "crm_email_logs",
        ["tenant_id", "prospect_id"],
    )
    op.create_index(
        "ix_crm_email_logs_tenant_sent_at",
        "crm_email_logs",
        ["tenant_id", sa.text("sent_at DESC")],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_email_logs"):
        return
    op.drop_index("ix_crm_email_logs_tenant_sent_at", table_name="crm_email_logs")
    op.drop_index("ix_crm_email_logs_tenant_prospect", table_name="crm_email_logs")
    op.drop_index("ix_crm_email_logs_tenant_lead", table_name="crm_email_logs")
    op.drop_table("crm_email_logs")
