"""CRM module domain models — canonical example for the Orbiteus engine.

Models (PR 9, ADR-0008):
  - Person  (kind=lead/customer/contact — unified contact record)
  - Lead    (sales pursuit attached to a Person)
  - Stage   (kanban / form statusbar progression)
  - Team    (sales team assignment)

The previous shape (Customer, Opportunity, Pipeline) is removed in this PR.
Migration `d4c0a1f2e005_canonical_crm.py` drops the old tables and creates
the new ones. See `docs/26-canonical-crm.md`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from orbiteus_core.base_domain import BaseModel


PERSON_KINDS = ("lead", "customer", "contact")


@dataclass
class Person(BaseModel):
    """Unified person/company record. `kind` distinguishes role in CRM."""

    name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""
    kind: str = "contact"               # lead | customer | contact
    is_company: bool = False
    vat: str = ""
    website: str = ""
    street: str = ""
    city: str = ""
    country_code: str = "PL"
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    tags: list[str] = field(default_factory=list)
    source: str = ""                    # website | referral | cold_call | event
    notes: str = ""


@dataclass
class Stage(BaseModel):
    """Kanban / statusbar step. Terminal flags: is_won, is_lost."""

    name: str = ""
    sequence: int = 10
    probability: float = 0.0            # default 0..100
    is_won: bool = False
    is_lost: bool = False
    fold_in_kanban: bool = False


@dataclass
class Team(BaseModel):
    """Sales team. `member_user_ids` is a JSONB list of base.user ids."""

    name: str = ""
    description: str = ""
    leader_user_id: uuid.UUID | None = None
    member_user_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass
class Lead(BaseModel):
    """Sales pursuit attached to a Person. Heart of the CRM-MVP."""

    name: str = ""
    person_id: uuid.UUID | None = None
    stage_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    assigned_team_id: uuid.UUID | None = None
    expected_revenue: float = 0.0
    probability: float = 0.0
    expected_close_date: date | None = None
    description: str = ""
    lost_reason: str = ""
    tags: list[str] = field(default_factory=list)
