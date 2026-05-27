"""Shipping Action declarations — Command Palette + navigation."""

from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="shipping.ifs_kiosk.open",
        label="Otwórz kiosk wysyłki IFS",
        keywords=["kiosk", "ifs", "dispatch", "etykieta"],
        description="Przejdź do skrzynki IFS (kiosk multi-waybill)",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/shipping/ifs_queue?view=inbox",
        requires_feature="shipping.ifs_queue.read",
        icon="layout-kanban",
    ),

    Action(
        id="shipping.shipment.list",
        label="Przesyłki",
        keywords=["shipping", "przesyłki", "logistyka", "waybill"],
        description="Lista przesyłek i waybilli",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/shipping/shipment",
        requires_feature="shipping.shipment.read",
        icon="truck",
    ),
    Action(
        id="shipping.ifs_queue.list",
        label="Kolejka IFS",
        keywords=["ifs", "oracle", "webhook", "kolejka", "secondary"],
        description="Przesyłki z IFS (ingress SECONDARY) oczekujące na dispatch",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/shipping/ifs_queue?view=inbox",
        requires_feature="shipping.ifs_queue.read",
        icon="inbox",
    ),
    Action(
        id="shipping.dispatch_ifs_queue",
        label="Dispatch etykiety z kolejki IFS",
        keywords=["ifs dispatch", "etykieta", "label", "kurier"],
        description="Kolejkuje utworzenie etykiety (outbox + Celery) dla wpisu IFS",
        category=ActionCategory.EXECUTE,
        target="api",
        target_url="/api/shipping/ifs/queue/{ifs_shipment_id}/dispatch",
        requires_feature="shipping.ifs_queue.write",
        icon="truck",
        parameters_schema={
            "type": "object",
            "properties": {
                "ifs_shipment_id": {"type": "string", "description": "IFS shipment id"},
                "order_id": {"type": "string", "description": "UUID orders.order"},
                "force_carrier": {"type": "string", "description": "Optional carrier override"},
            },
            "required": ["ifs_shipment_id", "order_id"],
        },
    ),
    Action(
        id="shipping.carriers.status",
        label="Status kurierów",
        keywords=["carriers", "dpd", "inpost", "dsv", "geodis"],
        description="Którzy kurierzy są skonfigurowani w env",
        category=ActionCategory.NAVIGATE,
        target="api",
        target_url="/api/shipping/carriers/status",
        requires_feature="shipping.shipment.read",
        icon="settings",
    ),
]
