# Shipping module — implementation tasks

> **Docs:** [`README.md`](./README.md) · [`spec.md`](./spec.md) · [`ux-kiosk.md`](./ux-kiosk.md) · [`carrier-labels.md`](./carrier-labels.md)  
> **Spec IDs:** SHP-001..012  
> **Use one task block per agent session / PR** unless noted as dependency chain.  
> Each task must end with **tests green** + **docs/spec.md** updated if behavior changed.

## How to run a session

1. Read [`docs/pre-prompt.md`](../../../../docs/pre-prompt.md) and [`spec.md`](./spec.md).
2. Pick the next task with `Status: todo` (respect **Depends on**).
3. Branch: `cursor/shipping-<short-name>-0223`.
4. Implement → pytest → commit → push → PR (draft).

---

## Wave A — Data model and services

### SHP-T01 — Domain and Alembic (SHP-001, SHP-002)

**Depends on:** —  
**Status:** done

**Goal:** Add `shipping.dispatch`, `shipping.waybill`, `shipping.handling_unit` dataclasses;
extend `IfsShipmentQueue.state` + `dispatch_id`; Alembic migration.

**Deliverables:**

- [ ] `model/domain.py` — new dataclasses + state tuples
- [ ] `model/mapping.py` + `model/schemas.py` — Read/Write Pydantic
- [ ] `migrations/versions/*_shipping_dispatch_kiosk.py`
- [ ] `security/access.yaml` — roles for new models
- [ ] `manifest.py` — register models in `MANIFEST["models"]`
- [ ] Unit test: tables register, schema round-trip

**Acceptance:** `pytest backend/tests/test_shipping_dispatch_workspace.py -q` (skeleton passes).

---

### SHP-T02 — Repositories and workspace service (SHP-003)

**Depends on:** SHP-T01  
**Status:** done

**Goal:** `DispatchRepository`, `WaybillRepository`, `HandlingUnitRepository`;
`start_dispatch_from_queue()`, `get_workspace()`, `assign_unit()`.

**Deliverables:**

- [ ] `controller/repositories.py`
- [ ] `controller/services.py` — parsing via `cf_handling_units_parser` + `coerce_ifs_payload`
- [ ] No carrier HTTP in services
- [ ] Tests: create dispatch from fixture `ifs_shipment_webhook.json`, 3+ handling units

**Acceptance:** `GET /dispatch/{id}/workspace` returns pool + empty waybill slot 1.

---

### SHP-T03 — Kiosk REST router (SHP-003, partial SHP-008)

**Depends on:** SHP-T02  
**Status:** done

**Goal:** Implement inbox + workspace + assign + waybill CRUD endpoints from spec API table.

**Deliverables:**

- [ ] `controller/router.py` — new routes (keep legacy routes)
- [ ] `controller/ifs_inbox.py` or inbox handlers in router
- [ ] OpenAPI tags `shipping-kiosk`
- [ ] Tests: `test_shipping_ifs_inbox.py`, `test_shipping_dispatch_workspace.py`

**Acceptance:** Postman/curl: queue → dispatch → assign unit → workspace JSON correct.

---

## Wave B — Admin UI

> **Note:** UI tasks **SHP-T04..T09** are superseded by **SHP-T13..T20** (see Wave E) and **SHP-T21..T24** (Wave F). Keep IDs for history; implement T13+.

### SHP-T04 — IFS inbox page (SHP-004, SHP-010)

**Depends on:** SHP-T03  
**Status:** done

**Goal:** CRM-style inbox: table of `queued` rows, badges, “Open kiosk” CTA.

**Deliverables:**

- [ ] `admin-ui/src/components/shipping/ShippingIfsInbox.tsx`
- [ ] Route `admin-ui/src/app/shipping/ifs-inbox/page.tsx`
- [ ] `manifest.py` menu: **IFS Inbox** → `/shipping/ifs-inbox`
- [ ] `proxy.ts` public paths unchanged
- [ ] Match patterns from `CrmRottingDeals` / prospect inbox

