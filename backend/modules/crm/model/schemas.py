"""Pydantic Read/Write schemas for the canonical CRM models (PR 9)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel as PydanticBase
from pydantic import EmailStr, Field


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
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = []
    source: str = ""
    create_date: datetime | None = None
    write_date: datetime | None = None


class PersonWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    mobile: str | None = None
    kind: str = "contact"
    is_company: bool = False
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
    sequence: int
    probability: float
    is_won: bool
    is_lost: bool
    fold_in_kanban: bool


class StageWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    sequence: int = 10
    probability: float = 0.0
    is_won: bool = False
    is_lost: bool = False
    fold_in_kanban: bool = False


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
# Lead
# ---------------------------------------------------------------------------

class LeadRead(PydanticBase):
    id: uuid.UUID
    name: str
    person_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    expected_revenue: float
    probability: float
    expected_close_date: date | None = None
    description: str = ""
    tags: list[str] = []


class LeadWrite(PydanticBase):
    name: str = Field(..., min_length=1, max_length=255)
    person_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    expected_revenue: float = 0.0
    probability: float = 0.0
    expected_close_date: date | None = None
    description: str = ""
    lost_reason: str = ""
    tags: list[str] = []
