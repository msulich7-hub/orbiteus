#!/usr/bin/env bash
# Idempotent repair: create missing ORM tables (crm_*, shipping_*, inventory_*).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== CRM tables (before) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Create missing tables from metadata ==="
docker compose -p orbiteus exec -T backend sh -c "cd /app && python scripts/repair_missing_tables.py"

echo "=== CRM tables (after) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Restart API ==="
docker compose -p orbiteus restart backend worker beat

echo "=== Smoke ==="
docker compose -p orbiteus exec -T backend python -m pytest \
  tests/test_crm_csv.py::test_export_leads_csv_has_headers_and_seed_row -q --tb=line

echo "=== DONE ==="
