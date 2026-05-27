# Shipping — IFS inbox & mega kiosk UX

> **Status:** design spec (UI + API contract for admin-ui)  
> **Audience:** warehouse operators, dispatch supervisors, AI agents implementing `admin-ui/src/components/shipping/`  
> **Depends on:** [`spec.md`](./spec.md) (SHP-001..012), [`tasks.md`](./tasks.md), `docs/08-admin-ui.md`, `docs/10-design-system.md`, `docs/11-realtime.md`  
> **Stack:** Next.js 16, React 19, Mantine 9, `@dnd-kit` (same as CRM kanban). Carrier HTTP **only** in Celery.

## 1. Goals

| Goal | UX outcome |
|------|------------|
| **Speed** | Single-waybill shipments complete in ≤2 intentional taps after inbox selection (AUTO). |
| **Control** | 2–5 waybills per IFS shipment composed visually (mega kiosk) before one async dispatch. |
| **Clarity** | Operator always sees: order ref, carrier recommendation, unit tiles, per-waybill status, outbox/Celery progress. |
| **Safety** | RBAC on every action; audit on compose + dispatch; no blocking UI on carrier latency. |
| **Parity** | Same integration pattern as CRM: module components under `admin-ui/src/components/shipping/`, wired from `[module]/[model]/page.tsx` — **no** new `admin-ui/src/app/shipping/...` routes. |

Polish copy in UI examples; English for routes, component names, API fields, and test IDs.

---

## 2. Information architecture

### 2.1 Screens (logical)

| Screen ID | Operator name (PL) | Entry | Primary task |
|-----------|-------------------|-------|----------------|
| `SHP-S01` | **Skrzynka IFS** | Menu → Kolejka IFS | Triage queued webhooks; pick row; AUTO or open kiosk |
| `SHP-S02` | **Kiosk wysyłki** | From inbox or deep link | Compose 1–5 waybills via drag-drop tiles |
| `SHP-S03` | **Podgląd przesyłki** | List → Przesyłki → row | Read-only tracking, label download, retry failed |
| `SHP-S04` | **Status kurierów** | ⌘K / action | Env + routing defaults (read-only banner) |

`SHP-S03` stays on the dynamic renderer (`shipping.shipment` list/form). Custom UX concentrates on `ifs_queue`.

### 2.2 Routes & query params (renderer-native)

Orbiteus list/form routes only — extend via **search params**, not new App Router segments.

| URL | Screen | Notes |
|-----|--------|-------|
| `/shipping/ifs_queue` | SHP-S01 | Default `?view=inbox&state=queued` |
| `/shipping/ifs_queue?filter=errors` | SHP-S01 | `state=failed` |
| `/shipping/ifs_queue?kiosk={ifs_shipment_id}` | SHP-S02 | Full-width kiosk overlay or replaces list body |
| `/shipping/ifs_queue/{uuid}` | SHP-S01 detail | XML form fallback; **primary** work in kiosk |
| `/shipping/shipment` | SHP-S03 | Standard list |
| `/shipping/shipment/{uuid}` | SHP-S03 | Label JSON, tracking, error |

**Deep link for floor scanners:** `/shipping/ifs_queue?kiosk={ifs_shipment_id}&auto=1` — attempts AUTO once payload is loaded.

### 2.3 Menus & command palette

Align with `manifest.py` menus (Logistyka → Kolejka IFS / Przesyłki) and `actions.py`:

| Surface | Item (PL) | Target |
|---------|-----------|--------|
| Side menu | Kolejka IFS | `/shipping/ifs_queue?view=inbox` |
| Side menu | Przesyłki | `/shipping/shipment` |
| ⌘K | Kolejka IFS | `shipping.ifs_queue.list` |
| ⌘K | Otwórz kiosk dla… | New action `shipping.ifs_kiosk.open` (navigate + `?kiosk=`) |
| ⌘K | Status kurierów | `shipping.carriers.status` |

