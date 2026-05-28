#!/usr/bin/env bash
# Repair VM DB when alembic is at head but CRM/product tables are missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Alembic version ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c "SELECT version_num FROM alembic_version;"

echo "=== CRM tables (before) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c \
  "SELECT tablename FROM pg_tables WHERE tablename LIKE 'crm_%' ORDER BY 1;"

echo "=== create_all via backend metadata ==="
docker compose -p orbiteus exec -T backend python -c "
import asyncio
from api import app  # noqa: F401 — bootstrap mappings
from orbiteus_core.db import engine, metadata

async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    names = sorted(t.name for t in metadata.sorted_tables if t.name.startswith('crm_'))
    print('crm tables in metadata:', len(names))
    for n in names[:5]:
        print(' ', n)

asyncio.run(main())
"

echo "=== CRM tables (after) ==="
docker compose -p orbiteus exec -T postgres psql -U orbiteus -d orbiteus -c \
  "SELECT tablename FROM pg_tables WHERE tablename LIKE 'crm_%' ORDER BY 1;"

echo "=== Restart backend ==="
docker compose -p orbiteus restart backend

echo "=== DONE ==="
