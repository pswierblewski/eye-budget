# Domyślne sortowanie paragonów po dacie — design

**Status:** zatwierdzony (brainstorming 2026-08-18)  
**Data:** 2026-08-18  
**Kontekst:** Lista paragonów (`/receipts`) domyślnie sortuje po `id` malejąco. Użytkownik chce widzieć najpierw najnowsze paragony według **daty zakupu z OCR** (kolumna „Data”), z uploadami bez daty na początku listy.

## Decyzje użytkownika (zamknięte)

| Temat | Wybór |
|--------|--------|
| Kryterium sortowania | **A** — data zakupu z paragonu (OCR, kolumna „Data”) |
| Zakres zmiany | **B** — strona `/receipts`, domyślny parametr w `listReceipts()` (`api.ts`), endpoint `GET /receipts`, repozytorium |
| Paragony bez daty | **B** — na **początku** listy (świeże uploady bez OCR widoczne od razu) |
| Podejście techniczne | **1** — zmiana domyślnych parametrów + `NULLS FIRST` przy `date DESC`; bez castu na `date` w SQL |

## Cel

Ustawić domyślne sortowanie listy paragonów na **datę malejąco** (najnowsze u góry), spójnie w całym stacku API, z paragonami bez daty na początku listy.

## Zachowanie (sekcja 1)

| Aspekt | Decyzja |
|--------|---------|
| Domyślne sortowanie | `sort_by=date`, `sort_dir=desc` |
| Paragony bez daty | Na początku listy przy domyślnym sortowaniu (`NULLS FIRST` przy `date DESC`) |
| Sortowanie ręczne | Użytkownik nadal może sortować po ID, pliku, sklepie, sumie, statusie — bez regresji |
| Kolumna w UI | Nagłówek „Data” pokazuje aktywny sort przy pierwszym wejściu na stronę |
| Kierunek `date ASC` | Paragony bez daty na **końcu** (`NULLS LAST`) — spójne z oczekiwaniem przy rosnącym sortowaniu |

## Zmiany techniczne (sekcja 2)

### Frontend

**`frontend/app/receipts/page.tsx`**
- `useState("id")` → `useState("date")` dla `sortBy`

**`frontend/lib/api.ts`**
- W `listReceipts()`: default `sort_by = "id"` → `sort_by = "date"` (`sort_dir = "desc"` bez zmian)

### Backend

**`backend/src/main.py`**
- Endpoint `GET /receipts`: `sort_by: str = "id"` → `"date"`

**`backend/src/repositories/receipts_scans.py`**
- Default `sort_by` w `get_all()`: `"id"` → `"date"`
- Fallback przy nieznanym `sort_by`: `"date"` zamiast `"id"`
- Logika `ORDER BY`:
  - `sort_by == "date"` i `sort_dir == "desc"` → `{order_expr} DESC NULLS FIRST`
  - W pozostałych przypadkach → `{order_expr} {direction} NULLS LAST` (jak dziś)

**`backend/src/app.py`**
- Default w delegacji `get_all_receipts()`: `"id"` → `"date"`

### Bez zmian

- `LinkReceiptSearchModal` — już wymusza `sort_by: "date", sort_dir: "desc"`
- `receipts/[id]/page.tsx` — nawigacja prev/next sortuje po `id` lokalnie w kliencie; bez wpływu
- Brak migracji DB; brak zmian kontraktu API (tylko domyślne query params)

## Błędy (sekcja 3)

Bez zmian — istniejący `QueryState` / `QueryErrorNotice` na stronie paragonów.

## Testy i weryfikacja (sekcja 4)

### Testy jednostkowe (backend)

**`backend/tests/unit/test_receipts_scans_repository.py`**

1. **`test_get_all_default_sorts_by_date_desc`** — `get_all()` bez parametrów sortu; SQL zawiera `ORDER BY rs.result->>'date' DESC NULLS FIRST`
2. **`test_get_all_date_asc_nulls_last`** — `get_all(sort_by="date", sort_dir="asc")`; SQL zawiera `NULLS LAST`

### Weryfikacja manualna

1. `/receipts` — kolumna „Data” ma aktywną strzałkę ↓
2. Najnowsze daty u góry (poniżej wierszy bez daty); paragony pending/processing bez daty nad datowanymi
3. Kliknięcie innego nagłówka (np. ID) — sort działa jak wcześniej
4. Modal „Wyszukaj paragon” — bez regresji

## Proces wydania (implementacja)

Zgodnie z `AGENTS.md` — **PATCH** frontend i backend (zmiana domyślnego zachowania, bez nowej funkcji użytkowej):

- `frontend/package.json` + `frontend/package-lock.json`
- `backend/src/version.py` + `backend/tests/unit/test_version.py`

---

*Po akceptacji tego pliku następny krok: plan implementacji (`writing-plans`), nie implementacja w tej samej turze spec.*
