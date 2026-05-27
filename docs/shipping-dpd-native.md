# Shipping — natywny DPD Poland (Orbiteus crm-engine)

**Status:** wdrożony w Testorbiteka (Python, bez subprocess Mercato)  
**Źródło prawdy Mercato:** `mercato/.ai/specs/SPEC-003-DPD.md`, `mercato-shipping-hub/src/carrier/dpd-carrier.ts`

## Cel

Integracja **DPD Poland** jako hybryda **REST** (waybille) + **SOAP** (etykiety) — port `DpdPythonAdapter`, analogicznie do `GeodisPythonAdapter` / `DsvPythonAdapter`.

Kod rejestru: `DPD`.

## Architektura

```
POST /api/shipping/dispatch  (202 Accepted)
  → ir_outbox (target_kind=shipping_label)
  → Celery → execute_dispatch_for_order() → adapter.create_label()
  → REST generatePackagesNumbers → SOAP generateSpedLabelsV4
```

Przy `SHIPPING_DPD_NATIVE=0` pozostaje `MercatoHubAdapter` (Node subprocess).

## API

| Krok | Transport | Operacja |
|------|-----------|----------|
| Waybille | REST | `POST …/public/shipment/v1/generatePackagesNumbers` |
| Etykiety | SOAP | `generateSpedLabelsV4` na PackageObjServices |

| Środowisko | REST base | SOAP |
|------------|-----------|------|
| test | `https://dpdservicesdemo.dpd.com.pl/public` | `…demo…/DPDPackageObjServices` |
| prod | `https://dpdservices.dpd.com.pl/public` | `…dpdservices…/DPDPackageObjServices` |

Auth: HTTP Basic (`DPD_LOGIN`/`DPD_PASSWORD`) + nagłówek `X-DPD-FID` (`DPD_MASTER_FID`). Body: `payerFID` (= `DPD_FID` lub master).

## Nadawca z kontraktu IFS

| Prefiks | Site | Profil |
|---------|------|--------|
| `BIS`, `BIS^01` | Bielsko | `ifs_dispatch_profiles` |
| `CIE`, `CIE^01` | Cieszyn | j.w. |
| `BAZ`, `BAZ^01` | Bażanowice | j.w. |

Bez kontraktu: `DPD_SENDER_*` z env (domyślnie MDM NT Bielsko).

## Zmienne środowiskowe

| Zmienna | Wymagane | Domyślnie |
|---------|----------|-----------|
| `DPD_LOGIN` | **TAK** | — |
| `DPD_PASSWORD` | **TAK** | — |
| `DPD_MASTER_FID` | **TAK** | — |
| `DPD_FID` | nie | = `DPD_MASTER_FID` |
| `DPD_ENV` | nie | `test` |
| `DPD_ENDPOINT` | nie | auto z env |
| `DPD_SOAP_URL` | nie | auto z env |
| `DPD_LABEL_FORMAT` | nie | `PDF` |
| `SHIPPING_DPD_NATIVE` | nie | `1` |

Sync z Mercato: `.\scripts\sync-carrier-env-from-mercato.ps1`

## Pułapki

- Etykiety **tylko SOAP** — REST `generateSpedLabels` na demo zwraca HTTP 422.
- Testy **wyłącznie** `DPD_ENV=test` — PROD po jawnej zgodzie.
- REST nie akceptuje pustych stringów w polach kontaktowych — wysyłamy `null`.
- Kod pocztowy bez myślników (`43346` nie `43-346`).

## Testy

### Unit (bez HTTP)

```bash
cd crm-engine/backend
pytest tests/test_dpd_native.py -v
```

### Smoke — 9 etykiet (3 magazyny × 3 scenariusze paczki)

```bash
cd crm-engine/backend
python scripts/dpd_orbiteus_smoke.py       # domyślnie 9
python scripts/dpd_orbiteus_smoke.py 3     # szybki (1 per magazyn, scenariusz S)
```

Macierz: BIS/CIE/BAZ × S (5.5 kg) / M (15 kg) / L (31 kg). PDF: `dpd-label-{waybill}.pdf`.

## Pliki

| Plik | Rola |
|------|------|
| `lib/adapters/dpd_adapter.py` | `DpdPythonAdapter.create_label()` |
| `lib/adapters/dpd/client.py` | REST + orchestracja SOAP |
| `lib/adapters/dpd/soap_labels.py` | `generateSpedLabelsV4` |
| `lib/adapters/dpd/config.py` | env, endpoints |
| `lib/adapters/dpd/auth.py` | credentials |
| `lib/carrier_registry.py` | `SHIPPING_DPD_NATIVE` |
| `scripts/dpd_orbiteus_smoke.py` | smoke 9/9 |

Rollout VM: [TASK-DPD-NATIVE-VM.md](./TASK-DPD-NATIVE-VM.md)
