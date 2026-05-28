"""Inventory (WMS) module manifest — WMS-001..003 foundation."""

MANIFEST = {
    "name": "Inventory",
    "version": "0.1.0",
    "depends_on": ["base", "auth"],
    "layer": "product",
    "description": "Warehouse locations, SKU master, on-hand quants (WMS Track B).",
    "models": [
        "inventory.warehouse",
        "inventory.location",
        "inventory.product",
        "inventory.quant",
    ],
    "category": "Warehouse",
    "auto_install": False,
    "data": [
        "security/access.yaml",
        "view/warehouse_views.xml",
        "view/location_views.xml",
        "view/product_views.xml",
        "view/quant_views.xml",
    ],
    "menus": [
        {"name": "Magazyn", "sequence": 35, "icon": "building-warehouse"},
        {
            "name": "Magazyny",
            "parent": "Magazyn",
            "sequence": 10,
            "model": "inventory.warehouse",
        },
        {
            "name": "Lokalizacje",
            "parent": "Magazyn",
            "sequence": 20,
            "model": "inventory.location",
        },
        {
            "name": "Produkty (SKU)",
            "parent": "Magazyn",
            "sequence": 30,
            "model": "inventory.product",
        },
        {
            "name": "Stany",
            "parent": "Magazyn",
            "sequence": 40,
            "model": "inventory.quant",
        },
    ],
    "view_config": "modules.inventory.view.config",
    "bootstrap": "modules.inventory.bootstrap",
}
