# Refaktory testów `App` — od „coverage boost” do kontraktów i warstw

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Usunąć `test_coverage_boost.py`, rozłożyć testy na moduły domenowe, usunąć duplikaty względem `test_receipts.py`, wzmocnić asercje (wynik + argumenty), zaktualizować `backend/AGENTS.md` tak, aby opis pokrycia zgadzał się z CI.

**Architecture:** Testy `App` nadal przez `make_app()` z pełnym mockowaniem zależności. Metody typu C (czysta delegacja) — behawiory w testach repozytoriów/serwisów tam gdzie brakuje; przy `App` krótki test kontraktu z `return_value` i `assert_called_once_with`. Metody B (mapowanie) — asercje na modelu zwrotnym i kwargs wywołania.

**Tech Stack:** Python 3.11, pytest, `unittest.mock`, marker `@pytest.mark.unit`, wzorzec AAA.

---

## Mapa plików (wynik końcowy)

| Plik | Odpowiedzialność |
|------|------------------|
| `backend/tests/unit/test_app_receipts_pipeline.py` | `_run_production`, `get_receipt_by_id`, obraz, reupload, ground truth, `localize_receipt` |
| `backend/tests/unit/test_receipts.py` | `confirm_receipt` (istniejący moduł — rozszerzenie o scenariusze wyłącznie z boost) |
| `backend/tests/unit/test_app_bank_transactions.py` | import CSV, kategoryzacja banku, szczegóły, kategoria, kandydaci, link bankowy |
| `backend/tests/unit/test_app_cash_transactions.py` | cash CRUD, link, tagi powiązane z cash |
| `backend/tests/unit/test_app_unified_budget.py` | `get_transactions_analytics`, `get_all_tags`, budżet (analiza, focus, emergency), symulacje, `create_category`, eval runs, `get_bank_tx_ids_for_recategorization` |
| `backend/tests/unit/test_coverage_boost.py` | **usunięty** po migracji |
| `backend/AGENTS.md` | sekcja testów / pokrycia — zsynchronizowana z `pytest.ini` i `.github/workflows/deploy.yml` |

---

## Task 0: Audyt duplikatów i baseline

**Files:**
- Read: `backend/tests/unit/test_coverage_boost.py`
- Read: `backend/tests/unit/test_receipts.py`

- [ ] **Step 1: Lista kolizji nazw testów**

Uruchom z katalogu repo:

```bash
cd /home/pawel/eye-budget/backend && python3 << 'PY'
import re, pathlib
root = pathlib.Path("tests/unit")
by_name = {}
for p in root.rglob("test_*.py"):
    if "tasks" in p.parts:
        continue
    text = p.read_text(encoding="utf-8")
    for m in re.finditer(r"^def (test_\w+)\(", text, re.M):
        name = m.group(1)
        by_name.setdefault(name, []).append(str(p))
for name, paths in sorted(by_name.items()):
    if len(paths) > 1:
        print(name, "->", paths)
PY
```

Oczekiwany wynik: co najmniej  
`test_confirm_receipt_applies_vendor_override` oraz `test_confirm_receipt_normalized_vendor_path` w dwóch plikach — **zostaw jedną wersję** w `test_receipts.py` (mocniejsze asercje); scenariusze unikalne dla boost (np. `normalized_vendor_already_exists`, `normalized_product_path`, `date_parse_failure`, `product_with_no_category_skipped`, `returns_none_when_transaction_create_fails`) **przenieś** do `test_receipts.py` z nowymi nazwami jeśli trzeba uniknąć kolizji.

- [ ] **Step 2: Baseline pytest**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/ -m unit -q
```

Zapisz: liczba przechodzących testów (referencja przed refaktorem).

- [ ] **Step 3: Commit (opcjonalny checkpoint)**

Tylko jeśli robisz branch feature: `git checkout -b refactor/app-unit-tests-coverage`

---

## Task 1: Utworzyć `test_app_receipts_pipeline.py`

**Files:**
- Create: `backend/tests/unit/test_app_receipts_pipeline.py`
- Modify: `backend/tests/unit/test_coverage_boost.py` (usuń przeniesione bloki w Task 7 lub kopiuj-stopniowo)

Przenieś **bez zmiany logiki** (na razie) następujące funkcje z `test_coverage_boost.py` — od początku pliku do końca sekcji `localize` (oko linii 14–491), **z wyłącieniem** całej sekcji `confirm_receipt` (ta idzie w Task 2):

- `test_run_production_already_added_file`
- `test_run_production_calls_on_progress`
- `test_get_receipt_by_id_with_transaction_and_bank_link`
- `test_get_receipt_by_id_with_transaction_and_cash_link`
- `test_get_receipt_by_id_counts_candidates`
- `test_get_receipt_image_url_returns_url_when_key_exists`
- `test_reupload_receipt_image_returns_false_when_scan_missing`
- `test_reupload_receipt_image_returns_false_when_preprocessing_fails`
- `test_reupload_receipt_image_returns_false_when_upload_fails`
- `test_reupload_receipt_image_success`
- `test_get_ground_truth_image_bytes_returns_none_when_missing`
- `test_get_ground_truth_image_bytes_downloads`
- `test_localize_receipt_raises_404_when_scan_missing`
- `test_localize_receipt_raises_404_when_no_minio_key`
- `test_localize_receipt_success`

- [ ] **Step 1:** Utwórz plik z docstringiem modułu (bez frazy „coverage gate”; np. „Unit tests for App receipt scan pipeline helpers.”).

- [ ] **Step 2:** Skopiuj powyższe testy wraz z importami (`pytest`, `MagicMock`, `patch`, `make_app`).

- [ ] **Step 3:** Uruchom tylko ten plik:

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/test_app_receipts_pipeline.py -m unit -v
```

