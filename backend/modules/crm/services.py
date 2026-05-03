"""Legacy re-export — see modules.crm.controller.services for the canonical
implementation. Kept for backward compatibility with existing imports.
"""
from __future__ import annotations

from modules.crm.controller.services import move_opportunity_to_stage

__all__ = ["move_opportunity_to_stage"]
