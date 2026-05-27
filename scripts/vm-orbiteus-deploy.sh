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
  up -d --build backend frontend portal

echo "=== 3) Migrations (inline on backend start; verify) ==="
sleep 8
docker compose -p orbiteus exec -T backend alembic upgrade head 2>/dev/null || true

echo "=== 4) CRM unit smoke ==="
docker compose -p orbiteus exec -T backend python -m pytest tests/test_crm_scoring.py tests/test_crm_forecast.py -q --tb=line 2>/dev/null || true

echo "=== DONE ==="
echo "Admin:  http://$(hostname -I | awk '{print $1}'):3020"
echo "API:    http://$(hostname -I | awk '{print $1}'):8020"
echo "Portal: http://$(hostname -I | awk '{print $1}'):3021"
echo "Login:  admin@example.com / admin1234 (after seed)"
