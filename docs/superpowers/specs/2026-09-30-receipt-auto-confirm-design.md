# Automatyczne potwierdzanie paragonów na podstawie historii (etap 1) — design

**Status:** zatwierdzony (brainstorming 2026-09-30)  
**Data:** 2026-09-30  
**Kontekst:** Paragony w statusie `to_confirm` zalegają, bo potwierdzanie jest w pełni ręczne. Większość historycznych paragonów jest potwierdzona, więc kategorie nowych produktów można w dużej mierze wywnioskować z historii. Obecnie `CategoriesService` nie widzi historii (tylko listę kategorii + paragon), a normalizacja produktów (`ProductsService`) wymyśla nazwę od zera, bez znajomości istniejących produktów.

## Decyzje użytkownika (zamknięte)

| Temat | Decyzja |
|-------|---------|
| Poziom autonomii | Auto-potwierdzanie **tylko pewnych** paragonów; reszta zostaje do ręcznego przeglądu |
| Zaległe paragony | Jednorazowe **przeliczenie nowym mechanizmem** (z historią), uruchamiane ręcznie, z trybem próbnym |
| Warunki | Suma produktów = total (**twardy**); sklep z historią potwierdzeń (**miękki**, nie blokuje); każdy produkt z kategorią z historii lub AI ≥ próg (**twardy**); data i limit kwoty — **bez znaczenia** |
| Normalizacja produktów | Wymagana poprawa (dopasowanie przybliżone + wybór z istniejących produktów) |
| Podejście | **A** — najpierw historia, LLM z przykładami tylko dla produktów bez werdyktu historii |
| Zakres | Etap 1 (ten spec). Etap 2 — weryfikacja drugim odczytem na wycinkach obrazu — osobny spec |

## Architektura

### Nowe / zmienione serwisy (`backend/src/services/`)

- **`product_resolver.py`** — surowa nazwa → `product_id`:
  1. dokładne dopasowanie w `products_alternative_names`,
  2. dopasowanie przybliżone do znanych nazw surowych (`pg_trgm`; toleruje błędy OCR, np. Ł/L) — przy podobieństwie **≥ 0.85** najlepszy kandydat jest przyjmowany bez LLM,
  3. w pozostałych przypadkach LLM (jedno wywołanie na paragon): nazwa + krótka lista (top 10, podobieństwo ≥ 0.3) najbliższych istniejących produktów → wybór istniejącego `product_id` (tylko spośród podanych kandydatów) albo nowa znormalizowana nazwa.
  Zastępuje obecne wywołanie `ProductsService.process_products` w pipeline. Nowy produkt jest wstawiany do `products` + `products_alternative_names` jak dotąd.
- **`category_history.py`** — dla `product_id` zwraca rozkład potwierdzonych kategorii z `receipt_transaction_items` (np. `{Nabiał: 14, Słodycze: 1}`) i werdykt: kategoria dominująca, jeśli `count ≥ HISTORY_MIN_COUNT` i `share ≥ HISTORY_MIN_SHARE`; w przeciwnym razie brak werdyktu.
- **`CategoriesService`** (rozszerzony) — wywoływany jednym zapytaniem na paragon **tylko** dla produktów bez werdyktu historii. Prompt zawiera kilka podobnych potwierdzonych pozycji (few-shot, dobór przez podobieństwo nazw) oraz nazwę sklepu. Jeśli wszystkie produkty mają werdykt historii — brak wywołania LLM.
- **`receipt_auto_confirm.py`** — czysta funkcja `evaluate(receipt, resolutions, vendor_has_history) -> AutoConfirmDecision(ok: bool, reasons: list[str])`. Bez dostępu do DB.

### Reguły `evaluate`

- **Twarde (wszystkie muszą przejść):**
  - `|Σ product.price − total| ≤ 0.01` (rabaty to pozycje z ujemną ceną — wliczają się naturalnie),
  - każdy produkt ma kategorię z `source=history` albo `source=ai` z `confidence ≥ MIN_AI_CONFIDENCE`.
