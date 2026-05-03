"""Static + structural tests for the canonical CRM rename (PR 9)."""
from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
MIG = BACKEND / "migrations" / "versions" / "d4c0a1f2e005_canonical_crm.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

def test_canonical_models_imported():
    sys.modules.pop("modules.crm.model.domain", None)
    domain = _load("orbiteus_crm_domain", BACKEND / "modules" / "crm" / "model" / "domain.py")
    assert hasattr(domain, "Person")
    assert hasattr(domain, "Lead")
    assert hasattr(domain, "Stage")
    assert hasattr(domain, "Team")
    # Old names are gone.
    assert not hasattr(domain, "Customer")
    assert not hasattr(domain, "Opportunity")
    assert not hasattr(domain, "Pipeline")


def test_person_kind_default_is_contact():
    domain = _load("orbiteus_crm_domain2", BACKEND / "modules" / "crm" / "model" / "domain.py")
    p = domain.Person(name="Alice")
    assert p.kind == "contact"
    assert "lead" in domain.PERSON_KINDS
    assert "customer" in domain.PERSON_KINDS


def test_lead_has_team_assignment_field():
    domain = _load("orbiteus_crm_domain3", BACKEND / "modules" / "crm" / "model" / "domain.py")
    fields = {f.name for f in dataclasses.fields(domain.Lead)}
    assert "person_id" in fields
    assert "stage_id" in fields
    assert "assigned_team_id" in fields
    assert "expected_close_date" in fields


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def test_migration_revises_ai():
    text = MIG.read_text()
    assert 'down_revision: Union[str, None] = "c3b5d2e1c004"' in text


def test_migration_drops_legacy_tables():
    text = MIG.read_text()
    for legacy in ("crm_customers", "crm_opportunities", "crm_pipelines"):
        assert f'DROP TABLE IF EXISTS {legacy}' in text


def test_migration_creates_canonical_tables():
    text = MIG.read_text()
    for tbl in ("crm_persons", "crm_teams", "crm_leads"):
        assert f'op.create_table(\n            "{tbl}"' in text
    # Stage is recreated, not dropped+left-out.
    assert 'op.create_table(\n            "crm_stages"' in text


def test_migration_uses_advisory_lock():
    assert "11534116837" in MIG.read_text()


# ---------------------------------------------------------------------------
# Manifest + bootstrap
# ---------------------------------------------------------------------------

def test_manifest_lists_canonical_models_and_bootstrap():
    sys.modules.pop("modules.crm.manifest", None)
    manifest = _load("orbiteus_crm_manifest", BACKEND / "modules" / "crm" / "manifest.py")
    m = manifest.MANIFEST
    assert m["models"] == ["crm.person", "crm.lead", "crm.stage", "crm.team"]
    assert m["bootstrap"] == "modules.crm.bootstrap"


def test_bootstrap_has_default_stages():
    sys.modules.pop("modules.crm.bootstrap", None)
    boot = _load("orbiteus_crm_boot", BACKEND / "modules" / "crm" / "bootstrap.py")
    names = {s["name"] for s in boot._DEFAULT_STAGES}
    assert {"New", "Qualified", "Won", "Lost"} <= names


# ---------------------------------------------------------------------------
# AI surface
# ---------------------------------------------------------------------------

def test_crm_ai_module_config_registers_into_registry():
    # The `modules.crm.ai` module imports `orbiteus_core.ai.config.ai_registry`
    # via the canonical package path; we therefore have to patch that exact
    # attribute, not a re-imported copy.
    sys.modules.pop("modules.crm.ai", None)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    from orbiteus_core.ai.config import ai_registry  # noqa: WPS433
    ai_registry._configs.clear()

    spec = importlib.util.spec_from_file_location(
        "modules.crm.ai", BACKEND / "modules" / "crm" / "ai.py"
    )
    assert spec and spec.loader
    ai_mod = importlib.util.module_from_spec(spec)
    sys.modules["modules.crm.ai"] = ai_mod
    spec.loader.exec_module(ai_mod)

    assert ai_mod.AI.enabled is True
    assert "crm.lead" in ai_mod.AI.accessible_models
    assert "crm" in ai_registry._configs


# ---------------------------------------------------------------------------
# api.py — _seed_crm_defaults removed
# ---------------------------------------------------------------------------

def test_api_no_longer_seeds_crm():
    api_text = (BACKEND / "api.py").read_text()
    # `_seed_crm_defaults` may appear once in the comment that documents the
    # rename — but never as a defined function nor as an `await` target.
    assert "async def _seed_crm_defaults" not in api_text
    assert "await _seed_crm_defaults" not in api_text
    assert "_bootstrap_modules" in api_text
    assert "_DEFAULT_CRM_PIPELINE" not in api_text


def test_legacy_re_exports_use_canonical_models():
    text = (BACKEND / "modules" / "crm" / "domain.py").read_text()
    assert "Lead" in text and "Person" in text and "Team" in text
    assert "Opportunity" not in text and "Customer" not in text
