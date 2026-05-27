# Module: shipping — logistics dispatch (IFS inbox + label kiosk)

> **Layer:** product  
> **depends_on:** [base, auth] — `orders` optional FK only (UUID), no cross-module import  
> **Status:** v0.2.0 shipped · v0.3.0–v1.0 planned (**SHP-001..012**, [`tasks.md`](./tasks.md))  
> **Doc index:** [`README.md`](./README.md)  
> **Carrier adapters:** [`docs/shipping-dpd-native.md`](../../../docs/shipping-dpd-native.md), [`docs/shipping-schenker-dsv-native.md`](../../../docs/shipping-schenker-dsv-native.md)

## Documentation set

| Document | Scope |
|----------|--------|
| [`spec.md`](./spec.md) | This file — module contract |
| [`tasks.md`](./tasks.md) | Implementation sessions |
| [`ux-kiosk.md`](./ux-kiosk.md) | **Canonical UI/UX** — inbox, kiosk, AUTO rules, components |
| [`carrier-labels.md`](./carrier-labels.md) | **Canonical waybills** — lifecycle, mapping, outbox, print |

## Purpose

Bring the **shipping** module to the same structural standard as **`crm`** (manifest, domain,
repositories, services, custom router, XML views, dedicated admin-ui components where the
dynamic renderer is insufficient) and deliver a **warehouse dispatch kiosk**:

1. **IFS inbox** — see what arrived from Oracle IFS (SECONDARY ingress), triage, open workspace.
2. **Dispatch kiosk** — full-screen UX to compose **1–5 waybills (listów przewozowych)** per
   inbound shipment via **drag-and-drop** of handling-unit tiles (pallet / parcel types) onto
   waybill slots.
3. **Staged carrier flow** — per-waybill carrier choice → async API (Celery + outbox) →
   `label_created` → print/download — same outcome classes as the prior hub implementation,
   without bypassing Orbiteus RBAC or audit.
4. **AUTO fast path** — when preview says one waybill and rules allow, operators get
   **≤2 taps** (inbox → confirm dispatch); **kiosk** only when composition is non-trivial.

Most shipments use **one** waybill (AUTO); multi-waybill uses the full kiosk (split pallets, mixed carriers).

## Operating modes — AUTO vs kiosk (SHP-AUTO)

Backend **`compose-preview`** is the single source of truth; the UI must not guess.

| Mode | Typical triggers | UX doc |
|------|------------------|--------|
| `auto` | 1 HU, 1 waybill in suggested plan, carrier configured, no blocking errors | [`ux-kiosk.md` §3](./ux-kiosk.md) |
| `kiosk` | 2–5 waybills, mixed pallet+parcel, weight over tenant max, manual override | [`ux-kiosk.md` §4](./ux-kiosk.md) |

| Tenant config (`ir_config_param`) | Default | Effect |
|-----------------------------------|---------|--------|
| `shipping.kiosk_auto_enabled` | `1` | Allow AUTO strip on inbox |
| `shipping.kiosk_auto_max_hu` | `1` | Max handling units for AUTO |
| `shipping.kiosk_auto_max_weight_kg` | `31` | Above → force kiosk |
| `shipping.kiosk_auto_confirm` | `1` | Show confirm strip vs silent `?auto=1` |

Carrier eligibility, payload mapping, and outbox idempotency: [`carrier-labels.md`](./carrier-labels.md).

## Alignment with Orbiteus rules

| Rule | How this module complies |
|------|---------------------------|
| No cross-module imports | `order_id` on dispatch is nullable UUID only; no `from modules.orders...` |
| RBAC | All persistence via `BaseRepository`; kiosk APIs use `require_auth` + model access |
| Audit | CRUD on dispatch / waybill / queue; `actor=system` on IFS webhook ingest |
| Carrier HTTP | **Only** in Celery (`tasks.shipping_tasks`); HTTP API returns **202** + outbox id |
| Boring tech | FastAPI, SQLAlchemy 2, Celery, Mantine 9, **@dnd-kit** (already in admin-ui stack) |
| Vendor-neutral docs | No third-party product names or demo URLs in this file |

