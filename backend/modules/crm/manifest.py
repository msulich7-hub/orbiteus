"""CRM module manifest (canonical: Person/Lead/Stage/Team)."""

MANIFEST = {
    "name": "CRM",
    "version": "0.2.0",  # PR 9: rename — see ADR-0008
    "depends_on": ["base", "auth"],
    "models": [
        "crm.person",
        "crm.lead",
        "crm.stage",
        "crm.team",
    ],
    "category": "Sales",
    "auto_install": False,
    "data": [
        "security/access.yaml",
    ],
    "menus": [
        {"name": "CRM",       "sequence": 10, "icon": "users"},
        {"name": "Persons",   "parent": "CRM", "sequence": 10, "model": "crm.person"},
        {"name": "Leads",     "parent": "CRM", "sequence": 20, "model": "crm.lead"},
        {"name": "Stages",    "parent": "CRM", "sequence": 30, "model": "crm.stage"},
        {"name": "Teams",     "parent": "CRM", "sequence": 40, "model": "crm.team"},
    ],
    "view_config": "modules.crm.view.config",
    "bootstrap": "modules.crm.bootstrap",
}
