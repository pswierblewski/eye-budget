# Zapis poprawek paragonu i wyjątki auto-potwierdzenia — design

**Status:** zatwierdzony (brainstorming 2026-10-01)  
**Data:** 2026-10-01  
**Kontekst:** Przy `to_confirm` użytkownik poprawia OCR (np. złą kwotę pozycji), ale jedyną akcją trwałą jest „Potwierdź paragon”. Auto-check czyta `receipts_scans.result` z bazy, więc poprawki w formularzu nie wchodzą w „Sprawdź auto-potwierdzenie”. Dodatkowo twarde blokery (np. `low_confidence` 85% przy progu 90%) nie dają ścieżki „akceptuję ryzyko na tym paragonie”.

## Decyzje użytkownika (zamknięte)

| Temat | Decyzja |
|-------|---------|
| Wyjątki auto-potwierdzenia | **Tylko bieżący paragon** (nie globalny próg ani reguła na przyszłość) |
| Zapis bez confirm | **OCR (`result`) + wybrane kategorie** (`category_selections`); kandydaci algorytmu nadal w `categories_candidates` |
| Które powody można zaakceptować | **Dowolny** blocking (`sum_mismatch`, `no_category`, `low_confidence`, `evaluation_error`, `confirm_failed`, …) |
| Po „Zapisz poprawki” | **Automatyczny dry-run** auto-potwierdzenia (jak „Sprawdź auto-potwierdzenie”) |
| Podejście API | **Jedna operacja** `save-review` (zapis + kategoryzacja + evaluate dry-run); waiver w osobnym endpoincie z dry-run w odpowiedzi |
| Copy UI przy powodzie | Przycisk **„Akceptuj”** (krótko) |

## UX (`/receipts/[id]`, status `to_confirm`)

1. **„Zapisz poprawki”** (secondary) obok **„Potwierdź paragon”**  
   - Zapisuje pola jak przy confirm (vendor, date, total, products, normalizacje, mapa kategorii).  
   - Status pozostaje `to_confirm`.  
   - Po sukcesie: automatyczny dry-run auto-potwierdzenia — odświeżone powody / komunikat sukcesu bez drugiego kliknięcia.

2. **Panel „Dlaczego nie potwierdzono automatycznie”**  
   - Przy każdej linii z `blocking: true` i bez waivu: **„Akceptuj”**.  
   - Po zaakceptowaniu: linia oznaczona jako zaakceptowana (bez ponownego „Akceptuj”); przy kolejnym evaluate traktowana jako nieblokująca.  
   - `vendor_new` pozostaje nieblokujący (bez zmian).

3. **Auto-potwierdzenie** — istniejące przyciski; po zapisie i waivers „Potwierdź automatycznie” działa, gdy nie ma niezaakceptowanych blockerów.

4. **Wybór kategorii** — po zapisie i po F5 UI pokazuje **zapisany** wybór z `category_selections`, nie tylko top kandydata z `categories_candidates`.

## Dane (Yoyo)

Plik migracji (jedna sprawa): kolumny na `receipts_scans`:

| Kolumna | Typ | Zawartość |
|---------|-----|-----------|
| `auto_confirm_waivers` | JSONB NULL | `[{ "code": string, "product_name"?: string }]` |
| `category_selections` | JSONB NULL | `{ [raw_product_name: string]: category_id: number }` |

Identyfikacja waivu:

- `sum_mismatch`, `evaluation_error`, `confirm_failed`: dopasowanie po `code` tylko.
- `low_confidence`, `no_category`: `code` + `product_name` (surowa nazwa pozycji).

**Reopen:** czyści `auto_confirm_waivers` i `category_selections`.  
**Po confirm (`manual` / `auto`):** opcjonalnie wyczyścić `category_selections` (stan w transakcji); waivers nieistotne.

## API

Kontrakt w czterech miejscach: `main.py`, `data.py`, proxy Next.js, `lib/api.ts` + `types.ts`.

### `POST /receipts/{scan_id}/save-review`

