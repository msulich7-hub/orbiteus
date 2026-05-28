# Module `inventory` (WMS) — implementation tasks

> **Spec:** [`spec.md`](./spec.md) (**WMS-001..015**)  
> **Authority:** Ekspert B — [`../shipping/docs/wms-audit.md`](../shipping/docs/wms-audit.md)  
> **Governance:** [ADR-0018](../../../docs/adr/0018-shipping-pack-station-not-wms.md) Track B  

**Prerequisite:** Product **WMS charter** signed (ADR-0018). **Do not start** until `shipping` Track A ≥ 8/10 pack score **or** explicit waiver.

One task block = one agent session / PR. Branch: `cursor/wms-<short-name>-0223`.

---

## Wave 0 — Charter (documentation)

### WMS-T00 — Charter + module skeleton

**Depends on:** —  
**Status:** done (spec + tasks)  
**Goal:** This document set; optional empty `manifest.py` stub.

**Deliverables:**

- [x] `docs/spec.md`, `docs/tasks.md`, `docs/README.md`
- [x] Product sign-off recorded in ADR-0018 (Track B started 2026-05-28, MDM NT)
- [x] Update `wms-audit.md` link to this spec

---

## Wave 1 — Foundation (Expert B: lokalizacje + stan → target 4/10)

> Closes audit rows: **Lokalizacje 1→8**, **Stan 1→8** (partial).

### WMS-T01 — Domain + migration (WMS-001..003)

**Depends on:** WMS-T00  
**Status:** done

**Goal:** `warehouse`, `location`, `product`, `quant`; Alembic; RBAC.

**Acceptance:** Tables exist; auto-CRUD registers; pytest domain round-trip.

---

### WMS-T02 — Location tree API (WMS-001)

**Depends on:** WMS-T01  
**Status:** todo

**Goal:** `GET /api/inventory/locations/tree`; barcode unique per warehouse.

**Acceptance:** 3-level tree JSON; create bin via POST.

---

### WMS-T03 — Stock move ledger (WMS-004)

**Depends on:** WMS-T01  
**Status:** todo

**Goal:** `inventory.move` confirm/cancel; updates `quant` atomically.

**Acceptance:** Transfer A→B; quant decrements/increments; audit entries.

---

### WMS-T04 — Admin UI: location tree + quant list

**Depends on:** WMS-T02  
**Status:** todo

**Goal:** XML views + optional `InvLocationTree.tsx` if renderer insufficient.

**Acceptance:** Manager sees bins and on-hand per SKU.

---

### WMS-T05 — Tests + audit score v0.1

**Depends on:** WMS-T03  
**Status:** todo

**Goal:** `test_inventory_moves.py`, `test_inventory_quant.py`; update audit appendix.

**Acceptance:** Re-score Expert B location+stock rows → ≥ **4/10** weighted.

---

## Wave 2 — Allocation (Expert B: rezerwacje)

### WMS-T06 — Reservations (WMS-005)

**Depends on:** WMS-T03  
**Status:** todo

**Goal:** Reserve qty; `reserved_quantity` on quant; release/consume.

**Acceptance:** Cannot pick more than available minus reserved.

---

### WMS-T07 — Link reservation to order UUID

**Depends on:** WMS-T06  
**Status:** todo

**Goal:** `order_id` FK on reservation (no orders module import).

**Acceptance:** API accepts order UUID from client.

---

## Wave 3 — Inbound (Expert B: przyjęcia + putaway → target 6/10)

### WMS-T08 — Receipt + ASN lines (WMS-006)

**Depends on:** WMS-T03  
**Status:** todo

**Goal:** Receipt header/lines; receive scan increases staging quant.

---

### WMS-T09 — Putaway tasks (WMS-007)

**Depends on:** WMS-T08  
**Status:** todo

**Goal:** Putaway from staging → bin; move type `transfer`.

**Acceptance:** Full inbound path staging → pickable bin.

---

### WMS-T10 — RF receive/putaway confirm API

**Depends on:** WMS-T09  
**Status:** todo

**Goal:** Scan envelope on receive and putaway confirm.

---

## Wave 4 — Outbound pick (Expert B: kompletacja → target 6–7/10)

### WMS-T11 — Pick wave + pick list (WMS-008)

