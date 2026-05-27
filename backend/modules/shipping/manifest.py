"""Shipping module manifest — spedycje / etykiety (DPD, DSV, Geodis, InPost).

Settings env var names mirror mercato/modules/mercato-shipping-hub/.env.example
and open-mercato/packages/carrier-*/lib/preset.ts — do not invent new names.
"""

MANIFEST = {
    "name": "Shipping",
    "version": "0.1.0",
    "depends_on": ["base", "auth"],
    "layer": "product",
    "description": "Carrier label dispatch, routing, shipment tracking.",
    "models": [
        "shipping.shipment",
        "shipping.ifs_queue",
    ],
    "category": "Logistics",
    "auto_install": False,
    "data": [
        "security/access.yaml",
        "view/shipment_views.xml",
        "view/ifs_queue_views.xml",
    ],
    "menus": [
        {"name": "Logistyka", "sequence": 30, "icon": "truck"},
        {
            "name": "Przesyłki",
            "parent": "Logistyka",
            "sequence": 10,
            "model": "shipping.shipment",
        },
        {
            "name": "Kolejka IFS",
            "parent": "Logistyka",
            "sequence": 20,
            "model": "shipping.ifs_queue",
        },
    ],
    "view_config": "modules.shipping.view.config",
    "bootstrap": "modules.shipping.bootstrap",
}