**Body:** rozszerzenie wzorca `ConfirmReceiptRequest` — te same opcjonalne override’y OCR/normalizacji; **`product_categories`** (mapa surowa nazwa → `category_id`) wymagana w praktyce gdy użytkownik ma wybory (FE wysyła aktualny stan formularza).

**Serwer (kolejność):**

1. Walidacja: skan istnieje, `to_confirm`, `result` niepuste.  
2. Zapis `result` (`set_result_by_id`), normalizacje vendor/product (jak w `confirm_receipt`, bez tworzenia transakcji).  
3. Zapis `category_selections`.  
4. Kategoryzacja (`ReceiptCategorizationService`) + aktualizacja `categories_candidates` (jak rescore).  
5. `evaluate(..., waivers)` — dry-run tylko: ustaw `auto_confirm_reasons`, **nie** confirm.  
6. `get_receipt_by_id` + payload auto-check.

**Response:** `SaveReviewResponse` — `{ receipt: ReceiptScanDetail, auto_confirm: SingleAutoConfirmResult }` (dry_run=true w embedzie).

### `POST /receipts/{scan_id}/auto-confirm-waiver`

**Body:** `{ code: string, product_name?: string | null }`.

**Serwer:** append idempotentny do `auto_confirm_waivers`; dry-run auto-check; zwrot jak wyżej (`receipt` + `auto_confirm`) **lub** minimalnie `SingleAutoConfirmResult` + invalidacja receipt po stronie FE — **preferencja:** pełny `receipt` w odpowiedzi.

Istniejący `POST .../auto-confirm` — wczytuje waivers z DB; przy `dry_run=false` używa `category_selections` do zbudowania `ConfirmReceiptRequest`, gdy mapa istnieje.

## Bramka `evaluate`

- Nowy parametr: zbiór waivers `(code, product_name | None)`.
- Wygenerowany powód pasujący do waivu: **`blocking: false`** (opcjonalnie `waived: true` w modelu API dla UI).
- `ok` gdy brak pozostałych `blocking: true`.

## Edge case’y

| Sytuacja | Zachowanie |
|----------|------------|
| Poprawiona kwota, zapis | `sum_mismatch` znika po re-evaluate; waiver zwykle niepotrzebny |
| Akceptuj `sum_mismatch` mimo rozjazdu | Dozwolone (decyzja C); auto-confirm może przejść po waivie — użytkownik świadomie |
| Zapis bez pełnych kategorii | BE/FE: spójnie z confirm — jeśli brakuje kategorii dla pozycji, save-review może 422 lub zapisać OCR i zwrócić `no_category` w auto_confirm |
| Re-kategoryzacja po zapisie | Nadpisuje `categories_candidates`; **`category_selections`** utrzymuje wybór użytkownika w UI i przy auto-confirm |
| Duplikat „Akceptuj” | Idempotentny zapis waivu |
| Confirm ręczny | `confirmation_source=manual`; selections z requestu jak dziś |

## Testy

**Backend (unit):**

- `evaluate` z waivers — `low_confidence` per product, `sum_mismatch` global.  
- `save_review` — zapis `result` + selections, status unchanged, dry-run nie woła `_apply_auto_confirm`.  
- `try_auto_confirm` z waivers + `category_selections` przy force confirm.  
- Reopen czyści nowe kolumny.

**Backend (integration):** route save-review + waiver (404/409, happy path z mock App lub migrated DB).

**Frontend:** schema parse; panel „Akceptuj”; save-review mutation + restore selections from detail.

## Wersjonowanie

**MINOR** (nowe endpointy, pola JSONB wstecznie opcjonalne): BE i FE podbić niezależnie (np. BE 1.12.0, FE 1.11.0).

## Poza zakresem

- Globalne obniżenie progu AI lub reguły per produkt na przyszłe paragony.  
- Automatyczny zapis draftu bez kliknięcia (debounce).  
- Edycja pozycji na już potwierdzonym paragonie (istniejący flow `PATCH items`).

## Następny krok

Po akceptacji tego pliku: plan implementacji (`writing-plans` → `docs/superpowers/plans/2026-10-01-receipt-save-review-waivers.md`).
