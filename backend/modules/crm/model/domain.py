"""CRM module domain models — Pipedrive-class extensions (SPEC-001..005).

Models:
  - Organization  B2B account (company)
  - Person        Contact linked to Organization
  - Pipeline      Multi-pipeline support
  - Stage         Kanban column scoped to Pipeline
  - Lead          Deal / opportunity in pipeline
  - Prospect      Pre-pipeline inbox (Leads vs Deals)
  - Activity      Calls, tasks, meetings — execution layer
  - StageHistory  Audit trail of stage moves
  - Team          Sales team
  - AutomationRule  Event-driven workflow rule (SPEC-006)
  - EmailLog        Manual email log stub (SPEC-014)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from orbiteus_core.base_domain import BaseModel


PERSON_KINDS = ("lead", "customer", "contact")
ACTIVITY_TYPES = ("call", "meeting", "task", "email", "deadline", "note")
EMAIL_DIRECTIONS = ("inbound", "outbound")
PROSPECT_TEMPERATURES = ("cold", "warm", "hot")
AUTOMATION_ACTION_TYPES = ("create_activity", "notify")
LIFECYCLE_STAGES = ("subscriber", "lead", "mql", "sql", "opportunity", "customer")


@dataclass
class Organization(BaseModel):
    """B2B account — Pipedrive Organization / HubSpot Company."""

    name: str = ""
    vat: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    country_code: str = "PL"
    industry: str = ""
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Person(BaseModel):
    """Contact person. Linked to Organization for B2B."""

    name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    kind: str = "contact"
    is_company: bool = False
    organization_id: uuid.UUID | None = None
    vat: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    country_code: str = "PL"
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = field(default_factory=list)
    source: str = ""
    notes: str = ""


@dataclass
class Pipeline(BaseModel):
    """Sales pipeline — multiple motions per tenant."""

    name: str = ""
    sequence: int = 10
    is_default: bool = False
    color: str = ""


@dataclass
class Stage(BaseModel):
    """Kanban step scoped to a Pipeline."""

    name: str = ""
    pipeline_id: uuid.UUID | None = None
    sequence: int = 10
    probability: float = 0.0
    is_won: bool = False
    is_lost: bool = False
    fold_in_kanban: bool = False
    rotting_days: int | None = None
    required_fields_json: list[str] = field(default_factory=list)


@dataclass
class Team(BaseModel):
    """Sales team."""

    name: str = ""
    description: str = ""
    leader_user_id: uuid.UUID | None = None
    member_user_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass
class Lead(BaseModel):
    """Deal in pipeline — heart of revenue tracking."""

    name: str = ""
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
    tags: list[str] = field(default_factory=list)
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


@dataclass
class Prospect(BaseModel):
    """Pre-pipeline lead inbox — before deal qualification."""

    name: str = ""
    person_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    source: str = ""
    temperature: str = "cold"
    notes: str = ""
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


@dataclass
class Activity(BaseModel):
    """Execution item — call, meeting, task."""

    subject: str = ""
    activity_type: str = "task"
    due_date: datetime | None = None
    done: bool = False
    done_at: datetime | None = None
    assigned_user_id: uuid.UUID | None = None
    res_model: str = ""
    res_id: uuid.UUID | None = None
    duration_minutes: int | None = None
    outcome: str = ""
    notes: str = ""


@dataclass
class StageHistory(BaseModel):
    """Immutable log of lead stage transitions."""

    lead_id: uuid.UUID | None = None
    from_stage_id: uuid.UUID | None = None
    to_stage_id: uuid.UUID | None = None
    changed_by_id: uuid.UUID | None = None
    changed_at: datetime | None = None


@dataclass
class Queue(BaseModel):
    """Saved view / work queue (SPEC-007)."""

    name: str = ""
    model_name: str = "crm.lead"
    domain_json: dict = field(default_factory=dict)
    sort_json: dict = field(default_factory=dict)
    user_id: uuid.UUID | None = None
    is_shared: bool = False
    sequence: int = 10


@dataclass
class AutomationRule(BaseModel):
    """Automation rule — trigger + condition + action (SPEC-006 v1)."""

    name: str = ""
    trigger_event: str = ""
    condition_json: dict = field(default_factory=dict)
    action_type: str = "create_activity"
    action_json: dict = field(default_factory=dict)


@dataclass
class EmailLog(BaseModel):
    """Logged email on a lead or prospect — stub without SMTP (SPEC-014)."""

    lead_id: uuid.UUID | None = None
    prospect_id: uuid.UUID | None = None
    direction: str = "outbound"
    from_address: str = ""
    to_address: str = ""
    cc: str | None = None
    subject: str = ""
    body: str = ""
    sent_at: datetime | None = None
