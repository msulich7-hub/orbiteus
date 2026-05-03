"""CRM module — RBAC access rights and record rules (PR 9 canonical)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CANONICAL_MODELS = ("crm.person", "crm.lead", "crm.stage", "crm.team")


CRM_ACCESS_RIGHTS = [
    *[
        {
            "role_name": "crm.group_crm_manager",
            "model_name": model,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": True,
        }
        for model in CANONICAL_MODELS
    ],
    *[
        {
            "role_name": "crm.group_crm_user",
            "model_name": model,
            "perm_read": True,
            "perm_write": True,
            "perm_create": True,
            "perm_unlink": False,
        }
        for model in ("crm.person", "crm.lead")
    ],
    *[
        {
            "role_name": "crm.group_crm_user",
            "model_name": model,
            "perm_read": True,
            "perm_write": False,
            "perm_create": False,
            "perm_unlink": False,
        }
        for model in ("crm.stage", "crm.team")
    ],
]


CRM_RECORD_RULES = [
    {
        "name": "crm_lead_salesman",
        "model_name": "crm.lead",
        "roles": ["crm.group_crm_user"],
        "global": False,
        "domain": [("assigned_user_id", "=", "current_user")],
    }
]


def setup() -> None:
    """Merge CRM access rights into the RBAC cache."""
    from orbiteus_core.security import rbac

    rbac._model_access.update(
        {
            entry["role_name"]: {
                **rbac._model_access.get(entry["role_name"], {}),
                entry["model_name"]: {
                    "read": entry["perm_read"],
                    "write": entry["perm_write"],
                    "create": entry["perm_create"],
                    "unlink": entry["perm_unlink"],
                },
            }
            for entry in CRM_ACCESS_RIGHTS
        }
    )

    for rule in CRM_RECORD_RULES:
        rbac._record_rules.setdefault(rule["model_name"], []).append(rule)

    logger.info(
        "CRM security loaded: %d access entries, %d rules",
        len(CRM_ACCESS_RIGHTS), len(CRM_RECORD_RULES),
    )
