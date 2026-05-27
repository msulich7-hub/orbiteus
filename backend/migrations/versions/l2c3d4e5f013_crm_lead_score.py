"""CRM lead scoring columns (SPEC-015).

Adds score + score_updated_at to crm_leads and crm_prospects.

Revision ID: l2c3d4e5f013
Revises: k1b2c3d4e012
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l2c3d4e5f013"
down_revision: Union[str, tuple[str, ...], None] = "k1b2c3d4e012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_score_columns(table: str) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return
    if not insp.has_column(table, "score"):
        op.add_column(
            table,
            sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        )
    if not insp.has_column(table, "score_updated_at"):
        op.add_column(
            table,
            sa.Column("score_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def _ensure_score_index(table: str, index_name: str) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if index_name not in existing:
        op.create_index(
            index_name,
            table,
            ["tenant_id", sa.text("score DESC")],
        )


def upgrade() -> None:
    _add_score_columns("crm_leads")
    _add_score_columns("crm_prospects")
    _ensure_score_index("crm_leads", "ix_crm_leads_tenant_score")
    _ensure_score_index("crm_prospects", "ix_crm_prospects_tenant_score")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("crm_prospects"):
        existing = {idx["name"] for idx in insp.get_indexes("crm_prospects")}
        if "ix_crm_prospects_tenant_score" in existing:
            op.drop_index("ix_crm_prospects_tenant_score", table_name="crm_prospects")
        if insp.has_column("crm_prospects", "score_updated_at"):
            op.drop_column("crm_prospects", "score_updated_at")
        if insp.has_column("crm_prospects", "score"):
            op.drop_column("crm_prospects", "score")

    if insp.has_table("crm_leads"):
        existing = {idx["name"] for idx in insp.get_indexes("crm_leads")}
        if "ix_crm_leads_tenant_score" in existing:
            op.drop_index("ix_crm_leads_tenant_score", table_name="crm_leads")
        if insp.has_column("crm_leads", "score_updated_at"):
            op.drop_column("crm_leads", "score_updated_at")
        if insp.has_column("crm_leads", "score"):
            op.drop_column("crm_leads", "score")
