# Design: Backend — „Prawdziwe” testy jednostkowe zamiast sztucznego boostu `app.py`

**Date:** 2026-04-17  
**Scope:** `backend/tests/unit/test_coverage_boost.py`, powiązane testy warstw `services/` i `repositories/`, dokumentacja pokrycia w `backend/AGENTS.md`  
**Goal:** Zastąpić testy motywowane wyłącznie metryką (cienkie `_delegates_`, samo `assert_called`) układem testów z asercjami na **wynik lub konkretne argumenty** oraz przeniesieniem ciężaru behawioralnego tam, gdzie faktycznie żyje logika — przy zachowaniu regresji dla publicznego API `App`.

---

## 1. Current State

- Plik `backend/tests/unit/test_coverage_boost.py` (~1300 linii) w docstringu deklaruje cel: podbić pokrycie `src/app.py` — co zachęca do stylu „dopisz gałąź”.
- Część testów jest wartościowa (orkiestracja, mapowanie, ścieżki błędów, `get_all_tags` z realnym SQL w treści metody).
- Inne testy kończą się na **`assert_called_once` / `assert_called`** bez sprawdzenia **zwracanej wartości** ani **argumentów** — szczególnie bloki nazwane `*_delegates_*` (m.in. `get_transactions_analytics`, `seed_and_get_classifications`, `create_category`, `get_all_evaluation_runs`, `get_bank_tx_ids_for_recategorization`, oraz `update_cash_transaction_delegates`).
- **CI:** `.github/workflows/deploy.yml` uruchamia `pytest` w `backend/` bez dodatkowego `fail_under`. `backend/pytest.ini` ma `addopts = --cov=src --cov-report=term-missing` — mierzone jest **całe** `src/`, nie wyłącznie `app.py`. `backend/.coveragerc` nie ustawia `fail_under`. Opis w `backend/AGENTS.md` (gate80% tylko na `app.py`, wykluczenia w `.coveragerc`) **nie odpowiada** obecnemu repo — należy to ujednolicić przy tej pracy lub krótkiej follow-up poprawce dokumentacji.

---

## 2. Principles (definition of a „real” test)

Każdy nowy lub przepisany test musi spełniać **co najmniej jedno**:

1. **Observable outcome:** asercja na zwróconą wartość (lub wyjątek) zgodną z założonym stanem mocków / danych.
2. **Contract on the wire:** `assert_called_once_with` / `assert_has_calls` z oczekiwanymi argumentami (w tym kwargs), gdy metoda `App` tylko przekazuje lub mapuje parametry.

**Antywzorzec do eliminacji przy refaktorze:** jedyny assert typu „collaborator został wywołany” bez powiązania z **wynikiem** lub **konkretnymi argumentami**.

Komentarze w stylu „lines 527–544 w `app.py`” — **usunąć** przy edycji (szybko się dezaktualizują i sugerują motywację wyłącznie numerem linii).

---

## 3. Taxonomy of `App` methods (where tests live)

| Klasa | Charakter | Strategia testów |
|--------|-----------|------------------|
| **A — Orkiestracja / gałęzie / SQL w `App`** | Np. `get_all_tags`, `import_bank_csv`, `confirm_receipt`, linkowanie, `_run_production` | Testy przy `App` z `make_app()` — już często na miejscu; tylko wzmocnić słabe asercje. |
| **B — Mapowanie DTO / struktur** | Np. `create_simulation`, `set_financial_focus`, `get_simulation`, `get_all_simulations`, `get_emergency_advice` (dociąga cele przed serwis) | Testy przy `App`: pełny kontrakt wyjścia + argumenty do repozytorium/serwisu. |
| **C — Jednolinijkowe delegacje** | Np. `seed_and_get_classifications`, `get_transactions_analytics`, `create_category`, `get_all_evaluation_runs`, `get_evaluation_run`, `get_bank_tx_ids_for_recategorization` | Behawioralne scenariusze w **testach repozytorium lub serwisu** (jeśli luka); przy `App` **jeden test kontraktu** na metodę: `return_value` mocka → ta sama wartość z `app.method`, ewentualnie propagacja argumentów (`limit`, `offset`, `sort_by`). |

---

## 4. File organization- **Usunąć** nazwę sugerującą metrykę: docelowo nie utrzymywać pliku `test_coverage_boost.py`.
- **Podzielić** testy `App` na **mniejsze moduły domenowe** pod `backend/tests/unit/`, np. (dokładna lista w planie implementacji):
  - paragony / skany / `confirm` / lokalizacja / produkcja,
  - bank (import, kategoryzacja, linki, tagi),
  - cash (CRUD, linki, tagi),
  - transakcje zunifikowane + analityka + tagi globalne,
  - budżet (analiza, symulacje, doradztwo awaryjne),
  - kategorie i ewaluacje.
- Wspólne: nadal `make_app()` z `tests/unit/conftest.py`; bez duplikacji fabryk.

---

## 5. Coverage and CI

- Po refaktorze uruchomić: `cd backend && ../venv/bin/python -m pytest tests/unit/ -m unit` (oraz pełny `pytest` jak w CI).
- **Nie wprowadzać nowego twardego `fail_under`** w tym designie bez osobnej decyzji — obecny CI go nie wymusza. Jeśli zespół chce próg, osobny krótki dokument + zmiana `.coveragerc` / workflow.
- Zaktualizować `backend/AGENTS.md` tak, aby opis pokrycia zgadzał się z `pytest.ini` i workflow (sekcja „Coverage gate”).

---

## 6. Out of scope

- Zmiana logiki produkcyjnej w `src/app.py` wyłącznie pod testy (YAGNI).
- Integracja E2E HTTP w tym designie (opcjonalny follow-up).
- Frontend.

---

## 7. Success criteria

- Brak testów, które w praktyce tylko „dotykają” metody `App` przez `assert_called` bez asercji wyniku lub argumentów (z wyjątkiem świadomie udokumentowanych przypadków — w tym designie: **brak wyjątków**).
- Testy `App` pogrupowane w czytelnych plikach; usunięty moduł `test_coverage_boost.py`.
- Dokumentacja pokrycia w `AGENTS.md` spójna z rzeczywistym CI i konfiguracją pytest/coverage.
- Cały zestaw testów jednostkowych backendu przechodzi lokalnie i w CI.

---

## 8. Next step

Szczegółowy plan kroków (podział plików, lista testów do przepisania, uzupełnienie testów warstw) — w `docs/superpowers/plans/2026-04-17-backend-coverage-app-tests.md` (skill **writing-plans**).
