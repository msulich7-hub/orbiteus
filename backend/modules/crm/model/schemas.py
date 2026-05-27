"""Pydantic Read/Write schemas for CRM models (SPEC-001..005)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel as PydanticBase
from pydantic import EmailStr, Field, field_validator

from modules.crm.model.domain import EMAIL_DIRECTIONS, LIFECYCLE_STAGES


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class OrganizationRead(PydanticBase):
    id: uuid.UUID
    name: str
    vat: str | None = None
    website: str | None = None
    industry: str | None = None
    assigned_user_id: uuid.UUID | None = None
    tags: list[str] = []
    create_date: datetime | None = None


class OrganizationWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    vat: str | None = None
    website: str | None = None
    street: str | None = None
    city: str | None = None
    country_code: str = "PL"
    industry: str | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = []
    notes: str = ""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class PipelineRead(PydanticBase):
    id: uuid.UUID
    name: str
    sequence: int
    is_default: bool
    color: str | None = None


class PipelineWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    sequence: int = 10
    is_default: bool = False
    color: str | None = None


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------

class PersonRead(PydanticBase):
    id: uuid.UUID
    name: str
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    kind: str
    is_company: bool
    organization_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = []
    source: str = ""
    create_date: datetime | None = None


class PersonWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    mobile: str | None = None
    kind: str = "contact"
    is_company: bool = False
    organization_id: uuid.UUID | None = None
    vat: str | None = None
    website: str | None = None
    street: str | None = None
    city: str | None = None
    country_code: str = "PL"
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = []
    source: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------

class StageRead(PydanticBase):
    id: uuid.UUID
    name: str
    pipeline_id: uuid.UUID | None = None
    sequence: int
    probability: float
    is_won: bool
    is_lost: bool
    fold_in_kanban: bool
    rotting_days: int | None = None
    required_fields_json: list[str] = []


class StageWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    pipeline_id: uuid.UUID | None = None
    sequence: int = 10
    probability: float = 0.0
    is_won: bool = False
    is_lost: bool = False
    fold_in_kanban: bool = False
    rotting_days: int | None = None
    required_fields_json: list[str] = []


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

class TeamRead(PydanticBase):
    id: uuid.UUID
    name: str
    description: str
    leader_user_id: uuid.UUID | None = None
    member_user_ids: list[uuid.UUID] = []


class TeamWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    leader_user_id: uuid.UUID | None = None
    member_user_ids: list[uuid.UUID] = []


# ---------------------------------------------------------------------------
# Lead (Deal)
# ---------------------------------------------------------------------------

class LeadRead(PydanticBase):
    id: uuid.UUID
    name: str
    person_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    expected_revenue: float
    probability: float
    expected_close_date: date | None = None
    description: str = ""
    tags: list[str] = []
    stage_entered_at: datetime | None = None
    last_activity_at: datetime | None = None
    lifecycle_stage: str = "lead"
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""
    score: int = 0
    score_updated_at: datetime | None = None


class LeadWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    person_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    expected_revenue: float = 0.0
    probability: float = 0.0
    expected_close_date: date | None = None
    description: str = ""
    lost_reason: str = ""
    tags: list[str] = []
    lifecycle_stage: str = "lead"
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""

    @field_validator("lifecycle_stage")
    @classmethod
    def _validate_lifecycle_stage(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in LIFECYCLE_STAGES:
            raise ValueError(
                f"lifecycle_stage must be one of: {', '.join(LIFECYCLE_STAGES)}"
            )
        return normalized


# ---------------------------------------------------------------------------
# Prospect
# ---------------------------------------------------------------------------

class ProspectRead(PydanticBase):
    id: uuid.UUID
    name: str
    person_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    source: str = ""
    temperature: str = "cold"
    is_converted: bool = False
    converted_lead_id: uuid.UUID | None = None
    lifecycle_stage: str = "lead"
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""
    score: int = 0
    score_updated_at: datetime | None = None


class ProspectWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    person_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    source: str = ""
    temperature: str = "cold"
    notes: str = ""
    lifecycle_stage: str = "lead"
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""

    @field_validator("lifecycle_stage")
    @classmethod
    def _validate_prospect_lifecycle_stage(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in LIFECYCLE_STAGES:
            raise ValueError(
                f"lifecycle_stage must be one of: {', '.join(LIFECYCLE_STAGES)}"
            )
        return normalized


class ProspectConvertRequest(PydanticBase):
    pipeline_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    expected_revenue: float = 0.0


class LeadMoveRequest(PydanticBase):
    lost_reason: str = ""


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class ActivityRead(PydanticBase):
    id: uuid.UUID
    subject: str
    activity_type: str
    due_date: datetime | None = None
    done: bool
    done_at: datetime | None = None
    assigned_user_id: uuid.UUID | None = None
    res_model: str = ""
    res_id: uuid.UUID | None = None
    outcome: str = ""


class ActivityWrite(PydanticBase):
    subject: str = Field(..., min_length=1, max_length=255)
    activity_type: str = "task"
    due_date: datetime | None = None
    assigned_user_id: uuid.UUID | None = None
    res_model: str = ""
    res_id: uuid.UUID | None = None
    duration_minutes: int | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Stage history
# ---------------------------------------------------------------------------

class StageHistoryRead(PydanticBase):
    id: uuid.UUID
    lead_id: uuid.UUID
    from_stage_id: uuid.UUID | None = None
    to_stage_id: uuid.UUID
    changed_by_id: uuid.UUID | None = None
    changed_at: datetime


class StageHistoryWrite(PydanticBase):
    lead_id: uuid.UUID
    from_stage_id: uuid.UUID | None = None
    to_stage_id: uuid.UUID
    changed_by_id: uuid.UUID | None = None
    changed_at: datetime


# ---------------------------------------------------------------------------
# Queue (work queue / saved view — SPEC-007)
# ---------------------------------------------------------------------------

class QueueRead(PydanticBase):
    id: uuid.UUID
    name: str
    model_name: str
    domain_json: dict = {}
    sort_json: dict = {}
    user_id: uuid.UUID | None = None
    is_shared: bool = False
    sequence: int = 10


class QueueWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    model_name: str = "crm.lead"
    domain_json: dict = {}
    sort_json: dict = {}
    user_id: uuid.UUID | None = None
    is_shared: bool = False
    sequence: int = 10


# ---------------------------------------------------------------------------
# Automation rule (SPEC-006)
# ---------------------------------------------------------------------------

class AutomationRuleRead(PydanticBase):
    id: uuid.UUID
    name: str
    trigger_event: str
    condition_json: dict = {}
    action_type: str
    action_json: dict = {}
    active: bool = True


class AutomationRuleWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    trigger_event: str = Field(..., min_length=1, max_length=128)
    condition_json: dict = {}
    action_type: str = "create_activity"
    action_json: dict = {}
    active: bool = True


# ---------------------------------------------------------------------------
# Email log (SPEC-014)
# ---------------------------------------------------------------------------

class EmailLogRead(PydanticBase):
    id: uuid.UUID
    lead_id: uuid.UUID | None = None
    prospect_id: uuid.UUID | None = None
    direction: str
    from_address: str
    to_address: str
    cc: str | None = None
    subject: str = ""
    body: str = ""
    sent_at: datetime
    created_by_id: uuid.UUID | None = None
    create_date: datetime | None = None


class EmailLogWrite(PydanticBase):
    direction: str = "outbound"
    from_address: str = Field(..., min_length=1, max_length=255)
    to_address: str = Field(..., min_length=1, max_length=255)
    cc: str | None = None
    subject: str = Field(default="", max_length=500)
    body: str = ""
    sent_at: datetime | None = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in EMAIL_DIRECTIONS:
            raise ValueError(f"direction must be one of {EMAIL_DIRECTIONS}")
        return value

    @field_validator("from_address", "to_address")
    @classmethod
    def validate_addresses(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("address must not be empty")
        return value.strip()