## Current state (v0.2.x baseline)

| Area | Today |
|------|--------|
| Models | `shipping.shipment` (single-label path), `shipping.ifs_queue` |
| IFS | Webhook ingest, queue list, one-shot dispatch → one shipment |
| Adapters | DPD, DSV/Schenker, Geodis, MOCK; routing + `ifs_packaging` matrix |
| UI | Generic list/form on `ifs_queue` and `shipment` — **no kiosk** |
| Parsing | `cf_handling_units_parser`, `coerce_ifs_payload`, `ifs_dispatch_profiles` |

## Target architecture (v1.0 kiosk)

```
IFS webhook
  → shipping.ifs_queue (inbox)
  → operator opens Dispatch Kiosk
  → shipping.dispatch (workspace, 1:1 with queue row while open)
  → shipping.handling_unit[] (tiles from payload / CF parser)
  → shipping.waybill[] (slots 1..5, DnD assignment of units)
  → POST waybill submit → ir_outbox (target_kind=shipping_label)
  → Celery → adapter.create_label() per waybill
  → state label_created → Print stage (PDF/ZPL/blob)
```

### Parity with CRM module layout

```
modules/shipping/
  manifest.py          # menus: Inbox, Dispatch, Waybills (see SHP-010)
  model/domain.py      # dispatch, waybill, handling_unit (+ evolve shipment)
  model/mapping.py
  model/schemas.py
  controller/repositories.py
  controller/services.py    # workspace, assign, submit (no carrier HTTP here)
  controller/router.py      # kiosk + inbox endpoints
  controller/ifs_webhook_router.py
  security/access.yaml
  view/*.xml           # inbox list; optional read-only dispatch summary
  actions.py
  ai.py                # SHP-011
  bootstrap.py
  docs/spec.md         # this file
  docs/tasks.md        # implementation tasks for separate agent sessions
admin-ui/src/components/shipping/
  ShippingIfsInbox.tsx
  ShippingDispatchKiosk.tsx
  ... (see SHP-004..007)
```

Dedicated TSX is allowed **only** where CRM already does (`admin-ui/src/components/crm/*`) —
kiosk is that exception (`docs/08-admin-ui.md`: prefer XML; complex product UX may use components).

---

## Feature map (SHP-001..012)

| ID | Feature | CRM analogue |
|----|---------|----------------|
| SHP-001 | Domain: `dispatch`, `waybill`, `handling_unit`; evolve `shipment` | `lead` + `stage_history` |
| SHP-002 | Migrations + RBAC models in `security/access.yaml` | CRM pipedrive migrations |
| SHP-003 | `DispatchWorkspace` service + repositories | `move_lead_to_stage`, kanban services |
| SHP-004 | IFS **inbox** API + list UX | `crm.prospect` inbox |
| SHP-005 | **Kiosk route** shell + stepper (Review → Compose → Submit → Print) | `CrmDealKanban` / deal drawer |
| SHP-006 | **DnD** handling units → waybill slots (max 5) | — (new; uses @dnd-kit) |
| SHP-007 | Per-waybill carrier tile + routing override | stage + carrier registry |
| SHP-008 | Outbox: one outbox row **per waybill** submit | single `shipping_label` today |
| SHP-009 | Print panel: label PDF/blob per waybill | — |
| SHP-010 | Manifest menus + `actions.py` + XML views | CRM manifest |
| SHP-011 | `ai.py`: suggest carrier, split packages | `crm/ai.py` |
| SHP-012 | Tests: workspace, DnD API, outbox per waybill | `test_crm_*` |

---

## Domain model (SHP-001)

### `shipping.ifs_queue` (existing — extend semantics)

| Field | Notes |
|-------|--------|
| `state` | `queued` \| `claimed` \| `in_dispatch` \| `completed` \| `failed` |
| `dispatch_id` | nullable FK → `shipping.dispatch` while kiosk open |
| `payload_json` | raw + decoded logistics snapshot |

### `shipping.dispatch` (new)

One **workspace** per IFS shipment being processed in the kiosk.

