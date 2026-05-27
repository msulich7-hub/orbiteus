"""Geodis native Python adapter package."""

from modules.shipping.lib.adapters.geodis.client import GeodisCarrier
from modules.shipping.lib.adapters.geodis.pickup_date import next_geodis_suggested_pickup_date

__all__ = ["GeodisCarrier", "next_geodis_suggested_pickup_date"]
