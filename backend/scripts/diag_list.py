"""One-off diagnostic: list CRM organization (run in backend container)."""
from __future__ import annotations

import asyncio
import traceback

from httpx import ASGITransport, AsyncClient

from api import app
from tests.conftest import register_user


async def main() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await register_user(client)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        for path, params in [
            ("/api/crm/organization", {"limit": 5}),
            ("/api/crm/organization", {"limit": 5, "expand": "assigned_user_id"}),
            ("/api/base/ui-config", {}),
        ]:
            try:
                r = await client.get(path, params=params, headers=headers)
                print(path, params, "->", r.status_code, r.text[:400])
            except Exception:
                print(path, "EXCEPTION")
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