**Acceptance:** Login → inbox lists seeded queue rows; button navigates to kiosk URL.

---

### SHP-T05 — Kiosk shell and stepper (SHP-005)

**Depends on:** SHP-T04  
**Status:** done

**Goal:** Full-screen kiosk layout with steps Review → Compose → Submit → Print (shell only).

**Deliverables:**

- [ ] `ShippingDispatchKiosk.tsx` — fetch workspace, stepper state local + server `dispatch.state`
- [ ] Route `admin-ui/src/app/shipping/dispatch/[id]/kiosk/page.tsx`
- [ ] Step 1 Review: read-only IFS summary
- [ ] Mantine `Stepper`, large touch targets (kiosk / tablet)

**Acceptance:** Open kiosk from inbox; step 1 shows shipment id + recipient; no DnD yet.

---

### SHP-T06 — Drag-and-drop composition (SHP-006)

**Depends on:** SHP-T05  
**Status:** done

**Goal:** Pool + up to 5 waybill columns; @dnd-kit; `PUT assign-unit` on drop.

**Deliverables:**

- [ ] `ShippingUnitPool.tsx`, `ShippingWaybillColumn.tsx`
- [ ] Add/remove waybill slot (max 5)
- [ ] Optimistic UI + rollback on API error
- [ ] Vitest or Playwright smoke optional; API tests required

**Acceptance:** Drag `PAL_A` tile to waybill 2 → refresh workspace → unit.waybill_id set.

---

### SHP-T07 — Carrier tiles per waybill (SHP-007)

**Depends on:** SHP-T06  
**Status:** done

**Goal:** Per-column carrier selector; show configured/unconfigured from `/carriers/status`.

**Deliverables:**

- [ ] `ShippingCarrierChip.tsx` — DPD, DSV, GEODIS, INPOST, MOCK
- [ ] PATCH waybill `carrier_code` via auto-CRUD or dedicated PATCH endpoint
- [ ] Show `recommended_carrier_code` on dispatch header

**Acceptance:** Change waybill 1 to DPD, waybill 2 to DSV; workspace persists after reload.

---

## Wave C — Carrier execution and print

### SHP-T08 — Outbox per waybill (SHP-008)

**Depends on:** SHP-T02  
**Status:** done

**Goal:** `POST /waybill/{id}/submit` and `submit-all`; Celery `execute_dispatch_for_waybill`.

**Deliverables:**

- [ ] `enqueue` payload includes assigned units + carrier-specific pack types
- [ ] `tasks/shipping_tasks.py` — new executor; keep legacy `execute_dispatch_for_order`
- [ ] Waybill states: `queued` → `label_created` \| `failed`
- [ ] `test_shipping_waybill_outbox.py` with mocked adapter

**Acceptance:** Submit → 202 → worker → `label_created` + `tracking_number` on waybill.

---

### SHP-T09 — Submit and Print steps (SHP-009)

**Depends on:** SHP-T08, SHP-T07  
**Status:** done

**Goal:** Step 3 Submit (batch status); Step 4 Print (PDF download / new tab).

**Deliverables:**

- [ ] Submit step UI — per-waybill progress, errors surfaced
- [ ] `GET /waybill/{id}/label` — stream PDF or use `ir_attachment`
- [ ] Optional: `useRealtimeList` on `shipping.waybill` for dispatch id filter
- [ ] “Close dispatch” → queue `completed`, dispatch `closed`

**Acceptance:** End-to-end on MOCK carrier: compose 2 waybills → submit → print 2 labels.

---

## Wave D — Module polish

### SHP-T10 — Manifest, XML, actions (SHP-010)

**Depends on:** SHP-T04  
**Status:** done

**Goal:** Parity with CRM module packaging.

**Deliverables:**

