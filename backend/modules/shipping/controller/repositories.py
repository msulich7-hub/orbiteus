"""Shipping repositories — BaseRepository + RBAC + audit."""

from __future__ import annotations

import json
import uuid

from orbiteus_core.exceptions import NotFound
from orbiteus_core.repository import BaseRepository

from modules.shipping.model.domain import (
    Dispatch,
    HandlingUnit,
    IfsShipmentQueue,
    Shipment,
    Waybill,
)


class ShipmentRepository(BaseRepository[Shipment]):
    model_name = "shipping.shipment"
    domain_class = Shipment

    @property
    def table(self):
        from modules.shipping.model.mapping import shipments_table

        return shipments_table


class IfsQueueRepository(BaseRepository[IfsShipmentQueue]):
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
            existing = rows[0]
            if existing.dispatch_id:
                data.pop("state", None)
            return await self.update(rows[0].id, data)
        return await self.create(data)

    async def mark_state(
        self,
        ifs_shipment_id: str,
        *,
        state: str,
        error_message: str = "",
        dispatch_id: uuid.UUID | None = None,
    ) -> IfsShipmentQueue:
        row = await self.get_by_ifs_shipment_id(ifs_shipment_id)
        patch: dict = {"state": state, "error_message": error_message}
        if dispatch_id is not None:
            patch["dispatch_id"] = dispatch_id
        return await self.update(row.id, patch)

    async def link_dispatch(
        self,
        ifs_shipment_id: str,
        dispatch_id: uuid.UUID,
        *,
        state: str = "claimed",
    ) -> IfsShipmentQueue:
        return await self.mark_state(
            ifs_shipment_id,
            state=state,
            dispatch_id=dispatch_id,
        )


class DispatchRepository(BaseRepository[Dispatch]):
    model_name = "shipping.dispatch"
    domain_class = Dispatch

    @property
    def table(self):
        from modules.shipping.model.mapping import dispatch_table

        return dispatch_table

    async def get_for_ifs_shipment(self, ifs_shipment_id: str) -> Dispatch | None:
        rows, total = await self.search([("ifs_shipment_id", "=", ifs_shipment_id)], limit=1)
        if total < 1 or not rows:
            return None
        return rows[0]


class HandlingUnitRepository(BaseRepository[HandlingUnit]):
    model_name = "shipping.handling_unit"
    domain_class = HandlingUnit

    @property
    def table(self):
        from modules.shipping.model.mapping import handling_units_table

        return handling_units_table

    async def list_for_dispatch(self, dispatch_id: uuid.UUID) -> list[HandlingUnit]:
        rows, _ = await self.search(
            [("dispatch_id", "=", dispatch_id)],
            limit=100,
            order_by="sequence",
            order_dir="asc",
        )
        return list(rows)


class WaybillRepository(BaseRepository[Waybill]):
    model_name = "shipping.waybill"
    domain_class = Waybill

    @property
    def table(self):
        from modules.shipping.model.mapping import waybills_table

        return waybills_table

    async def list_for_dispatch(self, dispatch_id: uuid.UUID) -> list[Waybill]:
        rows, _ = await self.search(
            [("dispatch_id", "=", dispatch_id)],
            limit=10,
            order_by="sequence",
            order_dir="asc",
        )
        return list(rows)

    async def get_by_dispatch_sequence(
        self,
        dispatch_id: uuid.UUID,
        sequence: int,
    ) -> Waybill | None:
        rows, total = await self.search(
            [("dispatch_id", "=", dispatch_id), ("sequence", "=", sequence)],
            limit=1,
        )
        if total < 1 or not rows:
            return None
        return rows[0]
