"""Inventory repositories — BaseRepository + RBAC + audit."""

from __future__ import annotations

import uuid
from typing import Any

from orbiteus_core.exceptions import ValidationError
from orbiteus_core.repository import BaseRepository

from modules.inventory.controller.location_services import (
    assert_barcode_unique_in_warehouse,
    assert_parent_in_warehouse,
)
from modules.inventory.model.domain import Location, Product, Quant, Warehouse


class WarehouseRepository(BaseRepository[Warehouse]):
    model_name = "inventory.warehouse"
    domain_class = Warehouse

    @property
    def table(self):
        from modules.inventory.model.mapping import warehouses_table

        return warehouses_table


class LocationRepository(BaseRepository[Location]):
    model_name = "inventory.location"
    domain_class = Location

    @property
    def table(self):
        from modules.inventory.model.mapping import locations_table

        return locations_table

    async def _before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        data = await super()._before_create(data)
        await self._validate_location_fields(data)
        return data

    async def _before_write(self, obj: Location, data: dict[str, Any]) -> dict[str, Any]:
        data = await super()._before_write(obj, data)
        merged = {
            "warehouse_id": data.get("warehouse_id", obj.warehouse_id),
            "parent_id": data.get("parent_id", obj.parent_id),
            "barcode": data.get("barcode", obj.barcode),
        }
        await self._validate_location_fields(
            merged,
            exclude_id=obj.id,
        )
        return data

    async def _validate_location_fields(
        self,
        data: dict[str, Any],
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        warehouse_id = data.get("warehouse_id")
        if warehouse_id is None:
            raise ValidationError("warehouse_id is required")

        parent_id = data.get("parent_id")
        await assert_parent_in_warehouse(
            self.session,
            self.ctx,
            warehouse_id=warehouse_id,
            parent_id=parent_id,
        )

        barcode = (data.get("barcode") or "").strip()
        if not barcode:
            code = (data.get("code") or "").strip()
            if code:
                data["barcode"] = code
                barcode = code

        if barcode:
            await assert_barcode_unique_in_warehouse(
                self.session,
                self.ctx,
                warehouse_id=warehouse_id,
                barcode=barcode,
                exclude_id=exclude_id,
            )


class ProductRepository(BaseRepository[Product]):
    model_name = "inventory.product"
    domain_class = Product

    @property
    def table(self):
        from modules.inventory.model.mapping import products_table

        return products_table


class QuantRepository(BaseRepository[Quant]):
    model_name = "inventory.quant"
    domain_class = Quant

    @property
    def table(self):
        from modules.inventory.model.mapping import quants_table

        return quants_table
