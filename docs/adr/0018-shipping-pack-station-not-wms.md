# ADR-0018: Shipping is a pack station / TMS slice — not a WMS

- **Status:** Accepted
- **Date:** 2026-05-27
- **Deciders:** Product + engineering (shipping / logistics stream)
- **Context tags:** shipping, product-positioning, wms, logistics, admin-ui

## Context

Orbiteus gained a **`shipping`** product module: IFS webhook ingress, carrier label
adapters (DPD, DSV/Schenker, Geodis), IFS inbox, AUTO dispatch, and a multi-waybill
dispatch kiosk (v0.3).

Stakeholders asked whether this stack qualifies as a **modern WMS**. An external-style
audit ([`backend/modules/shipping/docs/wms-audit.md`](../../backend/modules/shipping/docs/wms-audit.md))
compared Orbiteus to a tier-1 WMS reference model:

| Perspective | Score |
|-------------|-------|
| Full WMS | **2.4 / 10** |
| Pack station / outbound labels | **6.8 / 10** (target **~8** with scan + ZPL + E2E) |
| Engine as WMS foundation | **7.5 / 10** |

Forces:

- MDM-style operations need **fast labels from IFS**, not full warehouse stock control.
- Building tier-1 WMS (bins, pick, putaway, cycle count) is a **multi-module program**,
  not an extension of label dispatch.
- Marketing Orbiteus as “WMS” would mis-set customer expectations and fail operational
  acceptance on the warehouse floor.
- The engine (RBAC, audit, outbox, multitenancy) is suitable to host future inventory
  modules **without** renaming `shipping` into WMS.

## Decision

1. **Product name (public):** Orbiteus **Shipping Dispatch** / **Outbound Labels** /
   **Pack Station** — never “Orbiteus WMS” unless a separate `inventory` program ships.
2. **Module `shipping` scope:** ERP/TMS outbound slice only — IFS ingress, handling
   units, 1–5 waybills per shipment, carrier APIs via Celery outbox, operator kiosk.
3. **WMS capabilities** (stock locations, reservations, pick waves, receiving, cycle
   count) require a **future `inventory` (or `wms`) module** with its own ADR and
   domain models — not bolted onto `shipping.shipment`.
4. **Integration pattern:** Orbiteus may act as the **label and dispatch layer** beside
   a customer’s existing WMS/ERP; UUID FKs only, no cross-module imports.
5. **Roadmap priority:** Finish **pack station to ~8/10** before any WMS program (see
   Roadmap below).

## Roadmap

### Track A — Pack station (module `shipping`) — **now**

Goal: **~8/10** vs tier-1 pack station reference (not vs full WMS).

| Phase | Deliverable | Success signal |
|-------|-------------|----------------|
| A1 (v0.3) | IFS inbox, AUTO, kiosk DnD, per-waybill outbox | Merged PR, migration applied |
| A2 | Scan-first UI (shipment / order / HU barcode) | Operator never types IDs |
| A3 | ZPL + production print path | Zebra on hall |
| A4 | Playwright E2E (AUTO + 3-waybill) | CI gate |
| A5 | Retry / dead-letter UI for failed waybills | Ops recovers without DB |
| A6 | Optional `orders` module stub (read-only header for `order_id` FK) | UI shows customer order |

Stop Track A when audit pack-station score ≥ **8** or diminishing returns.

### Track B — WMS program (module `inventory`) — **spec ready, code later**

**Authority:** Expert B audit — [`backend/modules/shipping/docs/wms-audit.md`](../../backend/modules/shipping/docs/wms-audit.md).

**Specification (no runtime until charter sign-off):**

| Doc | Path |
|-----|------|
| Index | [`backend/modules/inventory/docs/README.md`](../../backend/modules/inventory/docs/README.md) |
| Contract WMS-001..015 | [`backend/modules/inventory/docs/spec.md`](../../backend/modules/inventory/docs/spec.md) |
| Tasks WMS-T01..T27 | [`backend/modules/inventory/docs/tasks.md`](../../backend/modules/inventory/docs/tasks.md) |

Do **not** start implementation until product signs a WMS charter (or explicit waiver). Minimum sequence:

| Phase | Module / artifact | Spec / task | Depends on |
|-------|-------------------|-------------|------------|
| B0 | Charter + boundaries | WMS-T00 | This ADR |
| B1 | `inventory.location`, `inventory.quant` | WMS-001..003, WMS-T01..T05 | base |
| B2 | `inventory.move`, reservations | WMS-004..005, WMS-T03, T06..T07 | B1 |
| B3 | Pick waves + pick lists | WMS-008..009, WMS-T11..T13 | B2 |
| B4 | Receiving / putaway | WMS-005..007, WMS-T08..T10 | B1 |
| B5 | WMS ↔ shipping handoff | WMS-012, WMS-T15..T16, **SHP-T30** | A2+, B3 |

Estimated invasiveness: **new product line**, not a shipping sprint.

### Track C — Integrate-only (customer has WMS)

If the customer already runs a WMS:

- Orbiteus **shipping** consumes “ready to ship” events (webhook/API).
- No Track B in Orbiteus for that deployment.
- Document contract in module `shipping` spec (ingress only).

## Consequences

**Positive**

- Clear positioning for sales, ops, and implementers.
- Shipping team optimizes kiosk and carriers without scope creep into pick paths.
- Audit scores become actionable (pack station KPIs, not fake WMS checklist).

**Negative**

- Customers wanting one-vendor WMS will not find it in `shipping` alone.
- Competing RFPs that mandate full WMS require Track B or partner integration.

**Neutral**

- CRM remains the canonical product example; shipping is a second product module.
- Engine investment (outbox, RBAC) benefits both tracks.

## Alternatives considered

| Alternative | Rejection |
|-------------|-----------|
| Rename `shipping` → `wms` | Misleading; module has no stock or pick |
| Expand `shipping` with bins and pick lists | Violates module boundaries; unmaintainable monolith |
| Buy/partner WMS and drop shipping | Loses PL carrier native + IFS CF parser investment |
| Claim “WMS-ready” on engine only | True for platform, false for shipped modules today |

## References

- [`backend/modules/shipping/docs/wms-audit.md`](../../backend/modules/shipping/docs/wms-audit.md) — hard scores (Expert A + B)
- [`backend/modules/inventory/docs/spec.md`](../../backend/modules/inventory/docs/spec.md) — Track B WMS contract (Expert B baseline)
- [`backend/modules/inventory/docs/tasks.md`](../../backend/modules/inventory/docs/tasks.md) — Track B implementation tasks
- [`backend/modules/shipping/docs/spec.md`](../../backend/modules/shipping/docs/spec.md) — module contract
- [`backend/modules/shipping/docs/README.md`](../../backend/modules/shipping/docs/README.md) — doc index
- [ADR-0001](./0001-engine-vs-framework.md) — engine vs product positioning
- [ADR-0010](./0010-eventbus-postgres-outbox.md) — label dispatch async model