- **Miękkie (tylko informacja w `reasons`, nie blokuje):** sklep bez wcześniejszego potwierdzonego paragonu.
- Powód to obiekt `{code, message, blocking}`; `message` po polsku, np. `"Suma produktów 47,30 zł ≠ 49,99 zł"`, `"Nowy produkt „SER KOZI 150G”: pewność AI 62%"`. Kody: `sum_mismatch`, `no_category`, `low_confidence`, `vendor_new` (nieblokujący), `evaluation_error`, `confirm_failed`. Kod służy do agregacji w raporcie przeliczenia.
- Kandydaci AI z `category_id` spoza listy kategorii wydatków są odrzucani (inaczej auto-potwierdzenie zgubiłoby pozycję na kluczu obcym).

### Konfiguracja (env, dokumentowana w `.env.example`)

| Zmienna | Domyślnie |
|---------|-----------|
| `RECEIPT_AUTO_CONFIRM_ENABLED` | `false` |
| `RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE` | `0.9` |
| `RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT` | `2` |
| `RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE` | `0.9` |

Domyślnie wyłączone — użytkownik włącza po przejrzeniu raportu z trybu próbnego.

## Zmiany w bazie (Yoyo, jedna sprawa na plik)

1. `CREATE EXTENSION IF NOT EXISTS pg_trgm` + indeks GIN (`gin_trgm_ops`) na `products_alternative_names.name`. Jeśli rozszerzenie niedostępne (brak uprawnień na zewnętrznym Postgresie) — resolver przechodzi na `rapidfuzz` w Pythonie na liście nazw w pamięci i loguje ostrzeżenie.
2. `receipts_scans.confirmation_source TEXT NULL` (`'manual' | 'auto'`, `CHECK`), `NULL` dla niepotwierdzonych.
3. `receipts_scans.auto_confirm_reasons JSONB NULL` (lista obiektów `{code, message, blocking}`).
4. `prompt_analytics.auto_confirm_reverted BOOLEAN NOT NULL DEFAULT FALSE`.

`categories_candidates` (JSONB, bez migracji): każdy produkt dostaje opcjonalne `source: "history" | "ai"`, `product_id`, `history_count`.

## Przepływ danych

### Nowy paragon (`_run_production_async`, `_process_single_file`)

1. OCR → `validate_ocr_payload` → normalizacja sklepu (bez zmian).
2. `product_resolver` dla każdego produktu.
3. `category_history` → werdykty; reszta → `CategoriesService` (z few-shot).
4. Zapis `categories_candidates` (z `source`, `product_id`, `history_count`); lokalizacja tekstu (bez zmian).
5. Jeśli `RECEIPT_AUTO_CONFIRM_ENABLED`: `evaluate(...)`.
   - **ok** → istniejące `confirm_receipt` z `product_categories` z najlepszych kandydatów i znormalizowanymi nazwami, `confirmation_source='auto'`. Auto-link bank/gotówka i analityka działają jak przy ręcznym potwierdzeniu. **Ground truth zapisuje się tylko przy potwierdzeniu ręcznym** — niezweryfikowany OCR nie może trafiać do zbioru, którym oceniamy OCR.
   - **nie ok** → status `to_confirm`, `auto_confirm_reasons` zapisane.
   - Pusher `receipt.progress` dostaje pole `auto_confirmed: bool`.

`evaluate` uruchamia się zawsze, także przy wyłączonej fladze — flaga steruje tylko samym potwierdzeniem. Dzięki temu UI pokazuje powody od razu.

### Ręczne potwierdzenie

- Ustawia `confirmation_source='manual'`.
- Jeśli użytkownik poda znormalizowaną nazwę inną niż obecne mapowanie surowej nazwy — mapowanie w `products_alternative_names` / `vendors_alternative_names` jest **nadpisywane** (dziś pierwsze przypisanie zostaje na zawsze).

### „Otwórz ponownie”

- Czyści `confirmation_source`. Jeśli było `auto` → `prompt_analytics.auto_confirm_reverted = TRUE` (miara błędów automatu do strojenia progów).

### Przeliczenie zaległych