- [ ] `manifest.py` version bump, menus (Logistyka → IFS Inbox, Dispatch history)
- [ ] `view/dispatch_views.xml`, `view/waybill_views.xml` (read-only list for support)
- [ ] `actions.py` — ⌘K entries: Open IFS Inbox, New dispatch from queue
- [ ] `bootstrap.py` — demo queue row in dev (optional)

---

### SHP-T11 — AI module config (SHP-011)

**Depends on:** SHP-T08  
**Status:** done

**Goal:** `shipping/ai.py` + register in bootstrap; handler for safe enqueue-only tools.

**Deliverables:**

- [ ] `ai.py` per `docs/16-ai-recipes.md`
- [ ] `tests/test_ai_shipping.py` — dispatcher routes, RBAC denied without role

---

### SHP-T12 — Integration tests and docs (SHP-012)

**Depends on:** SHP-T09, SHP-T10  
**Status:** done

**Goal:** Hardening + inventory update.

**Deliverables:**

- [ ] Extend `test_ifs_webhook_integration.py`: ingest → inbox → kiosk dispatch
- [ ] Update `docs/34-inventory-and-status.md` — shipping kiosk row
- [ ] Root shipping guides cross-link to `modules/shipping/docs/spec.md`
- [ ] `CHANGELOG.md` entry

---

---

## Wave A0 — Preview & AUTO (before UI)

### SHP-T00 — Compose preview + AUTO rules (SHP-AUTO)

**Depends on:** SHP-T01 (or parallel with T02 if domain types stubbed)  
**Status:** done  
**Owner:** Backend (carrier + routing specialist)

**Goal:** `GET compose-preview`, `should_auto_dispatch()`, tenant `ir_config_param` keys.

**Deliverables:**

- [ ] `controller/compose_preview.py` — uses `cf_handling_units_parser`, `routing`, `carrier_settings`
- [ ] Returns `suggested_mode`, `suggested_plan`, `blocking_errors`, `handling_units[]`
- [ ] `PUT compose-plan` draft persistence on `shipping.dispatch` (revision)
- [ ] Tests: 1 HU → auto; 3 HU → kiosk; unconfigured carrier → blocking
- [ ] Document rules in [`carrier-labels.md`](./carrier-labels.md) §4

**Acceptance:** Inbox can call preview without kiosk; AUTO eligible matches [`ux-kiosk.md` §3](./ux-kiosk.md).

---

## Wave E — UX (frontend specialist)

> **Canonical UX:** [`ux-kiosk.md`](./ux-kiosk.md). CRM parity: hook `shipping` + `ifs_queue` in `[module]/[model]/page.tsx`.

### SHP-T13 — IFS inbox page (SHP-004)

**Depends on:** SHP-T03, SHP-T00  
**Status:** done  
**Owner:** UX + frontend

**Deliverables:** `ShpIfsInboxPage`, `ShpIfsInboxSidebar`, `ShpIfsInboxTable`, URL `?view=inbox`.

### SHP-T14 — AUTO confirm strip (SHP-AUTO)

**Depends on:** SHP-T13, SHP-T00  
**Status:** done

**Deliverables:** `ShpAutoConfirmStrip` — one CTA “Wyślij 1 list przewozowy”; escape to `?kiosk=`.

### SHP-T15 — Kiosk stepper shell (SHP-005)

**Depends on:** SHP-T13  
**Status:** done

**Deliverables:** `ShpKioskComposer`, steps Review / Compose / Submit / Print (shell); `?kiosk=` param.

### SHP-T16 — DnD compose board (SHP-006)

**Depends on:** SHP-T15  
**Status:** done

**Deliverables:** `ShpHandlingUnitTile`, `ShpWaybillColumn`, @dnd-kit + TouchSensor; `PUT assign-unit`.

### SHP-T17 — Carrier chips + simulate (SHP-007)

**Depends on:** SHP-T16  
**Status:** done

