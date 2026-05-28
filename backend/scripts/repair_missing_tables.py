"""Create any SQLAlchemy metadata tables missing from Postgres (idempotent).

Use on VM when alembic_version is at head but product tables (crm_*, etc.)
were never created. Does NOT drop or alter existing tables.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import inspect

from api import app  # noqa: F401 — load mappings via registry bootstrap
from orbiteus_core.db import engine, metadata


async def main() -> None:
    created: list[str] = []
    skipped: list[str] = []

    async with engine.begin() as conn:

        def _sync(connection) -> None:
            nonlocal created, skipped
            existing = set(inspect(connection).get_table_names())
            for table in metadata.sorted_tables:
                if table.name in existing:
                    skipped.append(table.name)
                    continue
                table.create(connection, checkfirst=True)
                created.append(table.name)

        await conn.run_sync(_sync)

    print(f"created={len(created)} skipped={len(skipped)}")
    for name in created:
        if name.startswith(("crm_", "inventory_", "shipping_")):
            print(f"  + {name}")


if __name__ == "__main__":
    asyncio.run(main())
