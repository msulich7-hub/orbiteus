"""CRM work queues / saved views (SPEC-007).

Adds crm_queues for filtered lead work queues.

Revision ID: i9e5f6a7b010
Revises: h8c3d4e5f009, h8d4e5f6a009
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9e5f6a7b010"
down_revision: Union[str, tuple[str, ...], None] = ("h8c3d4e5f009", "h8d4e5f6a009")
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
    if insp.has_table("crm_queues"):
        return
    op.create_table(
        "crm_queues",
        *_base_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=64), server_default="crm.lead", nullable=False),
        sa.Column("domain_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("sort_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("is_shared", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sequence", sa.Integer(), server_default="10", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["base_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_queues_tenant_id", "crm_queues", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_queues_tenant_id", table_name="crm_queues")
    op.drop_table("crm_queues")
