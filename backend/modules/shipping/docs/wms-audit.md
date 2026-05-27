# Audyt: Orbiteus vs nowoczesny WMS (twarda ocena)

> **Data:** 2026-05-27  
> **Zakres audytu:** cały produkt Orbiteus (silnik + CRM + moduł `shipping` na branchu kiosk v0.3)  
> **Metoda:** porównanie do **referencyjnego modelu tier-1 WMS** (funkcje, nie nazwy vendorów)  
> **Werdykt w skrócie:** Orbiteus **nie jest WMS** — to silnik aplikacji + CRM + **wysyłkowa stacja pakowania / TMS-lite**. Jako WMS: **2,4/10**. Jako stacja etykiet + integracja IFS: **6,8/10** (po wdrożeniu kiosku).

---

## Kto ocenia (2 eksperci)

| Ekspert | Profil | Ocenia głównie |
|---------|--------|----------------|
| **Ekspert A** | UX magazynu + operacje (kiosk, tempo, błędy) | Skrzynka IFS, AUTO, kiosk DnD, druk, ergonomia |
| **Ekspert B** | Architekt WMS / supply chain | Stany, lokalizacje, przyjęcia, kompletacja, fale, automatyzacja |

Skala **1–10** (twarda):

| Ocena | Znaczenie |
|-------|-----------|
| **9–10** | Poziom najlepszych WMS w danej kategorii (cloud, multi-site, automaty) |
| **7–8** | Solidny mid-market WMS — produkcja bez wstydu |
| **5–6** | Moduł ERP/TMS „doklejony” — da się pracować, brak głębi |
| **3–4** | Prototyp / punktowy moduł |
| **1–2** | Brak lub szkielet |

---

## Referencja: co ma „najnowszy” WMS (checklista)

Używamy uniwersalnej listy funkcji tier-1 / cloud-native WMS (2024–2026):

1. **Master data:** strefy, alejki, regały, biny, slotting, SKU, EAN, UOM, lot/serial, data ważności  
2. **Inbound:** ASN, przyjęcie, jakość, putaway, cross-dock, zwroty przyjęciowe  
3. **Inventory:** stan w czasie rzeczywistym, rezerwacje, blokady, inwentaryzacja cykliczna, ABC  
4. **Outbound:** alokacja, fale, pick (głos/RF), cluster, pack, manifest, załadunek  
5. **Yard / dock:** okna czasowe, bramy, kolejka wozów  
6. **Labor / WES:** normy, produktywność, priorytety zadań  
7. **Automatyzacja:** WCS, conveyor, AGV/AMR, wagomat, skanery Zebra  
8. **TMS / carrier:** etykiety, track, rate shop, multi-carrier (często osobny moduł)  
9. **Analityka:** OTIF, pick rate, fill rate, slotting AI  
10. **Platforma:** multi-tenant, audit, API, eventy, mobile offline  

---

## Co mamy w Orbiteus (fakty z kodu)

| Warstwa | Stan | Uwagi |
|---------|------|--------|
| **Silnik** | Silny | RBAC, audit, outbox+Celery, SSE, AI BYOK, multitenancy |
| **CRM** | ~8/10 jako mini-CRM | Lejek, kanban, AI — nie WMS |
| **Shipping v0.3** | Wdrożone na branchu kiosk | IFS queue, compose-preview, AUTO, kiosk 1–5 listów, DPD/DSV/Geodis native |
| **Moduł inventory / locations** | **Brak** | Brak `stock.quant`, binów, pick list |
| **Moduł orders (ERP)** | **Brak w repo** | `order_id` tylko UUID FK |
| **MES** | **Brak** | — |

---

## Tabela twardych ocen — Orbiteus vs WMS

### Ekspert B (system WMS)

| Obszar WMS | Tier-1 WMS | Orbiteus dziś | Luka |
|------------|------------|---------------|------|
| Lokalizacje / bin / slotting | 10 | **1** | Brak modelu magazynu |
| Stan magazynowy / rezerwacje | 10 | **1** | Brak |
| Przyjęcia / ASN / putaway | 10 | **1** | Brak |
| Kompletacja / fale / pick path | 10 | **1** | Brak |
| Pakowanie operacyjne (carton logic) | 9 | **3** | Tylko HU + etykieta, bez carton ID/cubiscan |
| Manifest / załadunek | 9 | **2** | Śledzenie tracking, bez load plan |
| Yard / dock scheduling | 8 | **1** | Brak |
| Inwentaryzacja / cykle | 9 | **1** | Brak |
| Lot / serial traceability | 9 | **1** | Brak |
| Labor management | 8 | **2** | RBAC user, bez norm |
| Automatyzacja WCS/RF | 9 | **2** | Brak integracji skanerów jako first-class |
| TMS / multi-carrier labels | 8 | **7** | DPD/DSV/Geodis + routing + multi-waybill |
| Integracja ERP (IFS) | 8 | **7** | Webhook IFS + CF parser — mocne dla niszy |
| Analityka operacyjna | 9 | **3** | Audit log, brak WMS KPI |
| API / eventy / multi-tenant | 9 | **8** | Outbox, SSE — silnik na poziomie WMS platform |