| Field | Type | Notes |
|-------|------|--------|
| `ifs_queue_id` | UUID FK | optional link back to inbox row |
| `ifs_shipment_id` | str | denormalized for search |
| `state` | enum | `draft` \| `composing` \| `submitting` \| `partial_labels` \| `ready_to_print` \| `closed` \| `cancelled` |
| `pickup_site_code` | str | `BAZ` \| `CIE` \| `BIS` from contract profile |
| `recommended_carrier_code` | str | from `resolve_carrier_for_shipment` |
| `destination_json` | JSONB | recipient snapshot |
| `sender_json` | JSONB | pickup/sender snapshot |
| `metadata_json` | JSONB | CF logistics notes, VIP, coordinator, etc. |
| `waybill_count` | int | 1..5, default 1 |
| `assigned_user_id` | UUID FK → users | operator lock (optional v1) |

### `shipping.handling_unit` (new)

Draggable **tile** — one row per pack line from IFS / CF parser.

| Field | Type | Notes |
|-------|------|--------|
| `dispatch_id` | UUID FK | parent |
| `pack_type` | str | `PAL_A`, `PACZKASTD`, … |
| `unit_type` | str | `pallet` \| `parcel` |
| `qty` | int | |
| `weight_kg` | float | |
| `length_cm`, `width_cm`, `height_cm` | float | from `get_default_dimensions` |
| `waybill_id` | UUID FK nullable | set when dropped on a slot |
| `sequence` | int | stable ordering in pool |

### `shipping.waybill` (new)

One **carrier label job** (list przewozowy).

| Field | Type | Notes |
|-------|------|--------|
| `dispatch_id` | UUID FK | |
| `sequence` | int | 1..5 |
| `carrier_code` | str | DPD, DSV, GEODIS, … per slot |
| `state` | enum | `draft` \| `queued` \| `label_created` \| `failed` \| `cancelled` |
| `tracking_number` | str | |
| `label_attachment_id` | UUID FK → `ir_attachment` | preferred for PDF |
| `label_payload_json` | JSONB | adapter raw + base64 fallback |
| `error_message` | str | |
| `submitted_at`, `label_created_at` | timestamptz | |

### `shipping.shipment` (existing — role after SHP-001)

- **v0.3:** keep for backward-compatible single-shot `POST /api/shipping/dispatch`.
- **v1.0:** treat as legacy aggregate or 1:1 alias of first waybill; new kiosk writes `waybill` only.

---

## Kiosk UX (SHP-004..009)

**Canonical wireframes, routes, components, and Polish copy:** [`ux-kiosk.md`](./ux-kiosk.md).

### Routes (CRM parity — dynamic renderer)

No dedicated `admin-ui/src/app/shipping/...` tree. Wire kiosk from
`admin-ui/src/app/[module]/[model]/page.tsx` when `shipping` + `ifs_queue`:

| URL | Screen |
|-----|--------|
| `/shipping/ifs_queue?view=inbox` | IFS inbox table |
| `/shipping/ifs_queue?kiosk={ifs_shipment_id}` | Mega kiosk overlay |
| `/shipping/ifs_queue?kiosk={id}&auto=1` | Attempt AUTO once preview loads |

Components: `admin-ui/src/components/shipping/` (prefix `Shp*`). Menu entries in `manifest.py`.

### Stepper stages

| Step | Operator sees | Actions |
|------|---------------|---------|
| **1. Review** | IFS header (shipment id, contract site, recipient, notes), parsed units in pool | Confirm → Compose |
| **2. Compose** | Up to 5 waybill columns; **drag tiles** from pool; add/remove waybill slot; per-slot carrier chip | Auto-split suggestion (optional SHP-011) |
| **3. Submit** | Per-waybill status badges; disabled until each slot has ≥1 unit | Submit all → 202 + outbox ids |
| **4. Print** | Poll / realtime until `label_created`; open PDF / print dialog | Mark dispatch `closed` |

### DnD rules (SHP-006)

