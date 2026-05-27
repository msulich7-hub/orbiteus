"""CRM repositories (SPEC-001..005)."""
from __future__ import annotations

from orbiteus_core.repository import BaseRepository

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


class OrganizationRepository(BaseRepository[Organization]):
    model_name = "crm.organization"
    domain_class = Organization

    @property
    def table(self):
        from modules.crm.model.mapping import organizations_table
        return organizations_table


class PipelineRepository(BaseRepository[Pipeline]):
    model_name = "crm.pipeline"
    domain_class = Pipeline

    @property
    def table(self):
        from modules.crm.model.mapping import pipelines_table
        return pipelines_table


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


class ProspectRepository(BaseRepository[Prospect]):
    model_name = "crm.prospect"
    domain_class = Prospect

    @property
    def table(self):
        from modules.crm.model.mapping import prospects_table
        return prospects_table


class ActivityRepository(BaseRepository[Activity]):
    model_name = "crm.activity"
    domain_class = Activity

    @property
    def table(self):
        from modules.crm.model.mapping import activities_table
        return activities_table


class StageHistoryRepository(BaseRepository[StageHistory]):
    model_name = "crm.stage_history"
    domain_class = StageHistory

    @property
    def table(self):
        from modules.crm.model.mapping import stage_histories_table
        return stage_histories_table


class AutomationRuleRepository(BaseRepository[AutomationRule]):
    model_name = "crm.automation_rule"
    domain_class = AutomationRule

    @property
    def table(self):
        from modules.crm.model.mapping import automation_rules_table
        return automation_rules_table


class QueueRepository(BaseRepository[Queue]):
    model_name = "crm.queue"
    domain_class = Queue

    @property
    def table(self):
        from modules.crm.model.mapping import queues_table
        return queues_table


class EmailLogRepository(BaseRepository[EmailLog]):
    model_name = "crm.email_log"
    domain_class = EmailLog

    @property
    def table(self):
        from modules.crm.model.mapping import email_logs_table
        return email_logs_table
