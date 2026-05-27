"""CRM automation rules (SPEC-006 v1).

Adds crm_automation_rules for event-driven workflow rules.

Revision ID: h8c3d4e5f009
Revises: g7b2c3d4e008
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8c3d4e5f009"
down_revision: Union[str, None] = "g7b2c3d4e008"
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
    if insp.has_table("crm_automation_rules"):
        return
    op.create_table(
        "crm_automation_rules",
        *_base_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_event", sa.String(length=128), nullable=False),
        sa.Column("condition_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("action_json", sa.JSON(), server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crm_automation_rules_tenant_id",
        "crm_automation_rules",
        ["tenant_id"],
    )
    op.create_index(
        "ix_crm_automation_rules_trigger_event",
        "crm_automation_rules",
        ["trigger_event"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_automation_rules_trigger_event", table_name="crm_automation_rules")
    op.drop_index("ix_crm_automation_rules_tenant_id", table_name="crm_automation_rules")
    op.drop_table("crm_automation_rules")
