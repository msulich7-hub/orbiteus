#!/usr/bin/env bash
# Deploy msulich7-hub/orbiteus on VM (MDM intranet).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== 1) Pull msulich7-hub/orbiteus ==="
git fetch origin
git pull origin main

echo "=== 2) Rebuild stack (orbiteus project) ==="
docker compose -p orbiteus \
  -f docker-compose.yml \
  -f docker-compose.vm-ports.yml \
  up -d --build backend frontend portal worker beat

echo "=== 3) Migrations ==="
sleep 8
if ! docker compose -p orbiteus exec -T backend alembic upgrade head; then
  echo "WARN: alembic upgrade failed — if CRM lists return 500, run: ./scripts/vm-repair-alembic-crm.sh"
  exit 1
fi
# Sanity: alembic at head but zero CRM tables = stamped DB; repair script required.
CRM_COUNT="$(docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';" | tr -d '[:space:]')"
if [ "${CRM_COUNT:-0}" = "0" ]; then
  echo "WARN: no crm_* tables — running repair_missing_tables.py"
  docker compose -p orbiteus exec -T backend sh -c "cd /app && python scripts/repair_missing_tables.py"
  CRM_COUNT="$(docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -tAc \
    "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';" | tr -d '[:space:]')"
  if [ "${CRM_COUNT:-0}" = "0" ]; then
    echo "ERROR: CRM tables still missing after repair"
    exit 1
  fi
  docker compose -p orbiteus restart backend worker beat
fi

echo "=== 4) Shipping + CRM + WMS unit smoke ==="
docker compose -p orbiteus exec -T backend python -m pytest \
  tests/test_shipping_compose_preview.py \
  tests/test_shipping_dispatch_workspace.py \
  tests/test_shipping_carrier_matrix.py \
  tests/test_dpd_native.py \
  tests/test_ifs_outbox_dispatch.py \
  tests/test_ifs_webhook_route.py \
  tests/test_ifs_cf_parser.py \
  tests/test_ifs_webhook_integration.py \
  tests/test_crm_scoring.py \
  tests/test_crm_forecast.py \
  tests/test_inventory_foundation.py \
  tests/test_inventory_location_tree.py \
  -q --tb=line 2>/dev/null || true

echo "=== DONE ==="
echo "Admin:  http://$(hostname -I | awk '{print $1}'):3020"
echo "API:    http://$(hostname -I | awk '{print $1}'):8020"
echo "Portal: http://$(hostname -I | awk '{print $1}'):3021"
echo "Login:  admin@example.com / admin1234 (after seed)"
