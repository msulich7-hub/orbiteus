"""CRM module — SQLAlchemy imperative mapping (canonical: Person/Lead/Stage/Team)."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.auto_router import register_model
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping

from modules.crm.model import schemas
from modules.crm.model.domain import Lead, Person, Stage, Team


# Module-level table refs (set in setup()).
persons_table: Table | None = None
stages_table: Table | None = None
teams_table: Table | None = None
leads_table: Table | None = None


def _build_tables() -> tuple[Table, Table, Table, Table]:
    persons = Table(
        "crm_persons",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("email", String(320)),
        Column("phone", String(50)),
        Column("mobile", String(50)),
        Column("kind", String(20), server_default="contact", index=True),
        Column("is_company", Boolean, server_default="false"),
        Column("vat", String(50)),
        Column("website", String(255)),
        Column("street", String(255)),
        Column("city", String(100)),
        Column("country_code", String(5), server_default="PL"),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("assigned_team_id", UUID(as_uuid=True), nullable=True),
        Column("tags", JSON, server_default="[]"),
        Column("source", String(50)),
        Column("notes", Text),
    )

    stages = Table(
        "crm_stages",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("sequence", Integer, server_default="10"),
        Column("probability", Float, server_default="0"),
        Column("is_won", Boolean, server_default="false"),
        Column("is_lost", Boolean, server_default="false"),
        Column("fold_in_kanban", Boolean, server_default="false"),
    )

    teams = Table(
        "crm_teams",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("description", Text),
        Column("leader_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        # JSONB list of base.user UUIDs (cross-module FK kept as UUID per ADR / docs/03).
        Column("member_user_ids", JSON, server_default="[]"),
    )

    leads = Table(
        "crm_leads",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("person_id", UUID(as_uuid=True), ForeignKey("crm_persons.id"), nullable=True),
        Column("stage_id", UUID(as_uuid=True), ForeignKey("crm_stages.id"), nullable=True),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("assigned_team_id", UUID(as_uuid=True), ForeignKey("crm_teams.id"), nullable=True),
        Column("expected_revenue", Float, server_default="0"),
        Column("probability", Float, server_default="0"),
        Column("expected_close_date", Date),
        Column("description", Text),
        Column("lost_reason", String(500)),
        Column("tags", JSON, server_default="[]"),
    )

    return persons, stages, teams, leads


def setup() -> None:
    """Called by ModuleRegistry during module load."""
    global persons_table, stages_table, teams_table, leads_table

    persons_table, stages_table, teams_table, leads_table = _build_tables()

    register_mapping(Person, persons_table)
    register_mapping(Stage, stages_table)
    register_mapping(Team, teams_table)
    register_mapping(Lead, leads_table)

    from modules.crm.controller.repositories import (
        LeadRepository,
        PersonRepository,
        StageRepository,
        TeamRepository,
    )

    register_model("crm.person", Person, PersonRepository, persons_table,
                   schemas.PersonRead, schemas.PersonWrite)
    register_model("crm.stage", Stage, StageRepository, stages_table,
                   schemas.StageRead, schemas.StageWrite)
    register_model("crm.team", Team, TeamRepository, teams_table,
                   schemas.TeamRead, schemas.TeamWrite)
    register_model("crm.lead", Lead, LeadRepository, leads_table,
                   schemas.LeadRead, schemas.LeadWrite)
