#!/usr/bin/env bash
# Emergency VM fix: stamp alembic head, create missing tables, restart API.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -p orbiteus -f docker-compose.yml -f docker-compose.vm-ports.yml)

"${COMPOSE[@]}" up -d postgres redis
sleep 2

echo "=== Stamp alembic head (SQL) ==="
"${COMPOSE[@]}" exec -T postgres psql -U orbiteus -d orbiteus <<'SQL'
UPDATE alembic_version SET version_num = 'o5i6j7k8l016';
SQL

echo "=== CRM count before repair ==="
"${COMPOSE[@]}" exec -T postgres psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Repair missing tables ==="
"${COMPOSE[@]}" run --rm --no-deps --entrypoint sh backend \
  -c "cd /app && python scripts/repair_missing_tables.py"

echo "=== CRM count after repair ==="
"${COMPOSE[@]}" exec -T postgres psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE tablename LIKE 'crm_%';"

echo "=== Start stack ==="
"${COMPOSE[@]}" up -d --build backend frontend portal worker beat

sleep 10
echo "=== Backend health ==="
curl -sf http://127.0.0.1:8020/api/health || echo "health check failed"

echo "=== DONE ==="
