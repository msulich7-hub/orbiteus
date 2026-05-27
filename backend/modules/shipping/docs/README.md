# Shipping module — documentation index

> **Layer:** product · **Code:** `backend/modules/shipping/`  
> **CRM parity:** same module layout as `backend/modules/crm/` (see [`../../../docs/03-modules.md`](../../../docs/03-modules.md))

Read these in order when implementing or reviewing a change.

| # | Document | Who needs it |
|---|----------|----------------|
| 1 | [`spec.md`](./spec.md) | Everyone — contract: models, API, SHP-001..012, version roadmap |
| 2 | [`tasks.md`](./tasks.md) | Implementers — session-sized PRs (SHP-T01..T20) |
| 3 | [`ux-kiosk.md`](./ux-kiosk.md) | Frontend + API — IFS inbox, AUTO vs kiosk, DnD, copy, a11y |
| 4 | [`carrier-labels.md`](./carrier-labels.md) | Backend + ops — waybill lifecycle, carrier mapping, outbox, print |
| 5 | [`../../../docs/shipping-dpd-native.md`](../../../docs/shipping-dpd-native.md) | DPD adapter env + SOAP |
| 6 | [`../../../docs/shipping-schenker-dsv-native.md`](../../../docs/shipping-schenker-dsv-native.md) | DSV/Schenker + IFS queue ingress |
| 7 | [`wms-audit.md`](./wms-audit.md) | Audyt vs tier-1 WMS (twarde oceny) |
| 8 | [`../../../docs/adr/0018-shipping-pack-station-not-wms.md`](../../../docs/adr/0018-shipping-pack-station-not-wms.md) | ADR: pack station vs WMS roadmap |

## Operating modes (summary)

| Mode | When | Operator experience |
|------|------|---------------------|
| **AUTO** | Server `compose-preview` → `suggested_mode: auto` (typically **1 HU**, **1 waybill**, carrier configured) | Inbox → one tap → 202 outbox → print when ready |
| **Kiosk** | 2+ waybills, mixed pallet/parcel split, weight/rules, or operator override | Full-screen stepper: Review → Compose (DnD) → Submit → Print |

Normative rules: [`ux-kiosk.md` §3](./ux-kiosk.md), [`carrier-labels.md` §4](./carrier-labels.md).

## Matrix smoke (3× per spedycja)

```bash
cd backend
python scripts/shipping_carrier_matrix_smoke.py --mock-only   # 3 MOCK
python scripts/shipping_carrier_matrix_smoke.py --per-carrier 3  # MOCK+DPD+DSV+GEODIS if env set
```

See [`carrier-labels.md`](./carrier-labels.md) § Matrix smoke.

## Agent session prompt

```text
Read docs/pre-prompt.md, then backend/modules/shipping/docs/README.md and the doc
for your task (tasks.md → SHP-Txx). Follow Orbiteus: RBAC, audit, carrier HTTP
only in Celery. UI: Mantine 9 + @dnd-kit; prefer CRM-parity components under
admin-ui/src/components/shipping/.
```
