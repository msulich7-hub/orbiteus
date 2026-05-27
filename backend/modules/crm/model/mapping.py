"""CRM module — SQLAlchemy imperative mapping (SPEC-001..006)."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
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
from modules.crm.model.domain import (
    Activity,
    AutomationRule,
    EmailLog,
    Lead,
    Organization,
    Person,
    Pipeline,
    Prospect,
    Queue,
    Stage,
    StageHistory,
    Team,
)

organizations_table: Table | None = None
pipelines_table: Table | None = None
persons_table: Table | None = None
stages_table: Table | None = None
teams_table: Table | None = None
leads_table: Table | None = None
prospects_table: Table | None = None
activities_table: Table | None = None
stage_histories_table: Table | None = None
queues_table: Table | None = None
automation_rules_table: Table | None = None
email_logs_table: Table | None = None


def _build_tables() -> tuple[Table, ...]:
    organizations = Table(
        "crm_organizations",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("vat", String(50)),
        Column("website", String(255)),
        Column("street", String(255)),
        Column("city", String(100)),
        Column("country_code", String(5), server_default="PL"),
        Column("industry", String(100)),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("assigned_team_id", UUID(as_uuid=True), nullable=True),
        Column("tags", JSON, server_default="[]"),
        Column("notes", Text),
    )

    pipelines = Table(
        "crm_pipelines",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("sequence", Integer, server_default="10"),
        Column("is_default", Boolean, server_default="false"),
        Column("color", String(20)),
    )

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
        Column("organization_id", UUID(as_uuid=True), ForeignKey("crm_organizations.id"), nullable=True),
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
        Column("pipeline_id", UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=True),
        Column("sequence", Integer, server_default="10"),
        Column("probability", Float, server_default="0"),
        Column("is_won", Boolean, server_default="false"),
        Column("is_lost", Boolean, server_default="false"),
        Column("fold_in_kanban", Boolean, server_default="false"),
        Column("rotting_days", Integer, nullable=True),
        Column("required_fields_json", JSON, server_default="[]"),
    )

    teams = Table(
        "crm_teams",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("description", Text),
        Column("leader_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("member_user_ids", JSON, server_default="[]"),
    )

    leads = Table(
        "crm_leads",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("person_id", UUID(as_uuid=True), ForeignKey("crm_persons.id"), nullable=True),
        Column("organization_id", UUID(as_uuid=True), ForeignKey("crm_organizations.id"), nullable=True),
        Column("pipeline_id", UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=True),
        Column("stage_id", UUID(as_uuid=True), ForeignKey("crm_stages.id"), nullable=True),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("assigned_team_id", UUID(as_uuid=True), ForeignKey("crm_teams.id"), nullable=True),
        Column("expected_revenue", Float, server_default="0"),
        Column("probability", Float, server_default="0"),
        Column("expected_close_date", Date),
        Column("description", Text),
        Column("lost_reason", String(500)),
        Column("tags", JSON, server_default="[]"),
        Column("stage_entered_at", DateTime(timezone=True)),
        Column("last_activity_at", DateTime(timezone=True)),
        Column("lifecycle_stage", String(32), server_default="lead", index=True),
        Column("utm_source", String(255)),
        Column("utm_medium", String(255)),
        Column("utm_campaign", String(255)),
        Column("utm_content", String(255)),
        Column("utm_term", String(255)),
        Column("score", Integer, server_default="0", nullable=False),
        Column("score_updated_at", DateTime(timezone=True)),
    )

    prospects = Table(
        "crm_prospects",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("person_id", UUID(as_uuid=True), ForeignKey("crm_persons.id"), nullable=True),
        Column("organization_id", UUID(as_uuid=True), ForeignKey("crm_organizations.id"), nullable=True),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("source", String(50)),
        Column("temperature", String(20), server_default="cold"),
        Column("notes", Text),
        Column("is_converted", Boolean, server_default="false"),
        Column("converted_lead_id", UUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=True),
        Column("lifecycle_stage", String(32), server_default="lead", index=True),
        Column("utm_source", String(255)),
        Column("utm_medium", String(255)),
        Column("utm_campaign", String(255)),
        Column("utm_content", String(255)),
        Column("utm_term", String(255)),
        Column("score", Integer, server_default="0", nullable=False),
        Column("score_updated_at", DateTime(timezone=True)),
    )

    activities = Table(
        "crm_activities",
        metadata,
        *make_base_columns(),
        Column("subject", String(255), nullable=False),
        Column("activity_type", String(32), server_default="task"),
        Column("due_date", DateTime(timezone=True)),
        Column("done", Boolean, server_default="false"),
        Column("done_at", DateTime(timezone=True)),
        Column("assigned_user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("res_model", String(64)),
        Column("res_id", UUID(as_uuid=True)),
        Column("duration_minutes", Integer),
        Column("outcome", String(255)),
        Column("notes", Text),
    )

    stage_histories = Table(
        "crm_stage_histories",
        metadata,
        *make_base_columns(),
        Column("lead_id", UUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=False),
        Column("from_stage_id", UUID(as_uuid=True), ForeignKey("crm_stages.id"), nullable=True),
        Column("to_stage_id", UUID(as_uuid=True), ForeignKey("crm_stages.id"), nullable=False),
        Column("changed_by_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("changed_at", DateTime(timezone=True), nullable=False),
    )

    automation_rules = Table(
        "crm_automation_rules",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("trigger_event", String(128), nullable=False, index=True),
        Column("condition_json", JSON, server_default="{}"),
        Column("action_type", String(64), nullable=False),
        Column("action_json", JSON, server_default="{}"),
    )

    queues = Table(
        "crm_queues",
        metadata,
        *make_base_columns(),
        Column("name", String(255), nullable=False),
        Column("model_name", String(64), server_default="crm.lead", nullable=False),
        Column("domain_json", JSON, server_default="{}"),
        Column("sort_json", JSON, server_default="{}"),
        Column("user_id", UUID(as_uuid=True), ForeignKey("base_users.id"), nullable=True),
        Column("is_shared", Boolean, server_default="false"),
        Column("sequence", Integer, server_default="10"),
    )

    email_logs = Table(
        "crm_email_logs",
        metadata,
        *make_base_columns(),
        Column("lead_id", UUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=True),
        Column("prospect_id", UUID(as_uuid=True), ForeignKey("crm_prospects.id"), nullable=True),
        Column("direction", String(8), nullable=False),
        Column("from_address", String(255), nullable=False),
        Column("to_address", String(255), nullable=False),
        Column("cc", Text, nullable=True),
        Column("subject", String(500), server_default=""),
        Column("body", Text, server_default=""),
        Column("sent_at", DateTime(timezone=True), nullable=False),
    )

    return (
        organizations,
        pipelines,
        persons,
        stages,
        teams,
        leads,
        prospects,
        activities,
        stage_histories,
        automation_rules,
        queues,
        email_logs,
    )


def setup() -> None:
    """Called by ModuleRegistry during module load."""
    global organizations_table, pipelines_table, persons_table, stages_table
    global teams_table, leads_table, prospects_table, activities_table, stage_histories_table
    global automation_rules_table, queues_table, email_logs_table

    (
        organizations_table,
        pipelines_table,
        persons_table,
        stages_table,
        teams_table,
        leads_table,
        prospects_table,
        activities_table,
        stage_histories_table,
        automation_rules_table,
        queues_table,
        email_logs_table,
    ) = _build_tables()

    register_mapping(Organization, organizations_table)
    register_mapping(Pipeline, pipelines_table)
    register_mapping(Person, persons_table)
    register_mapping(Stage, stages_table)
    register_mapping(Team, teams_table)
    register_mapping(Lead, leads_table)
    register_mapping(Prospect, prospects_table)
    register_mapping(Activity, activities_table)
    register_mapping(StageHistory, stage_histories_table)
    register_mapping(AutomationRule, automation_rules_table)
    register_mapping(Queue, queues_table)
    register_mapping(EmailLog, email_logs_table)

    from modules.crm.controller.repositories import (
        ActivityRepository,
        AutomationRuleRepository,
        EmailLogRepository,
        LeadRepository,
        OrganizationRepository,
        PersonRepository,
        PipelineRepository,
        ProspectRepository,
        QueueRepository,
        StageHistoryRepository,
        StageRepository,
        TeamRepository,
    )

    register_model(
        "crm.organization", Organization, OrganizationRepository, organizations_table,
        schemas.OrganizationRead, schemas.OrganizationWrite,
    )
    register_model(
        "crm.pipeline", Pipeline, PipelineRepository, pipelines_table,
        schemas.PipelineRead, schemas.PipelineWrite,
    )
    register_model(
        "crm.person", Person, PersonRepository, persons_table,
        schemas.PersonRead, schemas.PersonWrite,
    )
    register_model(
        "crm.stage", Stage, StageRepository, stages_table,
        schemas.StageRead, schemas.StageWrite,
    )
    register_model(
        "crm.team", Team, TeamRepository, teams_table,
        schemas.TeamRead, schemas.TeamWrite,
    )
    register_model(
        "crm.lead", Lead, LeadRepository, leads_table,
        schemas.LeadRead, schemas.LeadWrite,
    )
    register_model(
        "crm.prospect", Prospect, ProspectRepository, prospects_table,
        schemas.ProspectRead, schemas.ProspectWrite,
    )
    register_model(
        "crm.activity", Activity, ActivityRepository, activities_table,
        schemas.ActivityRead, schemas.ActivityWrite,
    )
    register_model(
        "crm.stage_history", StageHistory, StageHistoryRepository, stage_histories_table,
        schemas.StageHistoryRead, schemas.StageHistoryWrite,
    )
    register_model(
        "crm.queue", Queue, QueueRepository, queues_table,
        schemas.QueueRead, schemas.QueueWrite,
    )
    register_model(
        "crm.automation_rule", AutomationRule, AutomationRuleRepository, automation_rules_table,
        schemas.AutomationRuleRead, schemas.AutomationRuleWrite,
    )
    register_model(
        "crm.email_log", EmailLog, EmailLogRepository, email_logs_table,
        schemas.EmailLogRead, schemas.EmailLogWrite,
    )
