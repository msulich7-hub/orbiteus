"""CRM stage exit blueprint — required_fields_json on crm_stages.

Revision ID: j0a1b2c3d011
Revises: i9e5f6a7b010
Create Date: 2026-05-22
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0a1b2c3d011"
down_revision: Union[str, tuple[str, ...], None] = "i9e5f6a7b010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_stages"):
        return
    cols = {c["name"] for c in insp.get_columns("crm_stages")}
    if "required_fields_json" not in cols:
        op.add_column(
            "crm_stages",
            sa.Column("required_fields_json", sa.JSON(), server_default="[]", nullable=False),
        )
    op.execute(
        sa.text(
            """
            UPDATE crm_stages
            SET required_fields_json = '["expected_close_date"]'::json
            WHERE name = 'Proposal'
              AND (
                required_fields_json IS NULL
                OR required_fields_json::text = '[]'
              )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_stages"):
        return
    cols = {c["name"] for c in insp.get_columns("crm_stages")}
    if "required_fields_json" in cols:
        op.drop_column("crm_stages", "required_fields_json")
