"""Shipping repositories — BaseRepository + RBAC + audit."""

from __future__ import annotations

import json

from orbiteus_core.exceptions import NotFound
from orbiteus_core.repository import BaseRepository

from modules.shipping.model.domain import IfsShipmentQueue, Shipment


class ShipmentRepository(BaseRepository[Shipment]):
    model_name = "shipping.shipment"
    domain_class = Shipment

    @property
    def table(self):
        from modules.shipping.model.mapping import shipments_table

        return shipments_table


class IfsQueueRepository(BaseRepository[IfsShipmentQueue]):
    """IFS inbound queue — tenant-scoped, audited via BaseRepository."""

    model_name = "shipping.ifs_queue"
    domain_class = IfsShipmentQueue

    @property
    def table(self):
        from modules.shipping.model.mapping import ifs_shipment_queue_table

        return ifs_shipment_queue_table

    async def get_by_ifs_shipment_id(self, ifs_shipment_id: str) -> IfsShipmentQueue:
        rows, total = await self.search([("ifs_shipment_id", "=", ifs_shipment_id)], limit=1)
        if total < 1 or not rows:
            raise NotFound(self.model_name, ifs_shipment_id)
        return rows[0]

    async def upsert_from_event(
        self,
        *,
        ifs_shipment_id: str,
        ifs_sid: str,
        objstate: str,
        payload: dict,
    ) -> IfsShipmentQueue:
        payload_json = json.dumps(payload, ensure_ascii=False)
        rows, total = await self.search([("ifs_shipment_id", "=", ifs_shipment_id)], limit=1)
        data = {
            "ifs_shipment_id": ifs_shipment_id,
            "ifs_sid": ifs_sid or "",
            "objstate": objstate or "",
            "payload_json": payload_json,
            "state": "queued",
            "error_message": "",
        }
        if total > 0:
            return await self.update(rows[0].id, data)
        return await self.create(data)

    async def mark_state(
        self,
        ifs_shipment_id: str,
        *,
        state: str,
        error_message: str = "",
    ) -> IfsShipmentQueue:
        row = await self.get_by_ifs_shipment_id(ifs_shipment_id)
        return await self.update(
            row.id,
            {"state": state, "error_message": error_message},
        )
