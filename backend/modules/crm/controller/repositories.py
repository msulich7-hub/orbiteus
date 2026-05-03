"""CRM repositories (canonical: Person/Lead/Stage/Team)."""
from __future__ import annotations

from orbiteus_core.repository import BaseRepository

from modules.crm.model.domain import Lead, Person, Stage, Team


class PersonRepository(BaseRepository[Person]):
    model_name = "crm.person"
    domain_class = Person

    @property
    def table(self):
        from modules.crm.model.mapping import persons_table
        return persons_table


class StageRepository(BaseRepository[Stage]):
    model_name = "crm.stage"
    domain_class = Stage

    @property
    def table(self):
        from modules.crm.model.mapping import stages_table
        return stages_table


class TeamRepository(BaseRepository[Team]):
    model_name = "crm.team"
    domain_class = Team

    @property
    def table(self):
        from modules.crm.model.mapping import teams_table
        return teams_table


class LeadRepository(BaseRepository[Lead]):
    model_name = "crm.lead"
    domain_class = Lead

    @property
    def table(self):
        from modules.crm.model.mapping import leads_table
        return leads_table
