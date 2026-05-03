"""CRM module – admin-ui view configuration (LEGACY / superseded).

Background
----------
This file used to declare a static `UI_CONFIG` dictionary describing list /
kanban / form views for the *legacy* CRM models — `crm.customer`,
`crm.opportunity`, `crm.pipeline`, and the pre-rename `crm.stage`.

Those models were retired by **ADR-0008** ("CRM-MVP rename:
Person / Lead / Stage / Team") and replaced by the canonical CRM models in
`backend/modules/crm/model/`:

* `crm.person` — contacts (`kind` enum: customer / vendor / partner /
  individual)
* `crm.lead`   — sales opportunities tied to a Person and a Stage
* `crm.stage`  — pipeline columns (re-shaped: dropped `pipeline_id`,
  added `is_won`/sequence semantics)
* `crm.team`   — sales teams

The Admin UI no longer reads any per-module `view_config` dictionaries.
Both the dynamic dispatcher in `admin-ui/src/app/[module]/[model]/*` and
the schema served at `GET /api/base/ui-config` are driven by:

* the SQLAlchemy table definitions in `model/mapping.py`,
* the Pydantic Read/Write schemas in `model/schemas.py`,
* and any optional XML view archs declared in `view/`.

Keeping this file as an empty stub preserves the import surface declared
in `manifest.py["view_config"]` without leaking obsolete model names back
into the runtime catalogue.
"""
from __future__ import annotations

UI_CONFIG: dict = {}
