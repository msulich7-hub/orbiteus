# Orbiteus na VM MDM NT (10.10.99.60)

**Repo:** https://github.com/msulich7-hub/orbiteus  
**Katalog na VM:** `/home/marcins/apps/orbiteus`  
**Data ostatniej aktualizacji:** 2026-05-27

Główny stack do pracy (CRM + shipping kiosk). Testorbiteka pozostaje równolegle jako backup.

---

## Adresy

| Usługa | URL |
|--------|-----|
| Admin UI | http://10.10.99.60:3020 |
| API | http://10.10.99.60:8020 |
| Portal | http://10.10.99.60:3021 |
| OpenAPI | http://10.10.99.60:8020/api/docs |
| **Kiosk IFS (shipping)** | http://10.10.99.60:3020/shipping/ifs_queue |
| **WMS — magazyny / stany** | http://10.10.99.60:3020/inventory/warehouse · `/inventory/quant` |

Login dev: `admin@example.com` / `admin1234`

### Testorbiteka (stary stack — backup)

| Usługa | URL |
|--------|-----|
| Admin | http://10.10.99.60:3010 |
| API | http://10.10.99.60:8010 |

---

## Deploy z GitHub → VM

### Z Windows (zalecane)

```powershell
cd C:\Users\MARCINS\Documents\MIMMS_CORE\orbiteus
git pull origin main
.\scripts\vm-deploy-orbiteus.ps1
```

Skrypt: `git pull` + `docker compose -p orbiteus -f docker-compose.yml -f docker-compose.vm-ports.yml up -d --build` + migracje + pytest shipping.

### Na VM (ręcznie)

```bash
ssh ubnt
cd /home/marcins/apps/orbiteus
git pull origin main
./scripts/vm-orbiteus-deploy.sh
```

Compose project: **`orbiteus`** (nie `crmengine`).

---

## Sync credentials kurierów (DPD/DSV/Geodis)

Zmienne kopiowane z Testorbiteki do `.env` orbiteus:

```bash
ssh ubnt
cd /home/marcins/apps/orbiteus
./scripts/sync-shipping-env-from-testorbiteka.sh
docker compose -p orbiteus -f docker-compose.yml -f docker-compose.vm-ports.yml up -d --force-recreate backend worker
```

Backend ładuje `.env` przez `env_file` w `docker-compose.vm-ports.yml`.

### Smoke DPD (9 etykiet)

```bash
docker compose -p orbiteus exec -T backend python scripts/dpd_orbiteus_smoke.py
# Oczekiwane: [dpd-smoke] Result: 9/9 OK
```

### Testy jednostkowe shipping

```bash
docker compose -p orbiteus exec -T backend python -m pytest \
  tests/test_shipping_compose_preview.py \
  tests/test_shipping_dispatch_workspace.py \
  tests/test_shipping_carrier_matrix.py \
  tests/test_dpd_native.py \
  tests/test_ifs_cf_parser.py \
  tests/test_ifs_outbox_dispatch.py \
  tests/test_ifs_webhook_route.py \
  tests/test_ifs_webhook_integration.py -q
```

---

## Problem: „Loading dashboard…” — kółko w nieskończoność

### Objaw

Po wejściu na http://10.10.99.60:3020 widać tylko **Loading dashboard…** (spinner). Testorbiteka na :3010 działała.

### Przyczyna

Next.js 16 w trybie **`next dev`** blokuje zasoby dev/HMR, gdy UI otwierasz po **IP VM** zamiast `localhost`. W logach frontendu:

```
Blocked cross-origin request to Next.js dev resource /_next/webpack-hmr from "10.10.99.60"
```

Klient React/axios nie dochodzi do skutku — dashboard czeka na `GET /api/crm/stats`.

Testorbiteka miała już fix w `admin-ui/next.config.js`; w forku Orbiteus brakowało `allowedDevOrigins`.

### Fix (wdrożony)

W `admin-ui/next.config.js`:

```javascript
allowedDevOrigins: [
  "10.10.99.60",
  "localhost",
  "127.0.0.1",
],
```

Commit: `7972490` — po deploy **twarde odświeżenie** przeglądarki (`Ctrl+Shift+R`) lub incognito.

### Obejście

Wejście prosto w moduł shipping (bez dashboardu CRM):

http://10.10.99.60:3020/shipping/ifs_queue

---

## Celery worker + beat

W `docker-compose.vm-ports.yml` worker/beat używają `entrypoint: ["celery"]` (nie `entrypoint.sh` z Gunicorn).

Sprawdzenie:

```bash
docker compose -p orbiteus ps
# orbiteus-worker-1, orbiteus-beat-1 → Up
```

---

## Migracje Alembic (shipping)

| Revision | Opis |
|----------|------|
| `m3g8b9c0d014` | kolejka IFS `shipping_ifs_shipment_queue` |
| `n4h5i6j7k015` | kiosk v0.3 — dispatch, waybill, handling_unit |

```bash
docker compose -p orbiteus exec -T backend alembic current
# Oczekiwane: n4h5i6j7k015 (head)
```

---

## GitHub — ważne commity (2026-05-27)

| Commit | Treść |
|--------|--------|
| `fb21861` | import modułu shipping z Testorbiteki |
| `5b85e8f` | merge PR #2 — kiosk v0.3, inbox IFS, Admin UI |
| `5697dc6` | fix Celery entrypoint + pytest w deploy |
| `622fed5` | `env_file` dla backendu (credentials) |
| `7972490` | `allowedDevOrigins` dla IP VM |

---

## PR dzienne (referencja)

| PR | Stan | Opis |
|----|------|------|
| [#2](https://github.com/msulich7-hub/orbiteus/pull/2) | **merged** | kiosk v0.3 + implementacja |
| [#1](https://github.com/msulich7-hub/orbiteus/pull/1) | open | docs kiosk (duplikat po merge #2) |
| [#3](https://github.com/msulich7-hub/orbiteus/pull/3) | open | docs WMS Track B |

---

## Pułapki

1. **Porty** — Orbiteus 3020/8020 ≠ Testorbiteka 3010/8010.
2. **Dev przez IP** — bez `allowedDevOrigins` admin na VM nie działa w `next dev`.
3. **`.env` kurierów** — tylko w orbiteus `.env`; sync z Testorbiteki po zmianie haseł w Mercato.
4. **Cookie auth** — sesja przez `orbiteus_token` (httpOnly); API z przeglądarki idzie przez proxy `/api/*` w Next.
