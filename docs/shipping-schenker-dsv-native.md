# Shipping — natywny DB Schenker / DSV (Orbiteus crm-engine)

**Status:** wdrożony w Testorbiteka (Python, bez subprocess Mercato)  
**Źródło prawdy Mercato:** `mercato/.ai/specs/SPEC-005-DSV-SCHENKER.md`, `mercato-shipping-hub/src/carrier/dsv-carrier.ts`

## Cel

Integracja **eSchenker Connect Booking WebService v1.1** (SOAP) jako natywny adapter Python — analogicznie do `GeodisPythonAdapter`.

Kody rejestru: `DSV`, `SCHENKER`, `DBSCHENKER` → kanoniczny `DSV`.

## Architektura

```
POST /api/shipping/dispatch  (202 Accepted)
  → services.dispatch_for_order() → ir_outbox (target_kind=shipping_label)
  → Celery drain_outbox → tasks.shipping_tasks
  → execute_dispatch_for_order() → routing + adapter.create_label()
  → ShipmentRepository (state=label_created)
```

Przy `SHIPPING_DSV_NATIVE=0` pozostaje `MercatoHubAdapter` (Node subprocess).

## Geodis vs Schenker — model adresów

| | Geodis | Schenker/DSV |
|---|--------|--------------|
| Nadawca umowny | jeden z env (`GEODIS_SENDER_*`) | **SHIPPER** — zawsze MDM NT Bielsko (`PLMDMNT007000`) |
| Miejsce odbioru | ten sam adres (symbol z env) | **PICKUP** — magazyn z `pickupLocation` |
| Nadpisanie z IFS | `sender` nadpisuje pola, symbol z env | `sender` nadpisuje **tylko PICKUP** |
| Grupa Connect | jeden shipperId | **groupId** per magazyn (2170538/39/40) |

## Lokalizacje odbioru (MDM NT)

| Klucz | groupId | pickupAddressId | Firma / adres |
|-------|---------|-----------------|---------------|
| `bielsko` | 2170538 | PLMDMNT007000 | MDM NT, ul. Bestwińska 143, Bielsko-Biała |
| `cieszyn` | 2170539 | PLMDMNT007004 | MDM SA, ul. Bielska 206, Cieszyn |
| `bazanowice` | 2170540 | PLMDMNT007005 | MDM NT, Cieszyńska 1F, Bażanowice |

**SHIPPER (płatnik):** zawsze `PLMDMNT007000`, VAT `5482614481`.

## Mapowanie kontraktu IFS → pickupLocation

| Prefiks kontraktu | Site | pickupLocation |
|-------------------|------|----------------|
| `BIS`, `BIS^01` | Bielsko | `bielsko` |
| `CIE`, `CIE^01` | Cieszyn | `cieszyn` |
| `BAZ`, `BAZ^01` | Bażanowice | `bazanowice` |

Implementacja: `modules/shipping/lib/ifs_dispatch_profiles.py`.

## SOAP API

| Operacja | Cel |
|----------|-----|
| `getBookingRequestLand` | booking + opcjonalnie inline PDF (`barcodeDocument`) |
| `getBookingBarcodeRequest` | PDF etykiety dla istniejącego `bookingId` |

| Środowisko | URL |
|------------|-----|
| FAT (test) | `https://eschenker-fat.dbschenker.com/webservice/bookingWebServiceV1_1` |
| PROD | `https://eschenker.dbschenker.com/webservice/bookingWebServiceV1_1` |

Auth: `<applicationArea><accessKey>` — bez OAuth.

## Zmienne środowiskowe

