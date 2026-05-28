#!/usr/bin/env bash
# Repair DB: alembic stamped at head but CRM tables never created.
# Re-run migrations from pre-CRM revision (d4c0a1f2e005 canonical CRM).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STAMP_REV="${1:-c3b5d2e1c004}"

echo "=== Current alembic ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c \
  "SELECT version_num FROM alembic_version;"

echo "=== CRM table count (before) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c \
  "SELECT count(*) AS crm_tables FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Stamp to ${STAMP_REV} and upgrade head ==="
docker compose -p orbiteus exec -T backend alembic stamp "${STAMP_REV}"
docker compose -p orbiteus exec -T backend alembic upgrade head

echo "=== CRM table count (after) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c \
  "SELECT count(*) AS crm_tables FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Restart backend ==="
docker compose -p orbiteus restart backend worker beat

echo "=== Smoke: organization list ==="
docker compose -p orbiteus exec -T backend python -m pytest \
  tests/test_crm_csv.py::test_export_leads_csv_has_headers_and_seed_row -q --tb=line

echo "=== DONE ==="
