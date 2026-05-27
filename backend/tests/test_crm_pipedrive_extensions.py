"""Structural tests for CRM Pipedrive-class extensions (SPEC-001..005)."""
from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MIG = BACKEND / "migrations" / "versions" / "g7b2c3d4e008_crm_pipedrive_extensions.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_extended_models_imported():
    domain = _load("orbiteus_crm_domain_ext", BACKEND / "modules" / "crm" / "model" / "domain.py")
    for cls in (
        "Organization",
        "Pipeline",
        "Person",
        "Lead",
        "Stage",
        "Team",
        "Prospect",
        "Activity",
        "StageHistory",
    ):
        assert hasattr(domain, cls), f"missing {cls}"


def test_lead_has_pipeline_and_org_fields():
    domain = _load("orbiteus_crm_domain_ext2", BACKEND / "modules" / "crm" / "model" / "domain.py")
    fields = {f.name for f in dataclasses.fields(domain.Lead)}
    assert "organization_id" in fields
    assert "pipeline_id" in fields
    assert "stage_entered_at" in fields
    assert "last_activity_at" in fields


def test_stage_has_pipeline_and_rotting():
    domain = _load("orbiteus_crm_domain_ext3", BACKEND / "modules" / "crm" / "model" / "domain.py")
    fields = {f.name for f in dataclasses.fields(domain.Stage)}
    assert "pipeline_id" in fields
    assert "rotting_days" in fields


def test_manifest_lists_extended_models():
    manifest = _load("orbiteus_crm_manifest_ext", BACKEND / "modules" / "crm" / "manifest.py")
    models = manifest.MANIFEST["models"]
    assert "crm.organization" in models
    assert "crm.pipeline" in models
    assert "crm.prospect" in models
    assert "crm.activity" in models
    assert manifest.MANIFEST["version"] == "0.4.0"


def test_bootstrap_seeds_pipeline_and_rotting():
    boot = _load("orbiteus_crm_boot_ext", BACKEND / "modules" / "crm" / "bootstrap.py")
    assert boot._DEFAULT_PIPELINE["is_default"] is True
    rotting = [s for s in boot._DEFAULT_STAGES if s.get("rotting_days")]
    assert len(rotting) >= 3


def test_migration_creates_extension_tables():
    text = MIG.read_text(encoding="utf-8")
    for tbl in (
        "crm_organizations",
        "crm_pipelines",
        "crm_prospects",
        "crm_activities",
        "crm_stage_histories",
    ):
        assert tbl in text
    assert 'down_revision: Union[str, None] = "f6a1b2c3d007"' in text


def test_router_has_convert_and_rotting_endpoints():
    router_text = (BACKEND / "modules" / "crm" / "controller" / "router.py").read_text(encoding="utf-8")
    assert "/prospect/{prospect_id}/convert" in router_text
    assert "/leads/rotting" in router_text
    assert "/activities/today" in router_text


def test_stats_includes_open_prospects_and_rotting():
    router_text = (BACKEND / "modules" / "crm" / "controller" / "router.py").read_text(encoding="utf-8")
    assert "open_prospects" in router_text
    assert "rotting_leads" in router_text


def test_navigate_actions_use_filter_urls():
    actions_text = (BACKEND / "modules" / "crm" / "actions.py").read_text(encoding="utf-8")
    assert 'target_url="/crm/lead?view=kanban"' in actions_text
    assert 'target_url="/crm/lead?filter=rotting"' in actions_text
    assert 'target_url="/crm/activity?filter=today"' in actions_text
    assert 'target_url="/crm/prospect?filter=inbox"' in actions_text