Oczekiwane: wszystkie PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_app_receipts_pipeline.py
git commit -m "test: extract App receipt pipeline tests from coverage boost module"
```

---

## Task 2: Scalić `confirm_receipt` z `test_receipts.py`

**Files:**
- Modify: `backend/tests/unit/test_receipts.py`
- Modify: `backend/tests/unit/test_coverage_boost.py` (usuń przeniesione testy confirm)

- [ ] **Step 1:** Usuń z planu migracji duplikaty już pokryte mocniej w `test_receipts.py`:
  - `test_confirm_receipt_applies_vendor_override` (boost) — **nie kopiuj**; zostaw wersję z `test_receipts.py`.
  - `test_confirm_receipt_normalized_vendor_path` (boost) — **nie kopiuj**; zostaw wersję z `test_receipts.py` (ma `assert_called_once_with` na `insert_alternative_name`).

- [ ] **Step 2:** Dodaj do `test_receipts.py` brakujące scenariusze z boost (jeden test = jedna funkcja), używając istniejących helperów `make_scan_detail`, `make_confirm_request`, `_setup_no_transaction` tam gdzie to możliwe zamiast lokalnego `_make_scan_with_result`:

  - `test_confirm_receipt_returns_none_when_transaction_create_fails` (create_transaction → -1)
  - `test_confirm_receipt_normalized_vendor_already_exists`
  - `test_confirm_receipt_normalized_product_path`
  - `test_confirm_receipt_date_parse_failure`
  - `test_confirm_receipt_product_with_no_category_skipped`

- [ ] **Step 3:** Jeśli `test_confirm_receipt_returns_none_when_no_scan` (boost) i `test_confirm_receipt_returns_none_when_scan_missing` (test_receipts) są równoważne — **zostaw jeden** test (preferuj nazwę `..._when_scan_missing`).

- [ ] **Step 4:**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/test_receipts.py -m unit -v
```

Oczekiwane: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/unit/test_receipts.py
git commit -m "test: merge confirm_receipt scenarios from coverage boost into test_receipts"
```

---

## Task 3: Utworzyć `test_app_bank_transactions.py`

**Files:**
- Create: `backend/tests/unit/test_app_bank_transactions.py`

Przenieś z `test_coverage_boost.py` funkcje od `test_import_bank_csv_empty_returns_zeros` przez `test_link_bank_to_receipt_returns_detail_on_success` (sekcje import / categorize / bank detail / update / candidates / link).

- [ ] **Step 1:** Wzmocnij test `test_import_bank_csv_with_rows` jeśli asercja nie sprawdza `BankImportResult` (imported, duplicates, auto_linked) — dodaj assert na polach zwróconej krotki `(result, ids)` zgodnie z mockami `insert_transactions` i `get_new_ids_for_categorization`.

- [ ] **Step 2:**

```bash
../venv/bin/python -m pytest tests/unit/test_app_bank_transactions.py -m unit -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_app_bank_transactions.py
git commit -m "test: extract App bank transaction tests from coverage boost"
```

---

## Task 4: Utworzyć `test_app_cash_transactions.py`

**Files:**
- Create: `backend/tests/unit/test_app_cash_transactions.py`

Przenieś testy od `test_create_cash_transaction_returns_none_when_insert_fails` do `test_update_bank_transaction_tags_with_link` (cash + tagi powiązane z receipt/bank/cash według obecnego układu w boost).

- [ ] **Step 1:** Utwórz plik i przenieś wymienione testy; usuń komentarze z numerami linii w `app.py`.

- [ ] **Step 2: Wzmocnij `test_update_cash_transaction_delegates` i `test_update_cash_transaction_no_booking_date`**

Zastąp nazwy (usuń `_delegates` z nazwy) i dodaj asercję na argumenty wywołania `update`, np.:

```python
app.cash_transactions_repository.update.assert_called_once()
call_kwargs = app.cash_transactions_repository.update.call_args[1]
assert call_kwargs["booking_date"] == "2024-02-01"  # lub brak klucza gdy None
```

Dostosuj do faktycznej sygnatury `CashTransactionsRepository.update` w `src/repositories/cash_transactions.py` (użyj `call_args` / kwargs faktycznie przekazywanych przez `App.update_cash_transaction`).

- [ ] **Step 3:** pytest pliku + commit analogiczny do Task 3.

---

## Task 5: Utworzyć `test_app_unified_budget.py` i wzmocnić „delegates”

**Files:**
- Create: `backend/tests/unit/test_app_unified_budget.py`

Przenieś: `get_transactions_analytics`, `get_all_tags*`, `seed_and_get_classifications`, `update_category_classification`, `set_financial_focus`, `get_emergency_advice`, symulacje (`create` / `get` / `get_all`), `create_category`, `get_all_evaluation_runs`, `get_evaluation_run`, `get_bank_tx_ids_for_recategorization`.

- [ ] **Step 1: Zamień wzorzec „tylko assert_called” na kontrakt**

Przykład dla `get_transactions_analytics`:

```python
@pytest.mark.unit
def test_get_transactions_analytics_returns_repository_summary():
    app = make_app()
    expected = MagicMock()
    app.unified_transactions_repository.get_analytics.return_value = expected

    result = app.get_transactions_analytics(date_from="2024-01-01", date_to="2024-01-31")

    assert result is expected
    app.unified_transactions_repository.get_analytics.assert_called_once_with(
        date_from="2024-01-01",
        date_to="2024-01-31",
    )
