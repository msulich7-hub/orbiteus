"""CRM lifecycle stages + UTM attribution (SPEC-008).

Adds lifecycle_stage and UTM columns to crm_leads and crm_prospects.

Revision ID: h8d4e5f6a009
Revises: g7b2c3d4e008
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8d4e5f6a009"
down_revision: Union[str, None] = "g7b2c3d4e008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_lifecycle_and_utm(table: str) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if "lifecycle_stage" not in cols:
        op.add_column(
            table,
            sa.Column(
                "lifecycle_stage",
                sa.String(length=32),
                server_default="lead",
                nullable=False,
            ),
        )
    for col in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        if col not in cols:
            op.add_column(table, sa.Column(col, sa.String(length=255), nullable=True))
    idx_name = f"ix_{table}_lifecycle_stage"
    indexes = {i["name"] for i in insp.get_indexes(table)}
    if idx_name not in indexes:
        op.create_index(idx_name, table, ["lifecycle_stage"])


def _drop_lifecycle_and_utm(table: str) -> None:
    op.drop_index(f"ix_{table}_lifecycle_stage", table_name=table)
    for col in ("utm_term", "utm_content", "utm_campaign", "utm_medium", "utm_source"):
        op.drop_column(table, col)
    op.drop_column(table, "lifecycle_stage")


def upgrade() -> None:
    _add_lifecycle_and_utm("crm_leads")
    _add_lifecycle_and_utm("crm_prospects")


def downgrade() -> None:
    _drop_lifecycle_and_utm("crm_prospects")
    _drop_lifecycle_and_utm("crm_leads")