**Depends on:** WMS-T06  
**Status:** todo

**Goal:** Create wave from reservations; release generates pick lines.

---

### WMS-T12 — Pick confirm scan (WMS-009)

**Depends on:** WMS-T11  
**Status:** todo

**Goal:** `POST /pick-lines/{id}/confirm-scan`; move type `pick`.

**Acceptance:** Wrong bin barcode → 409; golden scan OK.

---

### WMS-T13 — RF pick UI shell

**Depends on:** WMS-T12  
**Status:** todo

**Goal:** `admin-ui/src/components/inventory/InvRfPickSession.tsx` — scan-first.

---

## Wave 5 — Count + handoff + KPI (target 7,5/10)

### WMS-T14 — Cycle count (WMS-010)

**Depends on:** WMS-T03  
**Status:** todo

---

### WMS-T15 — Ready-to-ship + event (WMS-012)

**Depends on:** WMS-T12  
**Status:** todo

**Goal:** `inventory.ready_to_ship.created`; payload schema `ready_to_ship/v1`.

**Acceptance:** Event received by test subscriber; no import of shipping code.

---

### WMS-T16 — Shipping handoff adapter (in `shipping` module)

**Depends on:** WMS-T15, shipping Track A2+  
**Status:** todo  
**Owner:** shipping team

**Goal:** Handler creates dispatch draft or queue row from event (UUID FK).

**Note:** Task lives in `shipping/docs/tasks.md` as **SHP-T30** (add when executing).

---

### WMS-T17 — WMS KPI endpoints (WMS-013)

**Depends on:** WMS-T11  
**Status:** todo

---

### WMS-T18 — Re-audit Expert B (v1.0)

**Depends on:** WMS-T14, WMS-T15, WMS-T17  
**Status:** todo

**Goal:** Update `wms-audit.md` scores; target **7,5/10** weighted WMS.

---

## Wave 6 — Traceability (Expert B: lot/serial)

### WMS-T19 — Lot tracking (WMS-011)

**Depends on:** WMS-T03  
**Status:** todo

---

### WMS-T20 — Serial tracking (WMS-011)

**Depends on:** WMS-T19  
**Status:** todo

---

## Wave 7 — Phase 2 (Expert B: labor + yard)

### WMS-T21 — Labor task queue skeleton (WMS-014)

**Depends on:** WMS-T11  
**Status:** todo

---

### WMS-T22 — Dock appointment skeleton (WMS-015)

**Depends on:** WMS-T01  
**Status:** todo

---

## Cross-cutting

### WMS-T25 — `manifest.py` + bootstrap + menus

**Depends on:** WMS-T01  
**Status:** todo

---

### WMS-T26 — `ai.py` read-only assistant

**Depends on:** WMS-T11  
**Status:** todo

---

### WMS-T27 — Outbox consumers for KPI refresh

**Depends on:** WMS-T17  
**Status:** todo

---

## Parallel windows (recommended)

```
Window WMS-1: T01 → T02 → T03 → T05        (foundation)
Window WMS-2: T06 → T07                     (allocation)
Window WMS-3: T08 → T09 → T10                 (inbound)
Window WMS-4: T11 → T12 → T13                 (pick)
Window WMS-5: T14 → T15 → T17 → T18           (v1.0 close)
Shipping sync: T16 (SHP-T30) after T15
```

---

## Mapping: Expert B audit row → task

| Audyt B obszar | Tasks |
|----------------|-------|
| Lokalizacje / bin | T01, T02, T04 |
| Stan / rezerwacje | T03, T06, T07 |
| Przyjęcia / putaway | T08, T09, T10 |
| Kompletacja / fale | T11, T12, T13 |
| Inwentaryzacja | T14 |
| Lot / serial | T19, T20 |
| Integracja outbound | T15, T16 |
| Analityka | T17, T18 |
| Labor | T21 |
| Yard | T22 |

---

## Copy-paste prompt

```text
Implement WMS-Txx from backend/modules/inventory/docs/tasks.md.
Authority: Expert B audit in backend/modules/shipping/docs/wms-audit.md.
Read spec.md first. No cross-module imports. UUID FKs only to orders/shipping.
Tests required per docs/20-testing.md.
```
