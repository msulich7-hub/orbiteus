"""Structural tests for CRM work queues (SPEC-007)."""
from __future__ import annotations

import dataclasses
import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MIG = BACKEND / "migrations" / "versions" / "i9e5f6a7b010_crm_queues.py"


def _load(name: str, path: Path):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_queue_domain_model():
    domain = _load("orbiteus_crm_domain_queue", BACKEND / "modules" / "crm" / "model" / "domain.py")
    fields = {f.name for f in dataclasses.fields(domain.Queue)}
    for key in ("name", "model_name", "domain_json", "sort_json", "user_id", "is_shared", "sequence"):
        assert key in fields


def test_manifest_lists_queue():
    manifest = _load("orbiteus_crm_manifest_queue", BACKEND / "modules" / "crm" / "manifest.py")
    assert "crm.queue" in manifest.MANIFEST["models"]


def test_migration_creates_queues_table():
    text = MIG.read_text(encoding="utf-8")
    assert "crm_queues" in text
    assert "domain_json" in text


def test_router_has_queue_run_endpoint():
    router_text = (BACKEND / "modules" / "crm" / "controller" / "router.py").read_text(encoding="utf-8")
    assert "/queue/{queue_id}/run" in router_text


def test_bootstrap_seeds_default_queues():
    boot = _load("orbiteus_crm_boot_queue", BACKEND / "modules" / "crm" / "bootstrap.py")
    names = {q["name"] for q in boot._DEFAULT_QUEUES}
    assert "My rotting" in names
    assert "Closing this month" in names
    assert "No activity 7d" in names


def test_queue_filter_parser():
    filt = _load("orbiteus_crm_queue_filter", BACKEND / "modules" / "crm" / "controller" / "queue_filter.py")
    from datetime import datetime, timezone
    from uuid import uuid4

    from orbiteus_core.context import RequestContext

    from modules.crm.model.domain import Lead, Stage

    uid = uuid4()
    ctx = RequestContext(user_id=uid, tenant_id=uuid4())
    stage = Stage(id=uuid4(), rotting_days=7, is_won=False, is_lost=False)
    entered = datetime.now(timezone.utc)
    lead = Lead(
        id=uuid4(),
        name="Test",
        assigned_user_id=uid,
        stage_id=stage.id,
        stage_entered_at=entered,
    )
    stage_by_id = {stage.id: stage}
    assert filt.matches_domain(
        lead,
        {"assigned_user_id": "current_user", "is_rotting": False},
        ctx=ctx,
        stage_by_id=stage_by_id,
    )