**Deliverables:** `ShpCarrierChip` per column; `ShpCarrierStatusBanner`.

### SHP-T18 — Realtime inbox + progress (SHP-009)

**Depends on:** SHP-T08, SHP-T15  
**Status:** done

**Deliverables:** `useShpRealtimeIfsQueue`, `ShpDispatchProgress`, dispatch-status polling/SSE.

### SHP-T19 — Kiosk a11y + touch (SHP-005)

**Depends on:** SHP-T16  
**Status:** done

**Deliverables:** 48px targets, keyboard shortcuts (`?` modal), `prefers-reduced-motion`.

### SHP-T20 — E2E: AUTO + 3-waybill kiosk

**Depends on:** SHP-T14, SHP-T18  
**Status:** done

**Deliverables:** Playwright behind `E2E_FULL_SUITE`; Vitest for plan reducer.

---

## Wave F — Carrier execution (waybill specialist)

> **Canonical:** [`carrier-labels.md`](./carrier-labels.md)

### SHP-T21 — `execute_dispatch_for_waybill` (SHP-008)

**Depends on:** SHP-T02  
**Status:** done

**Deliverables:** Celery payload schema; `target_ref`=`{ifs_shipment_id}:{slot}`; idempotent drain.

### SHP-T22 — Multi-carrier parcel mapping

**Depends on:** SHP-T21  
**Status:** done

**Deliverables:** Per-carrier `packages[]` from assigned HUs; fix `is_pallet` from full line set.

### SHP-T23 — Label PDF / `ir_attachment`

**Depends on:** SHP-T21  
**Status:** done

**Deliverables:** `GET /waybill/{id}/label`; store base64 from DPD SOAP / DSV inline PDF.

### SHP-T24 — `dispatch-plan` batch outbox

**Depends on:** SHP-T21, SHP-T03  
**Status:** done

**Deliverables:** N outbox rows; `dispatch-status` endpoint; partial failure recovery + retry.

---

## Optional / later

| ID | Topic |
|----|--------|
| SHP-T25 | Operator lock (`assigned_user_id`) + claim queue row |
| SHP-T26 | Auto-split heuristic (weight → 2 waybills) in preview |
| SHP-T27 | ZPL printer bridge — ADR required |
| SHP-T28 | Deprecate legacy single `POST /dispatch` UI default |

---

### SHP-T30 — WMS ready-to-ship handoff (WMS-012)

**Depends on:** SHP-T02, inventory WMS-T15  
**Status:** todo  
**Owner:** shipping (cross-module contract)

**Goal:** Subscribe to `inventory.ready_to_ship.created` (outbox); create IFS queue row or dispatch draft from payload schema `ready_to_ship/v1`. UUID FKs only — no `from modules.inventory`.

**Acceptance:** Integration test with fake event; no direct read of `inventory.quant` tables.

---

## PR sizing guide

---

## PR sizing guide

| Task | Typical PR size |
|------|-----------------|
| T01–T03 | Backend-only, medium |
| T04–T07 | Frontend-heavy, large (split T06 if needed) |
| T08–T09 | Backend + UI, medium |
| T10–T12 | Small polish |

---

## Suggested session order (parallel windows)

```
Window A (backend):  T00 → T01 → T02 → T03 → T21 → T22 → T24 → T08
Window B (UX):       T13 → T14 → T15 → T16 → T17 → T18 → T09 → T20  (after T03+T00)
Window C (polish):   T10 → T11 → T12 → T23
```

---

## Copy-paste prompt for a new agent window

```text
Implement shipping task <SHP-T0X> from backend/modules/shipping/docs/tasks.md.
Read backend/modules/shipping/docs/README.md then spec + ux-kiosk OR carrier-labels for your wave.
Do not add cross-module imports. Carrier APIs only in Celery.
Include tests per docs/20-testing.md. Update spec.md version table if done.
```
