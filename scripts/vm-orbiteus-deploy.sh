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

echo "=== 3) Migrations (inline on backend start; verify) ==="
sleep 8
docker compose -p orbiteus exec -T backend alembic upgrade head 2>/dev/null || true

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
  -q --tb=line 2>/dev/null || true

echo "=== DONE ==="
echo "Admin:  http://$(hostname -I | awk '{print $1}'):3020"
echo "API:    http://$(hostname -I | awk '{print $1}'):8020"
echo "Portal: http://$(hostname -I | awk '{print $1}'):3021"
echo "Login:  admin@example.com / admin1234 (after seed)"