### 2.4 Layout (CRM parity)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AppShell · Logistyka                                                          │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Nav          │  [ViewHeader: Skrzynka IFS]     [Odśwież] [Filtr ▼] [⌘K]   │
│              ├──────────────────────────────────────────────────────────────┤
│              │  ┌─────────────┐  ┌──────────────────────────────────────────┐ │
│              │  │ IfsInbox    │  │ IfsInboxTable OR ShpKioskComposer       │ │
│              │  │ Sidebar     │  │ (when ?kiosk= set)                       │ │
│              │  │ (queues)    │  │                                          │ │
│              │  └─────────────┘  └──────────────────────────────────────────┘ │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

Pattern mirrors `CrmLeadWithQueues` + `CrmQueueSidebar`: sidebar filters, main canvas swaps to kiosk.

---

## 3. AUTO vs manual — decision tree

### 3.1 Definitions

- **Handling unit (HU):** One pallet or parcel tile from CF$_ / `lines` (see `cf_handling_units_parser.py`).
- **Waybill slot:** One carrier label request (may group ≥1 HU on same physical label per carrier rules).
- **AUTO:** Server + UI agree on a single waybill plan; operator confirms with one primary CTA (or skip confirm when tenant policy allows).
- **Kiosk (manual):** `ShpKioskComposer` — operator assigns HUs to 1–5 waybill columns via drag-drop.

### 3.2 Decision tree (backend is source of truth)

```
IFS row selected (ifs_shipment_id)
        │
        ▼
GET /api/shipping/ifs/queue/{id}/compose-preview   [SHP-004]
        │
        ├─ blocking_errors[] non-empty ──► Kiosk + alert banner (cannot AUTO)
        │
        ├─ suggested_mode == "auto"
        │       AND tenant ir_config shipping.kiosk_auto_enabled != "0"
        │       AND operator has shipping.ifs_queue.write
        │       AND carriers/status shows recommended carrier configured
        │           │
        │           ├─ URL ?auto=1 OR user pref auto_submit ──► POST compose (plan) + POST dispatch
        │           │                                              ► toast "Wysłano do kolejki"
        │           │                                              ► stay on inbox, SSE updates row
        │           │
        │           └─ else ──► ShpAutoConfirmStrip (1 big button)
        │                         "Wyślij 1 list przewozowy · {carrier}"
        │
        └─ suggested_mode == "kiosk"
                OR waybill_count > 1
                OR distinct_carrier_splits > 1
                OR total_hu_count > auto_max_hu (default 1)
                OR weight_kg > auto_max_weight_kg
                OR force_carrier conflict
                    │
                    ► Open SHP-S02 kiosk (?kiosk={ifs_shipment_id})
```

### 3.3 AUTO eligibility rules (normative)

Implement in `compose-preview` (SHP-004). UI **must not** guess.

| Condition | Result |
|-----------|--------|
| Exactly **1** waybill in suggested plan | `suggested_mode: "auto"` |
| **2–5** waybills | `suggested_mode: "kiosk"` |
| **>5** waybills after split | `suggested_mode: "kiosk"`, `blocking_errors: ["Za dużo listów — skontaktuj się z logistyką"]` |
| Unparsed CF$_ / missing `order_id` mapping | Kiosk + blocking error |
| Mixed pallet + parcel requiring distinct carriers | Kiosk |
| `state` not in `queued` | Read-only detail; dispatch disabled |
| Carrier not configured | Kiosk allowed but dispatch blocked with clear env hint |

### 3.4 Operator overrides

| Control | Effect |
|---------|--------|
| **Otwórz kiosk** | Forces `?kiosk=` even when AUTO eligible |
| **Tryb automatyczny** toggle (user localStorage) | When off, always show `ShpAutoConfirmStrip` instead of silent `?auto=1` |
| **Wymuś przewoźnika** | `force_carrier` on dispatch; re-runs simulate |

---

## 4. Mega kiosk — stepper wireframe & components

### 4.1 Stepper (3 steps, horizontal on ≥md, vertical on kiosk portrait)

```
 Step 1              Step 2                    Step 3
 PRZEGLĄD      →    UKŁAD LISTÓW        →    WYSYŁKA
 (dane IFS)         (drag-drop)              (podsumowanie)
```

