"""Structural tests for CRM lifecycle + UTM attribution (SPEC-008)."""
from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
MIG = BACKEND / "migrations" / "versions" / "h8d4e5f6a009_crm_lifecycle_attribution.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_lifecycle_stages_constant():
    domain = _load("orbiteus_crm_domain_lc", BACKEND / "modules" / "crm" / "model" / "domain.py")
    assert domain.LIFECYCLE_STAGES == (
        "subscriber",
        "lead",
        "mql",
        "sql",
        "opportunity",
        "customer",
    )


def test_lead_and_prospect_have_lifecycle_and_utm_fields():
    domain = _load("orbiteus_crm_domain_lc2", BACKEND / "modules" / "crm" / "model" / "domain.py")
    for cls_name in ("Lead", "Prospect"):
        fields = {f.name for f in dataclasses.fields(getattr(domain, cls_name))}
        assert "lifecycle_stage" in fields
        for utm in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
            assert utm in fields, f"{cls_name} missing {utm}"


def test_migration_adds_lifecycle_columns():
    text = MIG.read_text()
    for tbl in ("crm_leads", "crm_prospects"):
        assert f'"{tbl}"' in text or tbl in text
        assert "lifecycle_stage" in text
        assert "utm_source" in text
        assert "utm_campaign" in text
    assert 'down_revision: Union[str, None] = "g7b2c3d4e008"' in text


def test_router_has_lifecycle_patch_endpoint():
    router_text = (BACKEND / "modules" / "crm" / "controller" / "router.py").read_text()
    assert "/lead/{lead_id}/lifecycle" in router_text
    assert "patch_lead_lifecycle" in router_text


def test_convert_service_sets_sql_and_copies_utm():
    services_text = (BACKEND / "modules" / "crm" / "controller" / "services.py").read_text()
    assert '"lifecycle_stage": "sql"' in services_text
    assert "_utm_fields_from_prospect" in services_text
    assert "utm_source" in services_text


def test_normalize_lifecycle_stage_accepts_and_rejects():
    _load("orbiteus_crm_services_lc", BACKEND / "modules" / "crm" / "controller" / "services.py")
    from fastapi import HTTPException

    from modules.crm.controller.services import normalize_lifecycle_stage

    assert normalize_lifecycle_stage("MQL") == "mql"
    assert normalize_lifecycle_stage(" sql ") == "sql"

    with pytest.raises(HTTPException) as exc:
        normalize_lifecycle_stage("unknown")
    assert exc.value.status_code == 400
    assert "allowed" in exc.value.detail


def test_lead_write_schema_validates_lifecycle():
    _load("orbiteus_crm_schemas_lc", BACKEND / "modules" / "crm" / "model" / "schemas.py")
    from pydantic import ValidationError

    from modules.crm.model.schemas import LeadWrite

    lead = LeadWrite(name="Deal A", lifecycle_stage="opportunity")
    assert lead.lifecycle_stage == "opportunity"

    with pytest.raises(ValidationError):
        LeadWrite(name="Deal B", lifecycle_stage="bogus")