**Średnia ważona (cały WMS): 2,4 / 10**  
(Wagi: inventory+pick 40%, inbound 20%, reszta 40%)

### Ekspert A (UX operacyjny — stacja wysyłkowa)

| Obszar | Tier-1 pack station | Orbiteus shipping v0.3 | Ocena |
|--------|---------------------|-------------------------|-------|
| Skrzynka zadań (task queue) | 9 | IFS inbox + filtry | **7** |
| Ścieżka 1-klik (proste przesyłki) | 9 | AUTO + compose-preview | **8** |
| Multi-carton / split shipment | 9 | Kiosk 1–5 waybill + DnD | **7** |
| Wybór przewoźnika | 8 | Per-slot + routing | **7** |
| Feedback błędów kuriera | 8 | state failed + message | **6** |
| Druk etykiet | 9 | PDF/base64, brak ZPL native | **6** |
| Skaner barkodowy / RF UI | 9 | Brak trybu „scan-first” | **3** |
| Głośny tryb kiosk / dotyk 48px | 8 | Zaprojektowane w ux-kiosk | **7** (implementacja częściowa) |
| Offline / reconnect | 7 | SSE + polling | **5** |
| Potwierdzenie zawartości (QC pack) | 8 | Brak scan-verify SKU | **2** |

**Średnia (stacja pakowania / etykiety): 6,8 / 10**

---

## Porównanie do „najlepszych branżowo” — narrative

### Gdzie Orbiteus **przegrywa** (i to normalne)

Nowoczesny WMS żyje na **danych o lokalizacji i ruchu towaru**. Orbiteus nie wie, że paleta stoi w `BAZ-A-12-03` — wie tylko, że z IFS przyszedł `PAL_A` i trzeba wygenerować list DSV.

Bez tego **nie ma**:

- optymalnej kompletacji,
- potwierdzenia „złoty scan”,
- inwentaryzacji,
- slottingu,
- yard management.

To nie jest „brakujący sprint” — to **inny produkt** (dispatch hub vs WMS).

### Gdzie Orbiteus **dorównuje lub wygrywa**

1. **Architektura integracji** — outbox, idempotent dispatch, webhook IFS, tenant RBAC: na poziomie, na który wiele WMS-ów ma słabsze API.  
2. **Multi-waybill + AUTO** — tier-1 WMS często ma pack station, ale split na **wiele listów przewozowych z różnymi kurierami** bywa w TMS, nie w core WMS. Tu macie to jako first-class (v0.3).  
3. **Natywne adaptery kurierów (PL)** — DPD/Schenker/Geodis w Pythonie bez subprocess: **7–8/10** vs typowy „drukuj z TMS”.  
4. **CRM** — WMS nie sprzedaje; Orbiteus ma CRM **8/10** obok — combo ERP+WMS u vendora kosztuje miliony.

### Gdzie jesteście **środku pack**

| Capability | Opis |
|------------|------|
| Handling units z IFS | CF$/PAL_* parser — dobre pod ERP shipping, nie pod WMS stock |
| Routing wagowy | LOGISTICS_* — TMS logic, nie slotting |
| Kiosk UX | Nowoczesny na papierze; brak E2E i scan-first obniża ocenę operacyjną |

---

## Oceny zbiorcze (twarde)

| Perspektywa | Ocena | Komentarz jednym zdaniem |
|-------------|-------|---------------------------|
| **Jako pełny WMS** | **2,4 / 10** | Nie udajcie WMS — nie macie stocku ani picku. |
| **Jako moduł wysyłki / pack station** | **6,8 / 10** | Sensowny kiosk + IFS + kurierzy; brakuje skanów, ZPL, QC. |
| **Jako silnik pod budowę WMS** | **7,5 / 10** | Registry, RBAC, audit, outbox — lepsza baza niż custom PHP. |
| **Jako produkt „ERP+CRM+shipping” dla MDM** | **7,0 / 10** | Dopasowanie do IFS i PL carriers; orders/inventory osobno. |
| **Gotowość produkcyjna shipping v0.3** | **6,5 / 10** | Kod jest; brak pełnego E2E, retry, ir_attachment, load test. |