#### Step 1 — Przegląd (`kiosk-step=review`)

```
┌──────────────────────────────────────────────────────────────────┐
│ ← Skrzynka    Wysyłka IFS: 4729182    [BIS]  Objstate: Released   │
│ Zamówienie: SO-44102 (orders)   Waga: 24.5 kg   Agent: DPD_PL      │
├──────────────────────────────────────────────────────────────────┤
│ Odbiorca: ACME Sp. z o.o. · Warszawa · PL                          │
│ [Symuluj routing]  →  Rekomendacja: DPD (skonfigurowany)           │
├──────────────────────────────────────────────────────────────────┤
│ Jednostki (5):                                                     │
│  [PAL_A ×1 180kg] [PACZKASTD ×2] [PACZKASTD ×2] ...                │
│  (tiles read-only here; editing in step 2)                         │
├──────────────────────────────────────────────────────────────────┤
│ Zamówienie ERP: [ many2one orders.order ]  *wymagane*              │
│         [ Dalej: Układ listów ]                                    │
└──────────────────────────────────────────────────────────────────┘
```

#### Step 2 — Układ listów (`kiosk-step=compose`)

```
┌──────────────────────────────────────────────────────────────────┐
│ Pula jednostek (przeciągnij)          │ List przewozowy 1 (DPD)  │
│ ┌──────┐ ┌──────┐ ┌──────┐           │ ┌──────────────────────┐ │
│ │PAL_A │ │PKG 1 │ │PKG 2 │           │ │ PAL_A  180kg         │ │
│ │180kg │ │5.5kg │ │5.5kg │           │ └──────────────────────┘ │
│ └──────┘ └──────┘ └──────┘           │ [+ Dodaj list] (max 5)   │
│                                       ├──────────────────────────┤
│                                       │ List 2 (DPD) …           │
│                                       │ List 3 (pusty) …         │
└──────────────────────────────────────────────────────────────────┘
│ [ Wstecz ]              [ Dalej: Wyślij ]                         │
└──────────────────────────────────────────────────────────────────┘
```

#### Step 3 — Wysyłka (`kiosk-step=submit`)

