# Module `inventory` — WMS program (spec foundation)

> **Layer:** product  
> **Status:** specification only — **no runtime code** until Wave 1 tasks  
> **Authority:** Ekspert B (audyt WMS) — [`../../shipping/docs/wms-audit.md`](../../shipping/docs/wms-audit.md)  
> **Governance:** [ADR-0018](../../../docs/adr/0018-shipping-pack-station-not-wms.md) Track B

Orbiteus **nie jest WMS dziś** (audyt: **2,4/10**). Ten moduł definiuje program budowy **mid-market WMS**
na silniku Orbiteus, bez mieszania ze `shipping` (etykiety / TMS).

## Read order

| # | Document | Purpose |
|---|----------|---------|
| 1 | [`spec.md`](./spec.md) | Contract **WMS-001..015**, models, API, events, target scores |
| 2 | [`tasks.md`](./tasks.md) | Session tasks **WMS-T01..T30** |
| 3 | [`../../shipping/docs/wms-audit.md`](../../shipping/docs/wms-audit.md) | Baseline gaps (Expert B table) |
| 4 | [`../../../docs/adr/0018-shipping-pack-station-not-wms.md`](../../../docs/adr/0018-shipping-pack-station-not-wms.md) | Boundaries vs `shipping` |

## Relationship to other modules

| Module | Role |
|--------|------|
| `shipping` | Pack station, carrier labels, IFS dispatch — **nie** stock |
| `crm` | Sales — demand may create reservation source later |
| `orders` (planned) | Outbound order header — UUID FK only |
| `inventory` | **Stock, locations, moves, pick, receive** |

## Target (Expert B)

| Milestone | Audyt WMS (weighted) | When |
|-----------|----------------------|------|
| v0.1 MVP | **4/10** | Location + quant + manual move |
| v0.5 | **6/10** | + pick list + receiving |
| v1.0 | **7,5/10** | + waves, cycle count, shipping handoff |
| v2.0 | **8+/10** | + lot/serial, labor, RF hardening |

Pack station remains in `shipping` (target **8/10** pack score — Expert A).

## Agent prompt

```text
Implement WMS-Txx from backend/modules/inventory/docs/tasks.md.
Read spec.md and Expert B audit first. No cross-module imports — UUID FKs to orders/shipping only.
Follow docs/pre-prompt.md and docs/03-modules.md.
```