- Pool: unassigned units (`waybill_id IS NULL`).
- Each waybill column accepts drop; unit may move between columns.
- Empty waybill cannot be submitted.
- Max **5** waybill slots per dispatch.
- Visual: pack type code + icon (pallet vs parcel) + qty × weight.

Use **`@dnd-kit/core`** + **`@dnd-kit/sortable`** (already declared for admin-ui).

### Carrier selection (SHP-007)

- Default: `recommended_carrier_code` on dispatch (routing + IFS forward agent).
- Override per waybill slot (tile/chip: DPD, DSV, GEODIS, INPOST, MOCK).
- `GET /api/shipping/carriers/status` — already exists; kiosk calls on mount.
- `POST /api/shipping/simulate` — optional preview per slot before submit.

---

## API contract (SHP-003, SHP-008)

All paths prefixed `/api/shipping`. JWT unless noted.

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| GET | `/ifs/inbox` | `{ items[], counts{} }` | Filter `state=queued`, sort `created_at` |
| POST | `/dispatch/from-queue/{queue_id}` | `{ dispatch_id }` | Creates dispatch + handling units from payload; sets queue `claimed` |
| GET | `/dispatch/{id}/workspace` | `DispatchWorkspaceRead` | Dispatch + units + waybills + carrier status |
| PATCH | `/dispatch/{id}` | workspace meta | `waybill_count`, state transitions |
| POST | `/dispatch/{id}/waybills` | `{ waybill }` | Add slot if count < 5 |
| DELETE | `/dispatch/{id}/waybills/{seq}` | 204 | Only if `draft` and empty |
| PUT | `/dispatch/{id}/assign-unit` | 200 | Body: `{ unit_id, waybill_id \| null }` |
| POST | `/waybill/{id}/submit` | **202** `{ outbox_id }` | Enqueue label job; sets waybill `queued` |
| POST | `/dispatch/{id}/submit-all` | **202** `{ outbox_ids[] }` | All draft waybills with units |
| GET | `/waybill/{id}/label` | PDF stream or redirect | Only when `label_created` |
| POST | `/ifs/webhook/shipment` | ingest | unchanged; optional HMAC |

Existing endpoints remain during migration:

- `POST /api/shipping/dispatch` (single shipment)
- `POST /api/shipping/ifs/queue/{id}/dispatch`

### `DispatchWorkspaceRead` (schema sketch)

```json
{
  "dispatch": { "id", "state", "ifs_shipment_id", "pickup_site_code", "recommended_carrier_code", ... },
  "queue": { "id", "objstate", "payload_json" },
  "units": [{ "id", "pack_type", "unit_type", "qty", "weight_kg", "waybill_id", ... }],
  "waybills": [{ "id", "sequence", "carrier_code", "state", "tracking_number", "unit_ids": [] }],
  "carriers": { "configured": ["DPD","DSV"], "routing_defaults": {} }
}
```

---

## Events and outbox (SHP-008)

| Event | `target_kind` | Payload highlights |
|-------|---------------|-------------------|
| `shipping.ifs.ingested` | — | audit |
| `shipping.dispatch.started` | — | audit |
| `shipping.waybill.submit_requested` | `shipping_label` | `{ waybill_id, dispatch_id, carrier_code, parcels[], ifs_context }` |
| `shipping.waybill.label_created` | — | audit + realtime topic |
| `shipping.waybill.failed` | — | audit |

Celery handler **`execute_dispatch_for_waybill`** (new) replaces single-shipment path for kiosk;
builds adapter payload from assigned `handling_unit` rows + `ifs_packaging` matrix per carrier.

**Realtime:** publish on `shipping.waybill` list topic so kiosk Print step updates without polling.

---

## Packaging and IFS decoding

Reuse existing libs (no duplication):

| Module | Role |
|--------|------|
| `lib/coerce_ifs_payload.py` | Webhook → `IfsLogisticsPayload` |
| `lib/cf_handling_units_parser.py` | CF$_ → `HandlingUnit[]` |
| `lib/ifs_packaging.py` | `PAL_*` / `PACZKASTD` → carrier pack codes |
| `lib/ifs_dispatch_profiles.py` | Contract → pickup site |
| `lib/routing.py` | Default carrier |

