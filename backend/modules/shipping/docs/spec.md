# Module: shipping — carrier labels + IFS SECONDARY ingress

> **Layer:** product  
> **depends_on:** [base, auth, orders]  
> **Status:** v0.2.0 — IFS queue + outbox dispatch  
> **Indeks modułów:** [`docs/specs/README.md`](../../../../../docs/specs/README.md#kontrakty-modułów-orbiteus-modulesdocspecmd)

## Purpose

- Dispatch carrier labels (DSV/Geodis/DPD/InPost/MOCK) from Orbiteus `crm-engine`.
- Native Python adapters: DSV (`SHIPPING_DSV_NATIVE`), Geodis (`SHIPPING_GEODIS_NATIVE`), DPD (`SHIPPING_DPD_NATIVE`). See `crm-engine/docs/shipping-*-native.md`.
- **SECONDARY** IFS webhook ingress (parallel to Mercato PRIMARY) — queue + manual/async dispatch.
- CF$_ / PAL_* matrix decoding aligned with Mercato `cf-handling-units-parser` + `packaging-matrix`.

## Models

| Model | Table | Role |
|-------|-------|------|
| `shipping.shipment` | `shipping_shipments` | Outbound label / tracking |
| `shipping.ifs_queue` | `shipping_ifs_shipment_queue` | Inbound IFS webhook queue |

## Custom endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/shipping/ifs/webhook/shipment` | optional HMAC; no JWT |
| GET | `/api/shipping/ifs/queue` | JWT + RBAC |
| POST | `/api/shipping/ifs/queue/{ifs_shipment_id}/dispatch` | JWT → **202** + outbox |
| POST | `/api/shipping/dispatch` | JWT → **202** + outbox |
| POST | `/api/shipping/simulate` | JWT |
| GET | `/api/shipping/carriers/status` | JWT |

Legacy alias: `POST /api/ifs/webhook/shipment` (`api.py`).

## Events (outbox)

| Event | `target_kind` | Handler |
|-------|---------------|---------|
| `shipping.ifs.ingested` | — | audit only (optional future) |
| `shipping.label.dispatch_requested` | `shipping_label` | `tasks.shipping_tasks` |

Side effects to carrier APIs run **only** in Celery worker (pre-prompt §7).

## Config (`ir_config_param`)

| Key | Description |
|-----|-------------|
| `shipping.ifs_tenant_slug` | Tenant slug for IFS ingest (`actor=system`). Empty → first active tenant. |

## Env

| Variable | Default | Notes |
|----------|---------|-------|
| `IFS_WEBHOOK_ENABLED` | `1` | 503 when disabled |
| `IFS_WEBHOOK_SECRET` | — | HMAC optional |
| `IFS_WEBHOOK_ALLOWLIST` | — | Comma-separated client IPs |
| `IFS_AUTO_DISPATCH` | `0` | **Keep 0** while Mercato is PRIMARY |

## Out of scope

- Replacing Mercato as PRIMARY label generator.
- Syncing changes to `MIMMS_CORE/orbiteus` repo.