| Zmienna | Wymagane | Domyślnie |
|---------|----------|-----------|
| `DSV_ACCESS_KEY` | **TAK** | — |
| `DSV_GROUP_ID` | nie | z profilu pickup |
| `DSV_USER_ID` | nie | — |
| `DSV_ENV` | nie | `test` → FAT |
| `DSV_ENDPOINT` | nie | override URL |
| `DSV_INCOTERM` | nie | `DAP` |
| `DSV_PRODUCT_CODE` | nie | `43` |
| `DSV_VAT_NO` | nie | `5482614481` |
| `DSV_DEFAULT_LOCATION` | nie | `bielsko` |
| `DSV_SENDER_COUNTRY` | nie | `PL` |
| `DSV_SENDER_PHONE` | nie | — |
| `DSV_SENDER_EMAIL` | nie | — |
| `DSV_INTERNATIONAL_GROUP_ID` | nie | `2170537` |
| `SHIPPING_DSV_NATIVE` | nie | `1` — Python; `0` → Mercato hub |

Sync z Mercato: `.\scripts\sync-carrier-env-from-mercato.ps1`

## Reguły biznesowe

- Odbiór: **następny dzień roboczy** 09:00–17:00 (weekend pomijany).
- Etykieta: **A6**, `separated=true`.
- Opis ładunku: domyślnie `AKCESORIA DACHOWE` (`options.dsvCargoDescription` nadpisuje).
- Eksport: `groupId=2170537` gdy kraj odbiorcy ≠ PL (`options.dsvInternational`).
- PL–PL: osobny adres **PICKUP** nawet gdy identyczny z SHIPPER (wymóg eSchenker).

## Mapowanie opakowań IFS → DSV

`modules/shipping/lib/ifs_packaging.py` — np. `PAL_A`→`EP`, `PAL_G`→`XPP2`, `PACZKASTD`→`PC`.

## Pułapki FAT

- Testy **wyłącznie** na `DSV_ENV=test` (eschenker-fat). PROD tylko po jawnej zgodzie.
- Na FAT typy `PC`, `CTXX`, `XP1`, `XPP2` mogą zwracać **błąd 126** — smoke używa `EP` + `XP`.
- Brak `DSV_ACCESS_KEY` → czytelny błąd konfiguracji.

## Testy

### Unit (bez SOAP)

```bash
cd crm-engine/backend
pytest tests/test_dsv_native.py -v
```

### Smoke FAT — testowe listy przewozowe

```bash
cd crm-engine/backend
python scripts/dsv_orbiteus_smoke.py 3          # 3 bookingi (1 per magazyn)
python scripts/dsv_orbiteus_smoke.py 9          # 3 magazyny × 3 scenariusze palet
python scripts/dsv_orbiteus_smoke.py --matrix   # 30 bookingów (macierz jak Mercato)
```

Wymaga `DSV_ACCESS_KEY` w env (domyślnie ładowane z `MERCATO_ENV`).

PDF zapisywane jako `dsv-label-{bookingId}.pdf`.

## Pliki implementacji

| Plik | Rola |
|------|------|
| `lib/adapters/dsv_adapter.py` | `DsvPythonAdapter.create_label()` |
| `lib/adapters/dsv/client.py` | SOAP, `buildLandBooking` |
| `lib/adapters/dsv/locations.py` | profile pickup |
| `lib/adapters/dsv/config.py` | env credentials |
| `lib/adapters/dsv/types.py` | dataclasses |
| `lib/ifs_dispatch_profiles.py` | BIS/CIE/BAZ z kontraktu IFS |
| `lib/carrier_registry.py` | `SHIPPING_DSV_NATIVE` |

---

## IFS inbound (webhook SECONDARY) — zgodność Orbiteus

Równoległy ingress obok Mercato (PRIMARY `:3100`). Implementacja w module `shipping` z portem `orbiteus_core.ports.IfsInboundPort`.

### Przepływ (Outbox + Celery — pre-prompt §7)

```
IFS SHIPMENT (TEST)
  → Oracle MS_INTEGRATION_API (UTL_HTTP)
  → POST /api/shipping/ifs/webhook/shipment   (kanoniczny)
     lub POST /api/ifs/webhook/shipment      (alias legacy)
  → IfsInboundPort → IfsQueueRepository (state=queued)
  → actor=system, tenant z ir_config_param shipping.ifs_tenant_slug
  → Ręczny dispatch: POST .../queue/{id}/dispatch → 202 + ir_outbox
  → Celery drain_outbox (target_kind=shipping_label) → adapter.create_label
  → UI: /shipping/ifs_queue (dynamic renderer)
```