```
┌──────────────────────────────────────────────────────────────────┐
│ Podsumowanie · 3 listy przewozowe · DPD                            │
│  L1: PAL_A (1 HU)   L2: PACZKASTD (2 HU)   L3: PACZKASTD (2 HU)   │
├──────────────────────────────────────────────────────────────────┤
│ [ ] Drukuj etykiety po utworzeniu (domyślnie włączone)             │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │         WYŚLIJ DO KURIERA (202 · kolejka)                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Po kliknięciu: stan → processing; UI nie czeka na HTTP kuriera   │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Component file map

All under `admin-ui/src/components/shipping/`:

| File | Responsibility |
|------|----------------|
| `ShpIfsInboxPage.tsx` | Orchestrator: sidebar + table or kiosk; URL state |
| `ShpIfsInboxSidebar.tsx` | Filters: W kolejce / W trakcie / Błędy / Wszystkie (CRM queue pattern) |
| `ShpIfsInboxTable.tsx` | Dense table: shipment id, order, weight, HU count, carrier, state badge |
| `ShpIfsRowPreviewDrawer.tsx` | Quick peek without full kiosk (optional) |
| `ShpAutoConfirmStrip.tsx` | AUTO mode: single CTA + carrier badge + escape to kiosk |
| `ShpKioskComposer.tsx` | Stepper shell, step routing, loading/error boundaries |
| `ShpKioskReviewStep.tsx` | Step 1: recipient, meta, order many2one |
| `ShpKioskComposeStep.tsx` | Step 2: DnD board |
| `ShpKioskSubmitStep.tsx` | Step 3: summary + dispatch |
| `ShpHandlingUnitTile.tsx` | Draggable pallet/parcel chip (weight, pack_type, qty) |
| `ShpWaybillColumn.tsx` | Droppable column header + carrier select + HU list |
| `ShpWaybillDragOverlay.tsx` | `DragOverlay` clone (CRM card pattern) |
| `ShpDispatchProgress.tsx` | Outbox + per-waybill states from SSE/poll |
| `ShpCarrierStatusBanner.tsx` | Top banner from `GET /carriers/status` |
| `ShpRequiredOrderModal.tsx` | Missing `order_id` — mirrors `RequiredFieldsModal` |
| `shpTypes.ts` | Shared TS types mirroring Pydantic compose schemas |
| `useShpComposePreview.ts` | Hook: preview + suggested_mode |
| `useShpRealtimeIfsQueue.ts` | `useRealtimeList("shipping/ifs_queue")` wrapper |

### 4.3 Wiring in admin-ui (no new app routes)

In `admin-ui/src/app/[module]/[model]/page.tsx`:

```ts
const isShippingIfsQueue = mod === "shipping" && model === "ifs_queue";
// if (isShippingIfsQueue) return <ShpIfsInboxPage cfg={cfg} />;
```

In `[id]/page.tsx` — optional banner linking to `?kiosk={ifs_shipment_id}`.

Register `view/config.py` hook later if we add XML `widget="shp_kiosk"`; until then, conditional import like CRM.

---

## 5. Drag-and-drop interaction rules

### 5.1 Libraries & sensors

Same stack as `CrmDealKanban.tsx`:

- `@dnd-kit/core`: `DndContext`, `DragOverlay`, `closestCorners`
- `@dnd-kit/sortable` inside a column when reordering HUs
- `PointerSensor` with `{ activationConstraint: { distance: 8 } }` — prevents accidental drags on scroll
- **Touch:** add `TouchSensor` with `delay: 150`, `tolerance: 6` for gloved hands

### 5.2 Rules

| Rule | Behavior |
|------|----------|
| **Source pool** | All HUs start in “Pula” until assigned |
| **Drop target** | Only `ShpWaybillColumn` droppables; drop on column appends HU |
| **Split qty** | If `qty > 1`, drop opens `ShpSplitQtyModal` (how many to this waybill) |
| **Max columns** | 5 waybills; “+ Dodaj list” disabled at 5 |
| **Empty column** | Allowed; removed on “Usuń list” if empty |
| **Carrier per column** | Default from `simulate`; operator may override per column if RBAC allows |
| **Pallet guard** | If carrier rejects pallet (config flag), tile snaps back + toast |
| **Undo** | `Ctrl+Z` / `Cmd+Z` restores last plan snapshot (client-side stack, max 20) |
| **Persist draft** | Debounced `PUT compose-plan` (SHP-005) — optional badge “Zapisano” |

### 5.3 Keyboard shortcuts (kiosk focused)

| Key | Action |
|-----|--------|
| `↑` `↓` | Move focus between HU tiles |
| `Enter` | Pick up / drop focused HU on selected column |
| `1`–`5` | Focus waybill column N |
| `Ctrl+Enter` | Submit (step 3 only) |
| `Escape` | Back step or close kiosk → inbox |
| `R` | Refresh preview (reload compose-preview) |
| `?` | Open shortcuts help `Modal` |

Global ⌘K remains available but must not steal focus while typing in `TextInput`.

### 5.4 Error states

| Code / condition | UI (PL) | Recovery |
|------------------|---------|----------|
| `blocking_errors` from preview | Red `Alert` at top | Fix data in IFS or open supervisor |
| Missing `order_id` | `ShpRequiredOrderModal` | Select order many2one |
| 403 RBAC | Mantine notification | Request access |
| 409 state not queued | Yellow alert, read-only | Refresh list |
| 202 dispatch accepted | Green toast “W kolejce” | Show `ShpDispatchProgress` |
| Celery `failed` | Badge “Błąd” + `error_message` | Retry dispatch (SHP-007) |
| Carrier not configured | Gray banner + link to env docs | Override carrier or fix env |
| Network offline | Full-width `Alert` | Retry button |

### 5.5 Empty states

| Context | Copy (PL) | Illustration |
|---------|-----------|--------------|
| Inbox zero queued | “Brak przesyłek w kolejce. Nowe wpisy pojawią się po webhooku IFS.” | `IconInbox` |
| Kiosk no HUs parsed | “Nie rozpoznano jednostek wysyłkowych. Sprawdź CF$_ w payloadzie.” | `IconPackage` |
| All columns empty on submit | Disable CTA: “Przeciągnij jednostki do list przewozowych” | — |
| Shipments list | Use shared `EmptyState` | — |

---

## 6. Touch / kiosk ergonomics

| Token | Value | Rationale |
|-------|-------|-----------|
| Min tap target | **48×48 px** (Mantine `size="lg"` buttons) | Gloved warehouse hands |
| Tile min size | **72×72 px** | Drag affordance |
| Primary CTA height | **56 px** | Step 3 submit |
| Font scale | `theme.fontSizes.md` base; titles +1 step on kiosk breakpoint |
| Contrast | WCAG **AA** minimum; prefer `theme.white` on `theme.colors.dark[7]` for floor kiosks |
| `prefers-reduced-motion` | Disable drag animations; instant snap |

### Status colors (align with Mantine + `StatusBadge` conventions)

| State | Color | Label (PL) |
|-------|-------|------------|
| `queued` | `gray` | W kolejce |
| `processing` | `blue` | Przetwarzanie |
| `dispatched` / `label_created` | `green` | Wysłano |
| `failed` | `red` | Błąd |
| `draft` compose | `yellow` | Szkic |

Use **icon + text**, never color alone.

---

## 7. Performance & realtime

### 7.1 Non-blocking dispatch

1. UI calls `POST .../dispatch` or `POST .../compose` + `POST .../dispatch-plan`.
2. API returns **202** + `{ outbox_id, state: "processing" }`.
3. UI shows optimistic `processing` on row; **never** await Celery.
4. `ShpDispatchProgress` polls `GET .../queue/{id}/status` **or** subscribes SSE (preferred).

### 7.2 Optimistic UI

| Action | Optimistic update | Rollback on error |
|--------|-------------------|-------------------|
| AUTO dispatch | Row → `processing` | Revert to `queued` + toast |
| Save compose plan | Local plan + “Zapisano” | Reload preview |
| Drag HU | Immediate column change | Revert tile + notification |

### 7.3 SSE topics

Subscribe when inbox or kiosk open:

```
tenant:{tid}:model:shipping.ifs_queue:list
tenant:{tid}:model:shipping.ifs_queue:record:{uuid}
tenant:{tid}:model:shipping.shipment:list
```

On `record.updated`, patch row in `ShpIfsInboxTable` or advance `ShpDispatchProgress`.

Use `useRealtimeList` from `admin-ui/src/lib/realtime.ts` (same as `ResourceList`).

### 7.4 Caching & payload size

- `compose-preview` returns normalized HUs (not raw Oracle JSON).
- Raw `payload_json` only in drawer/debug expander.
- Debounce draft saves **500 ms**; coalesce in-flight PUTs.

---

## 8. Accessibility

- All drag tiles: `aria-grabbed`, `aria-roledescription="przeciągnij jednostkę"`.
- Each `ShpWaybillColumn`: `aria-label="List przewozowy {n}, przewoźnik {carrier}"`.
- Focus trap in kiosk overlay; restore focus to inbox row on close.
- Stepper: `aria-current="step"` on active step.
- Live region (`aria-live="polite"`) on dispatch status changes.
- High-contrast mode: rely on Mantine `theme` tokens, not hardcoded hex.

---

## 9. API shapes the UI needs

### 9.1 Implemented today (v0.2 — use as-is)

| Method | Path | UI usage |
|--------|------|----------|
| `GET` | `/api/shipping/ifs/queue?state=&limit=` | Inbox table |
| `POST` | `/api/shipping/ifs/queue/{ifs_shipment_id}/dispatch` | Legacy single-shot dispatch (202) |
| `POST` | `/api/shipping/dispatch` | Manual dispatch from order |
| `POST` | `/api/shipping/simulate` | Carrier recommendation |
| `GET` | `/api/shipping/carriers/status` | Banner + AUTO gate |
| `GET` | `/api/shipping/ifs_queue` | CRUD fallback / manager |
| `GET` | `/api/orders/order` | Many2one search (UUID FK only) |

**`IfsQueueRowRead`** (list row):

```json
{
  "id": "uuid",
  "ifs_shipment_id": "4729182",
  "ifs_sid": "BIS",
  "objstate": "Released",
  "state": "queued",
  "order_no": "SO-44102",
  "forward_agent_id": "DPD_PL",
  "total_weight_kg": 24.5,
  "line_count": 5,
  "error_message": "",
  "created_at": "2026-05-27T10:00:00Z"
}
```

**`POST /dispatch` body** (`DispatchBody` — multi-parcel capable):

```json
{
  "order_id": "uuid",
  "weight_kg": 24.5,
  "is_pallet": true,
  "is_locker": false,
  "forward_agent_id": "DPD_PL",
  "force_carrier": null,
  "recipient": { "company_name": "...", "zip": "00-001", "city": "Warszawa", "country": "PL" },
  "parcels": [{ "weight": 5.5, "pack_type": "PACZKASTD" }],
  "ifs_payload": { },
  "packages": [{ }]
}
```

**`DispatchAcceptedResponse`:**

```json
{
  "ok": true,
  "outbox_id": "uuid",
  "state": "processing",
  "ifs_shipment_id": "4729182"
}
```

### 9.2 New endpoints (SHP-004..007 — UI contract)

#### `GET /api/shipping/ifs/queue/{ifs_shipment_id}/compose-preview`

```json
{
  "ifs_shipment_id": "4729182",
  "queue_id": "uuid",
  "state": "queued",
  "suggested_mode": "auto",
  "suggested_carrier": "DPD",
  "order_no": "SO-44102",
  "order_id": null,
  "recipient": { "company_name": "ACME", "city": "Warszawa", "postal_code": "00-001", "country_code": "PL" },
  "handling_units": [
    {
      "id": "hu-0",
      "type": "pallet",
      "pack_type": "PAL_A",
      "qty": 1,
      "weight_kg": 180,
      "length_cm": 120,
      "width_cm": 80,
      "height_cm": 150
    }
  ],
  "suggested_plan": {
    "waybills": [
      {
        "index": 0,
        "carrier_code": "DPD",
        "hu_ids": ["hu-0"],
        "weight_kg": 180,
        "is_pallet": true
      }
    ]
  },
  "blocking_errors": [],
  "warnings": ["Brak mapowania zamówienia — wybierz ręcznie"]
}
```

#### `PUT /api/shipping/ifs/queue/{ifs_shipment_id}/compose-plan`

Draft only; no carrier call.

```json
{
  "order_id": "uuid",
  "waybills": [
    { "carrier_code": "DPD", "hu_ids": ["hu-0", "hu-1"], "force_carrier": null }
  ]
}
```

Response: `{ "saved": true, "revision": 3 }`.

#### `POST /api/shipping/ifs/queue/{ifs_shipment_id}/dispatch-plan`

Replaces single-shot dispatch for multi-waybill. **202** + outbox batch id.

```json
{
  "order_id": "uuid",
  "waybills": [
    { "carrier_code": "DPD", "hu_ids": ["hu-0"], "parcels": [], "is_pallet": true },
    { "carrier_code": "DPD", "hu_ids": ["hu-1", "hu-2"], "parcels": [], "is_pallet": false }
  ],
  "print_labels": true
}
```

Response:

```json
{
  "ok": true,
  "outbox_batch_id": "uuid",
  "waybill_jobs": [
    { "index": 0, "outbox_id": "uuid", "state": "processing" },
    { "index": 1, "outbox_id": "uuid", "state": "processing" }
  ],
  "ifs_shipment_id": "4729182"
}
```

#### `GET /api/shipping/ifs/queue/{ifs_shipment_id}/dispatch-status`

```json
{
  "ifs_shipment_id": "4729182",
  "queue_state": "processing",
  "waybills": [
    { "index": 0, "state": "label_created", "tracking_number": "123…", "error_message": null },
    { "index": 1, "state": "failed", "tracking_number": null, "error_message": "DPD: auth" }
  ]
}
```

#### `POST /api/shipping/ifs/queue/{ifs_shipment_id}/retry`

Body: `{ "waybill_index": 1 }` — **202**, single job re-queued.

### 9.3 Config keys (`ir_config_param`)

| Key | Default | Effect |
|-----|---------|--------|
| `shipping.kiosk_auto_enabled` | `1` | Tenant allows AUTO |
| `shipping.kiosk_auto_max_hu` | `1` | Max HUs for AUTO |
| `shipping.kiosk_auto_max_weight_kg` | `31` | Above → kiosk |
| `shipping.kiosk_auto_confirm` | `1` | Require strip vs silent `?auto=1` |

---

## 10. Security & audit (UI obligations)

- Hide dispatch CTAs without `shipping.ifs_queue.write`.
- Log compose-plan saves and dispatch-plan submits (backend audit); UI shows `request_id` in debug drawer for support.
- Never send carrier API keys to browser.
- Webhook ingress remains server-only (no UI).

---

## 11. Testing notes (for implementers)

| Layer | What to test |
|-------|----------------|
| Vitest | `shpTypes` guards, reducer for DnD plan, AUTO vs kiosk branch |
| RTL | `ShpAutoConfirmStrip` renders one CTA; disabled submit when empty columns |
| Playwright (`E2E_FULL_SUITE`) | Inbox → kiosk → assign HU → mock 202 → SSE row update |
| Backend | `compose-preview` AUTO/kiosk thresholds; `dispatch-plan` enqueues N outbox rows |

---

## 12. Updates to `tasks.md` (UX-specific additions)

Proposed tasks to append (ids follow SHP-Txx in [`tasks.md`](./tasks.md)):

| ID | Task | Depends |
|----|------|---------|
| **SHP-T13** | `ShpIfsInboxPage` + sidebar + table + URL `?view=` / `?kiosk=` wired in `page.tsx` | SHP-T08 |
| **SHP-T14** | `ShpKioskComposer` stepper + compose/submit steps + DnD | SHP-T04, SHP-T05 |
| **SHP-T15** | `ShpAutoConfirmStrip` + AUTO decision from `compose-preview` | SHP-T04 |
| **SHP-T16** | `useShpRealtimeIfsQueue` + inbox/kiosk SSE patch | SHP-T11 |
| **SHP-T17** | Touch sensors + kiosk theme density + `prefers-reduced-motion` | SHP-T14 |
| **SHP-T18** | `ShpDispatchProgress` + dispatch-status polling/SSE | SHP-T06, SHP-T07 |
| **SHP-T19** | Playwright: AUTO path + 3-waybill kiosk path | SHP-T13–T18 |
| **SHP-T20** | Command palette actions `shipping.ifs_kiosk.open` + docs link | SHP-T13 |

---

## 13. Reference — CRM files to mirror

| CRM file | Shipping analogue |
|----------|-------------------|
| `CrmQueueSidebar.tsx` | `ShpIfsInboxSidebar.tsx` |
| `CrmDealKanban.tsx` | `ShpKioskComposeStep.tsx` (DnD only) |
| `RequiredFieldsModal.tsx` | `ShpRequiredOrderModal.tsx` |
| `CrmDealDrawer.tsx` | `ShpIfsRowPreviewDrawer.tsx` |

---

## Appendix A — Polish UI copy cheat sheet

| Key | Text |
|-----|------|
| inbox.title | Skrzynka IFS |
| kiosk.title | Kiosk wysyłki |
| auto.cta | Wyślij 1 list przewozowy |
| submit.cta | Wyślij do kuriera |
| compose.pool | Pula jednostek |
| compose.add_waybill | Dodaj list przewozowy |
| toast.queued | Wysłano do kolejki — etykieta w trakcie |
| error.carrier | Przewoźnik nie jest skonfigurowany |

---

*Document version: 2026-05-27 · Module shipping · Orbiteus admin-ui*