```

Analogicznie: `seed_and_get_classifications` → `assert result is mock_return`; `create_category` → `assert result is ...` z `categories_repository.create_category.return_value`; `get_bank_tx_ids_for_recategorization` → `assert result == [1, 2]` gdy mock zwraca listę.

- [ ] **Step 2: `create_simulation`**

Asercja `budget_simulations_repository.create_simulation.assert_called_once_with` z polami z `CreateBudgetSimulationRequest` (name, expense_name, amount=req.expense_amount_pln, expense_type, start_date).

- [ ] **Step 3: Uzupełnij luki w warstwach (YAGNI — tylko jeśli brak testów)**

Szybki audyt:

```bash
rg -l "seed_and_get_classifications|get_analytics" tests/unit/test_services_domain.py tests/unit/test_budget_analysis_repository.py
```

Jeśli serwis analizy budżetu nie ma testu dla `seed_and_get_classifications`, dodaj **jeden** test behawioralny w `test_services_domain.py` (wzoruj się na istniejących klasach w tym pliku). Jeśli już jest — nie duplikuj.

- [ ] **Step 4:** pytest + commit.

---

## Task 6: Usunąć `test_coverage_boost.py` i sprawdzić całość

- [ ] **Step 1:** Upewnij się, że **wszystkie** `def test_*` z `test_coverage_boost.py` zostały przeniesione lub celowo scalone (grep po nazwach funkcji w nowych plikach / `test_receipts.py`).

- [ ] **Step 2:** Usuń `backend/tests/unit/test_coverage_boost.py`.

- [ ] **Step 3:**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/ -m unit -q
```

Oczekiwane: ten sam lub wyższy licznik testów niż baseline z Task 0 (po deduplikacji może być nieco mniej — to OK jeśli usunięto tylko duplikaty).

- [ ] **Step 4:**

```bash
../venv/bin/python -m pytest -q
```

(jak CI — z `--cov` z `pytest.ini`)

- [ ] **Step 5: Commit**

```bash
git add -A backend/tests/unit/
git commit -m "test: remove test_coverage_boost after splitting App unit tests"
```

---

## Task 7: Zaktualizować `backend/AGENTS.md`

**Files:**
- Modify: `backend/AGENTS.md`

- [ ] **Step 1:** W sekcji „Coverage gate” zastąp nieaktualny opis faktymi:

  - CI: `../venv/bin/python -m pytest` w `backend/` (patrz `.github/workflows/deploy.yml`).
  - `pytest.ini`: `addopts = --cov=src --cov-report=term-missing` — raport dla całego `src/`.
  - `backend/.coveragerc`: brak `fail_under` w repo — **nie pisz** o twardym progu 80% na samym `app.py`, chyba że dodasz go w osobnym PR.

- [ ] **Step 2:** Dodaj jedną linię: nowe moduły `test_app_*.py` grupują testy `App` według domeny (link do tego planu opcjonalny).

- [ ] **Step 3: Commit**

```bash
git add backend/AGENTS.md
git commit -m "docs: align AGENTS.md backend testing section with pytest and CI"
```

---

## Uwagi końcowe

- **Nie zmieniaj** `src/app.py` w tym planie poza ewentualnym bugfixem odkrytym przez nowe asercje (wtedy osobny commit z opisem regresji).
- **`test_delegation.py`** ma podobny ton do starego boost — **poza zakresem** tego planu; można zaplanować analogiczny refaktor później.
- Po zatwierdzeniu planu przez maintainers implementuj Task 0→7 po kolei; każdy task kończ commitami zgodnie z krokami.