### Ranking pozycjonowania (nie ocena jakości kodu)

```
Tier-1 WMS (referencja)          ████████████████████ 10
Mid-market WMS                   ███████████████      7,5
Orbiteus — stacja etykiet        ███████              6,8
Typowy ERP shipping bolt-on      █████                5
Orbiteus — jako WMS ogółem      ██                   2,4
```

---

## Macierz: funkcja WMS → moduł Orbiteus

| Funkcja WMS | Moduł / ścieżka | Status |
|-------------|-----------------|--------|
| Przyjęcie towaru | — | ❌ |
| Kompletacja | — | ❌ |
| Stany | — | ❌ |
| Pack & ship | `shipping` + kiosk | ✅ częściowo |
| Etykiety kuriera | `shipping` adapters | ✅ |
| Integracja ERP ship | `ifs_queue` webhook | ✅ |
| Sprzedaż / CRM | `crm` | ✅ |
| Portal klienta | `portal-ui` | ✅ szkielet |
| AI asystent | `orbiteus_core.ai` | ✅ |

---

## Track B — spec i taski WMS (Ekspert B)

Ocena **2,4/10** jako pełny WMS jest **punktem wyjścia** do programu modułu `inventory` (nie rozszerzenia `shipping`).

| Dokument | Ścieżka |
|----------|---------|
| Indeks modułu | [`backend/modules/inventory/docs/README.md`](../../inventory/docs/README.md) |
| Kontrakt **WMS-001..015** | [`backend/modules/inventory/docs/spec.md`](../../inventory/docs/spec.md) |
| Taski **WMS-T01..T27** | [`backend/modules/inventory/docs/tasks.md`](../../inventory/docs/tasks.md) |
| ADR granice pack vs WMS | [`../../../docs/adr/0018-shipping-pack-station-not-wms.md`](../../../docs/adr/0018-shipping-pack-station-not-wms.md) |

**Mapowanie audyt → spec:** każdy wiersz tabeli Eksperta B (lokalizacje, stan, przyjęcia, kompletacja, …) ma odpowiadające **WMS-00x** w `spec.md` i **WMS-Txx** w `tasks.md`.

**Handoff do wysyłki:** WMS-T15 / WMS-T16 + **SHP-T30** w `shipping/docs/tasks.md` — event `inventory.ready_to_ship.created`, bez importów między modułami.

---

## Rekomendacje strategiczne (obie ekspertyzy)

### Nie róbcie

- Marketingu „Orbiteus = WMS” — stracicie zaufanie operacji magazynowej.

### Róbcie

1. **Nazwa produktu:** „Shipping Dispatch / Pack Station” albo „Outbound Labels” — jasna nisza.  
2. **Dociągnięcie do 8/10 pack station:** scan-first UI, ZPL, retry waybill, Playwright E2E, potwierdzenie wagi z wagi RS232 (opcjonalnie).  
3. **Osobny moduł `inventory` (przyszłość):** jeśli celem jest WMS — zacząć od `stock.location` + `stock.move` + pick list, nie od etykiet.  
4. **Integracja z istniejącym WMS klienta:** Orbiteus jako **warstwa etykiet** pod WMS/RMS klienta (API + webhook) — realistyczny go-to-market.

---

## Podsumowanie ekspertów

**Ekspert A (UX):**  
„Kiosk i AUTO to **nowoczesna** myśl jak w dobrych pack station (7–8/10 UX concept). Bez skanera i QC pack nie wejdziecie na halę tier-1. Dla MDM spedycji z IFS — **wystarczające**, dla pełnego magazynu — **nie**.”

**Ekspert B (WMS):**  
„Orbiteus **nie jest WMS** (2,4/10). Jest **silnikiem** z dobrym TMS/shipping slice (7/10 integracje kurierów). Porównanie do Manhattan / Blue Yonder / SAP EWM jest nieuczciwe wobec was; porównanie do modułu **Shipping Label** w mid ERP — **wygrywacie architekturą**, przegrywacie magazynem.”

---

## Załącznik: co podnosi ocenę do 8/10 (tylko shipping)

| # | Inicjatywa | Wpływ |
|---|------------|-------|
| 1 | Scan-first (IFS id / order / HU) | +0,5 UX |
| 2 | ZPL + drukarka zebra | +0,4 UX |
| 3 | Playwright E2E AUTO + 3-waybill | +0,3 jakość |
| 4 | Retry + dead-letter UI | +0,3 ops |
| 5 | Moduł `orders` minimal (nagłówek zamówienia) | +0,2 product |

**Teoretyczny sufit pack station bez WMS stock: ~8,2/10.**

---

*Dokument audytowy — nie zmienia scope modułu `shipping` bez ADR.*
