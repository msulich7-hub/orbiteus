"""Compose preview and AUTO dispatch eligibility (SHP-AUTO)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

from modules.shipping.controller.repositories import DispatchRepository, IfsQueueRepository
from modules.shipping.lib.carrier_settings import get_carrier_settings
from modules.shipping.lib.ifs_dispatch_profiles import resolve_ifs_dispatch_profile
from modules.shipping.lib.ifs_inbound_mapper import build_logistics_payload_from_ifs_webhook
from modules.shipping.lib.ifs_logistics_types import IfsLogisticsPayload
from modules.shipping.lib.ifs_packaging import is_pallet
from modules.shipping.lib.routing import resolve_carrier_for_shipment
from modules.shipping.model.domain import IfsShipmentQueue
from modules.shipping.model.schemas import (
    ComposePreviewResponse,
    PreviewHandlingUnit,
    SuggestedPlan,
    SuggestedWaybillPlan,
)

KIOSK_AUTO_ENABLED = "shipping.kiosk_auto_enabled"
KIOSK_AUTO_MAX_HU = "shipping.kiosk_auto_max_hu"
KIOSK_AUTO_MAX_WEIGHT_KG = "shipping.kiosk_auto_max_weight_kg"
KIOSK_AUTO_CONFIRM = "shipping.kiosk_auto_confirm"

DEFAULT_AUTO_MAX_HU = 1
DEFAULT_AUTO_MAX_WEIGHT_KG = 31.0


@dataclass
class KioskAutoConfig:
    auto_enabled: bool = True
    auto_max_hu: int = DEFAULT_AUTO_MAX_HU
    auto_max_weight_kg: float = DEFAULT_AUTO_MAX_WEIGHT_KG
    auto_confirm: bool = True


async def load_kiosk_auto_config(
    session: AsyncSession,
    ctx: RequestContext,
) -> KioskAutoConfig:
    from modules.base.controller.repositories import IrConfigParamRepository

    repo = IrConfigParamRepository(session, ctx)
    keys = (KIOSK_AUTO_ENABLED, KIOSK_AUTO_MAX_HU, KIOSK_AUTO_MAX_WEIGHT_KG, KIOSK_AUTO_CONFIRM)
    rows, _ = await repo.search([("key", "in", list(keys))], limit=10)
    by_key = {r.key: (r.value or "").strip() for r in rows}

    def _flag(key: str, default: bool = True) -> bool:
        raw = by_key.get(key, "")
        if not raw:
            return default
        return raw not in ("0", "false", "False", "no")

    max_hu_raw = by_key.get(KIOSK_AUTO_MAX_HU, str(DEFAULT_AUTO_MAX_HU))
    max_w_raw = by_key.get(KIOSK_AUTO_MAX_WEIGHT_KG, str(DEFAULT_AUTO_MAX_WEIGHT_KG))
    try:
        max_hu = int(max_hu_raw)
    except ValueError:
        max_hu = DEFAULT_AUTO_MAX_HU
    try:
        max_weight = float(max_w_raw)
    except ValueError:
        max_weight = DEFAULT_AUTO_MAX_WEIGHT_KG

    return KioskAutoConfig(
        auto_enabled=_flag(KIOSK_AUTO_ENABLED, True),
        auto_max_hu=max(1, max_hu),
        auto_max_weight_kg=max_weight,
        auto_confirm=_flag(KIOSK_AUTO_CONFIRM, True),
    )


def _parse_queue_payload(payload_json: str) -> IfsLogisticsPayload:
    data = json.loads(payload_json or "{}")
    return IfsLogisticsPayload.model_validate(data)


def preview_handling_units_from_payload(
    payload: IfsLogisticsPayload,
    *,
    persisted: list[tuple[uuid.UUID, int]] | None = None,
) -> list[PreviewHandlingUnit]:
    """Build preview HUs from logistics payload (ephemeral hu-N or DB ids)."""
    units: list[PreviewHandlingUnit] = []
    if payload.lines:
        for i, line in enumerate(payload.lines):
            if not line.pack_type:
                continue
            pack = line.pack_type
            unit_id = (
                str(persisted[i][0])
                if persisted and i < len(persisted)
                else f"hu-{i}"
            )
            units.append(
                PreviewHandlingUnit(
                    id=unit_id,
                    type="pallet" if is_pallet(pack) else "parcel",
                    pack_type=pack,
                    qty=max(1, int(line.qty or 1)),
                    weight_kg=float(line.weight_kg or 0),
                    length_cm=float(line.length_cm or 0),
                    width_cm=float(line.width_cm or 0),
                    height_cm=float(line.height_cm or 0),
                )
            )
        return units

    for i, hu in enumerate(payload.handling_units_summary or []):
        unit_id = (
            str(persisted[i][0])
            if persisted and i < len(persisted)
            else f"hu-{i}"
        )
        units.append(
            PreviewHandlingUnit(
                id=unit_id,
                type=hu.type,
                pack_type=hu.pack_type,
                qty=hu.qty,
                weight_kg=float(hu.weight_kg or 0),
                length_cm=float(hu.length_cm or 0),
                width_cm=float(hu.width_cm or 0),
                height_cm=float(hu.height_cm or 0),
            )
        )
    return units


def build_suggested_plan(
    units: list[PreviewHandlingUnit],
    *,
    recommended_carrier: str,
) -> SuggestedPlan:
    if not units:
        return SuggestedPlan(waybills=[])
    if len(units) == 1:
        u = units[0]
        return SuggestedPlan(
            waybills=[
                SuggestedWaybillPlan(
                    index=0,
                    carrier_code=recommended_carrier,
                    hu_ids=[u.id],
                    weight_kg=u.weight_kg,
                    is_pallet=u.type == "pallet",
                )
            ]
        )
    waybills: list[SuggestedWaybillPlan] = []
    for i, u in enumerate(units):
        waybills.append(
            SuggestedWaybillPlan(
                index=i,
                carrier_code=recommended_carrier,
                hu_ids=[u.id],
                weight_kg=u.weight_kg,
                is_pallet=u.type == "pallet",
            )
        )
    return SuggestedPlan(waybills=waybills)


def _unit_types_mixed(units: list[PreviewHandlingUnit]) -> bool:
    types = {u.type for u in units}
    return len(types) > 1


def _total_weight(units: list[PreviewHandlingUnit]) -> float:
    return sum((u.weight_kg or 0) * max(1, u.qty) for u in units)


def should_auto_dispatch(
    *,
    units: list[PreviewHandlingUnit],
    suggested_plan: SuggestedPlan,
    recommended_carrier: str,
    queue_state: str,
    auto_cfg: KioskAutoConfig,
    blocking_errors: list[str],
) -> bool:
    if blocking_errors:
        return False
    if not auto_cfg.auto_enabled:
        return False
    if queue_state not in ("queued",):
        return False
    if len(units) > auto_cfg.auto_max_hu:
        return False
    if _total_weight(units) > auto_cfg.auto_max_weight_kg:
        return False
    if len(suggested_plan.waybills) != 1:
        return False
    if _unit_types_mixed(units):
        return False
    cfg = get_carrier_settings()
    if not cfg.carrier_configured(recommended_carrier):
        return False
    return True


def blocking_errors_for_preview(
    *,
    queue: IfsShipmentQueue,
    units: list[PreviewHandlingUnit],
    recommended_carrier: str,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if queue.state not in ("queued", "claimed"):
        errors.append(f"Queue row state '{queue.state}' does not allow dispatch")
    if not units:
        errors.append("No handling units parsed from IFS payload")
    cfg = get_carrier_settings()
    if not cfg.carrier_configured(recommended_carrier):
        errors.append(f"Carrier {recommended_carrier} is not configured in environment")
    if _unit_types_mixed(units) and len(units) > 1:
        warnings.append("Mixed pallet and parcel units — use kiosk to split waybills")
    return errors, warnings


async def get_compose_preview(
    session: AsyncSession,
    ctx: RequestContext,
    ifs_shipment_id: str,
) -> ComposePreviewResponse:
    queue_repo = IfsQueueRepository(session, ctx)
    row = await queue_repo.get_by_ifs_shipment_id(ifs_shipment_id)
    payload = _parse_queue_payload(row.payload_json)

    dispatch_repo = DispatchRepository(session, ctx)
    dispatch = await dispatch_repo.get_for_ifs_shipment(ifs_shipment_id)
    persisted: list[tuple[uuid.UUID, int]] | None = None
    if dispatch:
        from modules.shipping.controller.repositories import HandlingUnitRepository

        hu_repo = HandlingUnitRepository(session, ctx)
        db_units = await hu_repo.list_for_dispatch(dispatch.id)
        persisted = [(u.id, u.sequence) for u in db_units]

    units = preview_handling_units_from_payload(payload, persisted=persisted)
    profile = resolve_ifs_dispatch_profile(payload.contract)
    first_pack = payload.lines[0].pack_type if payload.lines else None
    pallet_flag = is_pallet(first_pack) if first_pack else any(u.type == "pallet" for u in units)
    recommended = resolve_carrier_for_shipment(
        forward_agent_id=payload.forward_agent_id or None,
        weight_kg=float(payload.total_weight_kg or _total_weight(units)),
        is_pallet=pallet_flag,
    )
    plan = build_suggested_plan(units, recommended_carrier=recommended)
    errors, warnings = blocking_errors_for_preview(
        queue=row,
        units=units,
        recommended_carrier=recommended,
    )
    auto_cfg = await load_kiosk_auto_config(session, ctx)
    mode = (
        "auto"
        if should_auto_dispatch(
            units=units,
            suggested_plan=plan,
            recommended_carrier=recommended,
            queue_state=row.state,
            auto_cfg=auto_cfg,
            blocking_errors=errors,
        )
        else "kiosk"
    )

    dest = payload.destination
    recipient: dict[str, Any] | None = None
    if dest:
        recipient = {
            "company_name": dest.company_name,
            "city": dest.city,
            "postal_code": dest.postal_code,
            "country_code": dest.country_code,
        }

    return ComposePreviewResponse(
        ifs_shipment_id=ifs_shipment_id,
        queue_id=row.id,
        state=row.state,
        suggested_mode=mode,
        suggested_carrier=recommended,
        order_no=payload.order_no,
        order_id=None,
        recipient=recipient,
        handling_units=units,
        suggested_plan=plan,
        blocking_errors=errors,
        warnings=warnings,
    )


def payload_from_queue_row(row: IfsShipmentQueue) -> IfsLogisticsPayload:
    try:
        return _parse_queue_payload(row.payload_json)
    except Exception:
        raw = json.loads(row.payload_json or "{}")
        return build_logistics_payload_from_ifs_webhook(raw)
