"""Inventory repositories — BaseRepository + RBAC + audit."""

from __future__ import annotations

from orbiteus_core.repository import BaseRepository

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
