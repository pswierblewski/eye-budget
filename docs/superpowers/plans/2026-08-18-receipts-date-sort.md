# Domyślne sortowanie paragonów po dacie — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ustawić domyślne sortowanie listy paragonów na datę zakupu (OCR) malejąco, spójnie w backendzie i frontendzie, z paragonami bez daty na początku listy.

**Architecture:** Zmiana domyślnych wartości `sort_by` z `"id"` na `"date"` w repozytorium, warstwie `App`, endpoincie FastAPI, kliencie API i stanie strony `/receipts`. W repozytorium dodajemy warunkowe `NULLS FIRST` tylko dla `sort_by == "date"` i `sort_dir == "desc"`; pozostałe kolumny/kierunki zostają przy `NULLS LAST`. Bez migracji DB i bez zmian kontraktu API.

**Tech Stack:** Python 3.11.7 / FastAPI / psycopg2 (backend), Next.js 14 / React 18 / TypeScript / React Query v5 (frontend), pytest (testy jednostkowe backendu).

**Spec:** `docs/superpowers/specs/2026-08-18-receipts-date-sort-design.md`

## Global Constraints

- UI copy: polski (bez zmian w tym zadaniu).
- SemVer PATCH po ukończeniu: `frontend/package.json` + `frontend/package-lock.json` (root i `packages[""].version`); `backend/src/version.py` (`VERSION`).
- Brak migracji DB; brak nowych endpointów.
- Nie modyfikuj `.env` / `.env.agent`.
- Testy backendu: `cd backend && ../venv/bin/python -m pytest tests/unit/ -m unit -q`.

---

## Pliki objęte zmianą

| Plik | Odpowiedzialność |
|------|------------------|
| `backend/src/repositories/receipts_scans.py` | Domyślny sort + `NULLS FIRST/FIRST` w SQL |
| `backend/tests/unit/test_receipts_scans_repository.py` | Testy sortowania SQL |
| `backend/src/app.py` | Domyślny parametr delegacji |
| `backend/src/main.py` | Domyślny query param endpointu |
| `frontend/lib/api.ts` | Domyślny `sort_by` w `listReceipts()` |
| `frontend/app/receipts/page.tsx` | Domyślny stan `sortBy` |
| `frontend/package.json` / `frontend/package-lock.json` | PATCH wersji FE |
| `backend/src/version.py` | PATCH wersji BE |

**Bez zmian:** `LinkReceiptSearchModal.tsx` (już wymusza `date desc`), `receipts/[id]/page.tsx` (prev/next sortuje po `id` lokalnie).

---

### Task 1: Repozytorium — testy sortowania (TDD)

**Files:**
- Modify: `backend/tests/unit/test_receipts_scans_repository.py` (sekcja `get_all tests`, po `test_get_all_happy_path`)

**Interfaces:**
- Consumes: `make_repo()` helper z tego samego pliku testowego.
- Produces: oczekiwane zachowanie `ReceiptsScansRepository.get_all()` — domyślnie `ORDER BY rs.result->>'date' DESC NULLS FIRST`.

- [ ] **Step 1: Dodaj test domyślnego sortowania**

W `backend/tests/unit/test_receipts_scans_repository.py`, zaraz po `test_get_all_happy_path`, dodaj:

```python
@pytest.mark.unit
def test_get_all_default_sorts_by_date_desc():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", "processed", "Lidl", "2025-01-01", "50.0", ["tag1"], 100, True, 1),
        ]
    )

    # Act
    repo.get_all(limit=50, offset=0)

    # Assert
    sql = cursor.execute.call_args[0][0]
    assert "ORDER BY rs.result->>'date' DESC NULLS FIRST" in sql


@pytest.mark.unit
def test_get_all_date_asc_nulls_last():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", "processed", "Lidl", "2025-01-01", "50.0", [], None, False, 1),
        ]
    )

    # Act
    repo.get_all(limit=50, offset=0, sort_by="date", sort_dir="asc")

    # Assert
    sql = cursor.execute.call_args[0][0]
    assert "ORDER BY rs.result->>'date' ASC NULLS LAST" in sql


@pytest.mark.unit
def test_get_all_id_sort_nulls_last():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", "processed", "Lidl", "2025-01-01", "50.0", [], None, False, 1),
        ]
    )

    # Act
    repo.get_all(limit=50, offset=0, sort_by="id", sort_dir="desc")

    # Assert
    sql = cursor.execute.call_args[0][0]
    assert "ORDER BY rs.id DESC NULLS LAST" in sql
```