`start_dispatch_from_queue()` must call the same parsing pipeline as today’s
`payload_to_dispatch_packages()` but persist **rows** in `shipping.handling_unit`.

---

## Security (`security/access.yaml`)

| Model | Sales user | Logistics manager | System |
|-------|------------|-------------------|--------|
| `shipping.ifs_queue` | read | crud | — |
| `shipping.dispatch` | — | crud | — |
| `shipping.waybill` | — | crud | — |
| `shipping.handling_unit` | — | crud | — |
| `shipping.shipment` | read | crud | — |

Webhook: no JWT; optional `IFS_WEBHOOK_SECRET`.

---

## AI surface (SHP-011)

`ai.py` — `AIModuleConfig` for module `shipping`:

- **accessible_models:** `ifs_queue`, `dispatch`, `waybill`
- **callable_actions:** `shipping.dispatch.start_from_queue`, `shipping.waybill.submit` (enqueue only)
- **suggested_prompts:** “Split pallets across two DSV labels”, “Why was Geodis recommended?”

Handlers call **services** only (same RBAC as user).

---

## Config and env

| Key / env | Notes |
|-----------|--------|
| `shipping.ifs_tenant_slug` | `ir_config_param` for ingest tenant |
| `IFS_AUTO_DISPATCH` | stay `0` for kiosk-first ops |
| `SHIPPING_*_NATIVE` | per carrier docs |
| `SHIPPING_MAX_WAYBILLS` | default `5` (optional guard) |

---

## Migrations (SHP-002)

One Alembic revision per wave:

1. `shipping_dispatch`, `shipping_handling_units`, `shipping_waybills` tables.
2. Alter `shipping_ifs_shipment_queue` (+ `dispatch_id`, state enum extension).
3. Indexes: `(tenant_id, ifs_shipment_id)`, `(dispatch_id, sequence)` unique on waybills.

---

## Testing (SHP-012)

| Test file | Covers |
|-----------|--------|
| `test_shipping_dispatch_workspace.py` | create from queue, workspace shape, assign unit |
| `test_shipping_waybill_outbox.py` | submit → 202, worker mock → `label_created` |
| `test_shipping_ifs_inbox.py` | inbox filters |
| Extend `test_ifs_cf_parser.py` | units → handling_unit mapping |

---

## Out of scope (this program)

- Replacing PRIMARY label generation in external legacy hub (SECONDARY path only).
- WMS / pick-path / serial numbers.
- Returns (RMA) labels.
- Portal-ui operator access (admin-ui only for v1).

---

## References (in-repo)

| Doc | Topic |
|-----|--------|
| [`README.md`](./README.md) | Documentation index |
| [`tasks.md`](./tasks.md) | Session-sized implementation tasks |
| [`ux-kiosk.md`](./ux-kiosk.md) | Inbox + kiosk UX, AUTO, DnD, API shapes for UI |
| [`carrier-labels.md`](./carrier-labels.md) | Waybill lifecycle, carrier mapping, Celery payload |
| [`../../../docs/shipping-dpd-native.md`](../../../docs/shipping-dpd-native.md) | DPD adapter |
| [`../../../docs/shipping-schenker-dsv-native.md`](../../../docs/shipping-schenker-dsv-native.md) | DSV + IFS queue |
| [`../../crm/docs/spec.md`](../../crm/docs/spec.md) | Module spec pattern |
| [`../../../docs/03-modules.md`](../../../docs/03-modules.md) | Layout convention |
| [`../../../docs/08-admin-ui.md`](../../../docs/08-admin-ui.md) | Dynamic renderer + widgets |
| [`../../../docs/12-events-and-queues.md`](../../../docs/12-events-and-queues.md) | Outbox + Celery |

---

## Version history

| Version | Scope |
|---------|--------|
| v0.2.0 | IFS queue + single shipment dispatch (shipped) |
| v0.3.0 | SHP-001..006 inbox + kiosk compose |
| v0.4.0 | SHP-007..009 submit + print |
| v1.0.0 | SHP-010..012 polish, AI, deprecate single-path UI default |