- Celery `rescore_pending_receipts(dry_run: bool)` + `POST /receipts/rescore?dry_run=true|false` → `task_id`.
- Zakres: `status='to_confirm'` z niepustym `result`. **Bez ponownego OCR** — kroki 2–5.
- `dry_run=true`: zapisuje nowych kandydatów i `auto_confirm_reasons`, nic nie potwierdza; raport: liczba paragonów, ile przeszłoby, najczęstsze powody blokady.
- `dry_run=false`: jak wyżej + potwierdza paragony z `ok` (niezależnie od `RECEIPT_AUTO_CONFIRM_ENABLED` — to jawna akcja użytkownika).
- Przed potwierdzeniem ponowna kontrola statusu (pomiń, jeśli w międzyczasie potwierdzony ręcznie).
- Postęp przez Pusher (`receipt.rescore_progress`); raport w zdarzeniu `receipt.rescore_done` oraz jako wynik zadania Celery (dostępny przez istniejące `GET /tasks/{task_id}`). Tabela `task_runs` nie jest używana w kodzie i nie ma kolumny na wynik — nie korzystamy z niej.

## Kontrakt API (wszystkie cztery miejsca: `main.py`, `data.py`, `route.ts`, `api.ts` + `types.ts`)

Wszystkie pola nowe i opcjonalne — zgodność wsteczna.

- `ReceiptScanListItem`, `ReceiptScanDetail`: `confirmation_source`, `auto_confirm_reasons`.
- `GET /receipts`: filtr `confirmation_source=auto|manual`.
- Kandydat kategorii: `source`, `product_id`, `history_count`.
- `POST /receipts/rescore?dry_run=` → `{ task_id }`; nowy route handler `frontend/app/api/receipts/rescore/route.ts`.

## UI (tylko prymitywy z `components/ui`, copy PL)

- **`/receipts`:** `Badge` „Auto” przy paragonach z `confirmation_source='auto'`; filtr/zakładka „Potwierdzone automatycznie”. Przycisk „Przelicz oczekujące” → `Modal`: uruchamia tryb próbny, pokazuje raport („32 z 47 potwierdziłoby się samo; najczęstsze blokady: …”) i przycisk „Potwierdź automatycznie 32”.
- **`/receipts/[id]`:**
  - `to_confirm`: sekcja „Dlaczego nie potwierdzono automatycznie” z listą powodów,
  - przy każdym produkcie `Pill` ze źródłem: „z historii (14×)” / „AI · 62%”,
  - auto-potwierdzony: informacja „Potwierdzony automatycznie” obok istniejącego „Otwórz ponownie”.
- Błędy API przez `QueryState` / `MutationErrorNotice`.

## Obsługa błędów

- Wyjątek w resolverze lub historii → fallback do obecnej ścieżki (LLM normalizacja + LLM kategorie dla wszystkich), bez auto-potwierdzenia, powód „Nie udało się ocenić automatycznie”. Pipeline paragonu nie może się przerwać.
- `confirm_receipt` nie jest transakcyjny (commit na krok). Jeśli auto-potwierdzenie zwróci `None` lub rzuci wyjątek → `transactions_repository.delete_by_scan_id`, status `to_confirm`, powód zapisany.
- Brak `pg_trgm` → `rapidfuzz` + log.

## Testy

- **Unit (AAA, `make_app()`):** `evaluate` (suma, tolerancja, rabaty, progi AI, brak historii, miękki warunek sklepu); werdykty `category_history` (progi count/share); `product_resolver` (dokładne / przybliżone / LLM mock / `new`); gałęzie pipeline z i bez auto-potwierdzenia; nadpisanie mapowań przy ręcznym potwierdzeniu; `reopen` ustawia `auto_confirm_reverted`; rescore pomija paragony potwierdzone w międzyczasie.
- **Integracyjne (testcontainers PG16):** migracje (`pg_trgm`), dopasowanie przybliżone na realnej bazie, `rescore` w trybie próbnym.
- **Frontend (Vitest):** schematy Zod dla nowych pól, render powodów i źródeł kategorii.

## Wersje

- Backend: 1.10.0 → **1.11.0** (MINOR).
- Frontend: 1.9.0 → **1.10.0** (MINOR).

## Poza zakresem

- Etap 2: weryfikacja drugim odczytem na wycinkach (`text_regions`) jako dodatkowy warunek.
- Scalanie istniejących duplikatów w `products`.
- Pełna transakcyjność `confirm_receipt`.