- [ ] **Step 2: Uruchom testy — oczekiwany FAIL**

Run:
```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_receipts_scans_repository.py::test_get_all_default_sorts_by_date_desc tests/unit/test_receipts_scans_repository.py::test_get_all_date_asc_nulls_last tests/unit/test_receipts_scans_repository.py::test_get_all_id_sort_nulls_last -v
```

Expected: FAIL — SQL zawiera `ORDER BY rs.id DESC NULLS LAST` (obecne zachowanie).

- [ ] **Step 3: Commit testów**

```bash
git add backend/tests/unit/test_receipts_scans_repository.py
git commit -m "test(backend): add receipts default date sort expectations"
```

---

### Task 2: Repozytorium — implementacja sortowania

**Files:**
- Modify: `backend/src/repositories/receipts_scans.py:226-246,352`

**Interfaces:**
- Consumes: brak (Task 1 zdefiniował kontrakt).
- Produces: `ReceiptsScansRepository.get_all(..., sort_by: str = "date", sort_dir: str = "desc")` z warunkowym `NULLS FIRST`.

- [ ] **Step 1: Zmień domyślny parametr i fallback**

W `get_all()`, zamień:

```python
        sort_by: str = "id",
```

na:

```python
        sort_by: str = "date",
```

oraz:

```python
        order_expr = _SORT_COLS.get(sort_by, "id")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
```

na:

```python
        order_expr = _SORT_COLS.get(sort_by, "date")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        nulls = "FIRST" if sort_by == "date" and direction == "DESC" else "LAST"
```

- [ ] **Step 2: Zmień klauzulę ORDER BY**

Zamień:

```python
                    ORDER BY {order_expr} {direction} NULLS LAST
```

na:

```python
                    ORDER BY {order_expr} {direction} NULLS {nulls}
```

- [ ] **Step 3: Uruchom testy z Task 1**

Run:
```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_receipts_scans_repository.py::test_get_all_default_sorts_by_date_desc tests/unit/test_receipts_scans_repository.py::test_get_all_date_asc_nulls_last tests/unit/test_receipts_scans_repository.py::test_get_all_id_sort_nulls_last tests/unit/test_receipts_scans_repository.py::test_get_all_happy_path -v
```

Expected: PASS (4 testy).

- [ ] **Step 4: Commit**

```bash
git add backend/src/repositories/receipts_scans.py
git commit -m "fix(backend): default receipt list sort by date desc with nulls first"
```

---

### Task 3: Domyślne parametry w App i endpoincie

**Files:**
- Modify: `backend/src/app.py:466`
- Modify: `backend/src/main.py:164`

**Interfaces:**
- Consumes: `ReceiptsScansRepository.get_all()` z Task 2.
- Produces: `GET /receipts` bez jawnych parametrów sortu przekazuje `sort_by="date"`.

- [ ] **Step 1: Zmień default w `app.py`**

W `get_all_receipts()`, zamień:

```python
        sort_by: str = "id",
```

na:

```python
        sort_by: str = "date",
```

- [ ] **Step 2: Zmień default w `main.py`**

W `list_receipts()`, zamień:

```python
    sort_by: str = "id",
```

na:

```python
    sort_by: str = "date",
```

- [ ] **Step 3: Uruchom pełne testy jednostkowe backendu**

Run:
```bash
cd backend && ../venv/bin/python -m pytest tests/unit/ -m unit -q
```