**Worker wymagany** przy dispatch etykiety:

```bash
celery -A celery_app worker -l info -Q default,outbox
celery -A celery_app beat -l info
```

### Warstwy Orbiteus

| Warstwa | Plik |
|---------|------|
| Port | `orbiteus_core/ports/ifs_inbound.py` |
| Adapter | `modules/shipping/lib/ifs_inbound_adapter.py` |
| System context | `orbiteus_core/integrations/system_context.py` |
| Repository + RBAC + audit | `modules/shipping/controller/repositories.py` (`IfsQueueRepository`) |
| Model RBAC | `shipping.ifs_queue` w `security/access.yaml` |
| Outbox handler | `tasks/outbox_tasks.py` → `tasks/shipping_tasks.py` |
| Spec modułu | `modules/shipping/docs/spec.md` |
| Migracja Alembic | `migrations/versions/l2f7a8b9c013_shipping_ifs_shipment_queue.py` |
| Migracja SQL (ręczna) | `scripts/migrations/20260527_shipping_ifs_shipment_queue.sql` |

### Dekodowanie matrycy

| Krok | Plik |
|------|------|
| CF$_ → PAL_* | `lib/cf_handling_units_parser.py` |
| Wymiary / kody kuriera | `lib/ifs_packaging.py` |
| Payload kolejki | `lib/ifs_inbound_mapper.py` |
| Etykieta | `lib/ifs_mapper.py` |

### API

| Endpoint | Auth | Opis |
|----------|------|------|
| `POST /api/shipping/ifs/webhook/shipment` | brak JWT; opcjonalnie `IFS_WEBHOOK_SECRET` | ingest (kanoniczny) |
| `POST /api/ifs/webhook/shipment` | j.w. | alias dla istniejących URL Oracle |
| `GET /api/shipping/ifs/queue` | JWT + RBAC `shipping.ifs_queue` read | lista |
| `POST /api/shipping/ifs/queue/{id}/dispatch` | JWT + RBAC write | **202** — kolejka outbox (bez sync HTTP kuriera) |
| `POST /api/shipping/dispatch` | JWT | **202** — j.w. |
| `GET /api/shipping/ifs_queue` | JWT | auto-CRUD (manager) |

### Env

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `IFS_WEBHOOK_ENABLED` | `1` | HTTP 503 gdy 0 |
| `IFS_WEBHOOK_SECRET` | — | HMAC (opcjonalnie) |
| `IFS_AUTO_DISPATCH` | `0` | enqueue po ingest tylko gdy `=1` **i** `order_id` w JSON |
| `IFS_WEBHOOK_ALLOWLIST` | — | opcjonalnie: lista IP Oracle (CSV) |

### Oracle SECONDARY — checklist

1. Host widoczny z `10.10.99.42` (LAN); opcjonalnie `IFS_WEBHOOK_ALLOWLIST`.
2. URL: `http://<host>:8010/api/shipping/ifs/webhook/shipment` (zalecane) lub `/api/ifs/...`.
3. `IFS_AUTO_DISPATCH=0` dopóki Mercato generuje etykiety (PRIMARY).
4. DB: `alembic upgrade head` lub SQL `scripts/migrations/20260527_*.sql`.
5. Worker + beat uruchomione (compose `worker` / `beat`).
6. Smoke ingest: `Create_List_No` → wiersz `shipping_ifs_shipment_queue`, `state=queued`.
7. Smoke dispatch: POST dispatch → `202` + wiersz `ir_outbox` (`target_kind=shipping_label`) → po drain `state=dispatched`.

### Testy

```bash
cd crm-engine/backend
pytest tests/test_ifs_cf_parser.py tests/test_ifs_webhook_route.py tests/test_ifs_outbox_dispatch.py tests/test_ifs_webhook_integration.py -v
```
