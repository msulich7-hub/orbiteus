"""Integration: IFS webhook ingest uses system context + queue upsert (SQLite/Postgres)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.shipping.controller.services import ingest_ifs_webhook

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_ingest_ifs_webhook_upserts_queue_row() -> None:
    raw = json.loads((FIXTURES / "ifs_shipment_webhook.json").read_text(encoding="utf-8"))
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    ctx = MagicMock()
    ctx.tenant_id = tenant_id
    ctx.actor = "system"

    row = MagicMock()
    row.ifs_shipment_id = "900123"
    row.ifs_sid = "TEST"
    row.state = "queued"
    row.tenant_id = tenant_id

    repo = MagicMock()
    repo.upsert_from_event = AsyncMock(return_value=row)

    with (
        patch(
            "modules.shipping.controller.services.system_tenant_context",
            new_callable=AsyncMock,
            return_value=ctx,
        ),
        patch(
            "modules.shipping.controller.services.IfsQueueRepository",
            return_value=repo,
        ),
        patch(
            "modules.shipping.controller.services.get_carrier_settings",
        ) as mock_cfg,
    ):
        mock_cfg.return_value.ifs_auto_dispatch = False
        result = await ingest_ifs_webhook(session, raw, ifs_sid="TEST")

    repo.upsert_from_event.assert_awaited_once()
    assert result.ifs_shipment_id == "900123"
    repo.mark_state.assert_not_called()