Expected: wszystkie testy PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/src/app.py backend/src/main.py
git commit -m "fix(backend): default GET /receipts sort_by to date"
```

---

### Task 4: Frontend — domyślny sort

**Files:**
- Modify: `frontend/lib/api.ts:122`
- Modify: `frontend/app/receipts/page.tsx:305`

**Interfaces:**
- Consumes: backend `GET /receipts?sort_by=date&sort_dir=desc`.
- Produces: strona `/receipts` startuje z `sortBy === "date"` i kolumna „Data” pokazuje aktywny sort.

- [ ] **Step 1: Zmień default w `listReceipts()`**

W `frontend/lib/api.ts`, zamień:

```typescript
  const { page = 1, limit = 50, status, sort_by = "id", sort_dir = "desc", search, vendor, product, date_from, date_to, total_min, total_max, tag } = params;
```

na:

```typescript
  const { page = 1, limit = 50, status, sort_by = "date", sort_dir = "desc", search, vendor, product, date_from, date_to, total_min, total_max, tag } = params;
```

- [ ] **Step 2: Zmień domyślny stan na stronie paragonów**

W `frontend/app/receipts/page.tsx`, zamień:

```typescript
  const [sortBy, setSortBy] = useState("id");
```

na:

```typescript
  const [sortBy, setSortBy] = useState("date");
```

- [ ] **Step 3: Sprawdź typy i lint**

Run:
```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: brak nowych błędów.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/app/receipts/page.tsx
git commit -m "fix(frontend): default receipts list sort by date desc"
```

---

### Task 5: Wersjonowanie PATCH + weryfikacja końcowa

**Files:**
- Modify: `frontend/package.json` — `"version": "1.8.1"` → `"1.8.2"`
- Modify: `frontend/package-lock.json` — `"version": "1.8.1"` (root) i `packages[""].version` → `"1.8.2"`
- Modify: `backend/src/version.py` — `VERSION = "1.9.2"` → `VERSION = "1.9.3"`

**Interfaces:**
- Consumes: ukończone Taski 1–4.

- [ ] **Step 1: Podbij wersje**

```python
# backend/src/version.py
VERSION = "1.9.3"
```

```json
// frontend/package.json
"version": "1.8.2"
```

W `frontend/package-lock.json` zaktualizuj oba wystąpienia `"version": "1.8.1"` na `"1.8.2"`.

- [ ] **Step 2: Uruchom testy backendu i lint frontendu**

Run:
```bash
cd backend && ../venv/bin/python -m pytest tests/unit/ -m unit -q
cd ../frontend && npm run lint
```

Expected: PASS / brak błędów.

- [ ] **Step 3: Weryfikacja manualna (checklista ze spec)**

1. Otwórz `http://localhost:3000/receipts` — kolumna „Data” ma aktywną strzałkę ↓.
2. Paragony bez daty (pending/processing) są **nad** datowanymi.
3. Najnowsze daty są wyżej wśród paragonów z datą.
4. Kliknięcie nagłówka „ID” — sort po ID działa.
5. Modal „Wyszukaj paragon” (z transakcji bankowej/gotówkowej) — lista bez regresji.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json backend/src/version.py
git commit -m "chore: bump patch versions for receipts date sort default"
```

---

## Self-review (plan vs spec)

| Wymaganie spec | Task |
|----------------|------|
| Domyślne `date desc` | Task 2, 3, 4 |
| Paragony bez daty na początku (`NULLS FIRST`) | Task 2 |
| `date ASC` → `NULLS LAST` | Task 1 + Task 2 |
| Zakres: strona + api.ts + backend | Task 3 + Task 4 |
| 2 testy repozytorium | Task 1 (+ dodatkowy test `id` dla regresji) |
| PATCH SemVer FE + BE | Task 5 |
| Brak migracji / brak zmian kontraktu | Global Constraints |

Brak placeholderów TBD. Typy i nazwy spójne między taskami.
