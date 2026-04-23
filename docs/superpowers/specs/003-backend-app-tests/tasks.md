# Tasks: Backend App.py Testability & Test Coverage

**Input**: Design documents from `/specs/003-backend-app-tests/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | quickstart.md ✅

**Organization**: Tasks grouped by user story — each story independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state dependency)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup (Test Infrastructure)

**Purpose**: Create the test directory structure, config files, and dependency manifest.

- [X] T001 Create `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/integration/__init__.py` (empty files to make packages)
- [X] T002 [P] Create `backend/requirements-test.txt` with: `pytest>=8.0`, `pytest-mock>=3.14`, `pytest-cov>=5.0`, `testcontainers[postgres,minio]>=4.13`
- [X] T003 [P] Create `backend/.coveragerc` with `[run] source=src omit=src/__init__.py,*/tests/*,*/migrations/*` and `[report] fail_under=80 exclude_lines=def dispose,def __init__`
- [X] T004 [P] Create `backend/tests/conftest.py` with `pytest_configure` registering `unit` and `integration` markers
- [X] T005 Install test dependencies into project venv: `venv/bin/pip install -r backend/requirements-test.txt`

**Checkpoint**: `venv/bin/pytest backend/tests/ --collect-only` runs without ImportError

---

## Phase 2: Foundational — DI Refactor of `App.__init__`

**Purpose**: The single blocking prerequisite for all unit test stories. No unit test can be written until `App` accepts injected dependencies.

**⚠️ CRITICAL**: All Phase 3–6 work depends on this phase being complete and verified.

- [X] T006 Refactor `backend/src/app.py` `App.__init__` signature to accept `eye_budget_db_context=None` as the first optional keyword argument; update the body so `self.eye_budget_db_context = eye_budget_db_context or EyeBudgetDbContext()`
- [X] T007 Refactor `backend/src/app.py` `App.__init__` to accept all 17 repository keyword arguments (defaulting to `None`); replace each direct construction with `self.x = x or XRepository(self.eye_budget_db_context)` — preserve original construction order
- [X] T008 Refactor `backend/src/app.py` `App.__init__` to accept all 15 service keyword arguments (defaulting to `None`); replace each direct construction with `self.x = x or XService(...)`
- [X] T009 Fix `categories_service` and `bank_categorization_service` build calls in `backend/src/app.py`: call `.build()` only when the service was auto-constructed (`if categories_service is None: self.categories_service.build()`), not when injected — prevents `MagicMock.build()` side-effects
- [X] T010 Create `backend/tests/unit/conftest.py` with the `make_app()` factory function: builds `ALL_PARAMS` list (starting with `eye_budget_db_context`, then all repo names, then all service names), creates `MagicMock()` defaults for each, and applies `**overrides`
- [X] T011 Smoke-verify the refactor: run `cd backend && ../venv/bin/python -c "from src.app import App; print('OK')"` and confirm no import errors; run `cd backend && ../venv/bin/pytest tests/ --collect-only` and confirm zero collection errors

**Checkpoint**: `make_app()` can be called in a Python REPL without any DB connection attempt or printed error messages.

---

## Phase 3: User Story 1 — DI Verification Tests (Priority: P1) 🎯 MVP

**Goal**: Prove that `App` can be instantiated with all dependencies injected as mocks — no psycopg2 connection, no print output, no side-effects.

**Independent Test**: `venv/bin/pytest backend/tests/unit/test_di.py -v` passes with zero failures and zero warnings about DB connections.

- [X] T012 [US1] Create `backend/tests/unit/test_di.py`: write test `test_make_app_does_not_connect_to_db` — calls `make_app()`, asserts `app.eye_budget_db_context.connect_db` was never called (MagicMock call count = 0)
- [X] T013 [US1] Add test `test_make_app_uses_injected_repos` in `backend/tests/unit/test_di.py`: create a named mock repo, pass it to `make_app(receipts_scans_repository=mock)`, assert `app.receipts_scans_repository is mock`
- [X] T014 [US1] Add test `test_make_app_uses_injected_service` in `backend/tests/unit/test_di.py`: pass a named mock service, assert `app.ocr_service is mock`
- [X] T015 [US1] Add test `test_make_app_does_not_call_build_on_injected_categories_service` in `backend/tests/unit/test_di.py`: pass `categories_service=MagicMock()`, assert `.build()` was never called
- [X] T016 [US1] Add test `test_make_app_does_not_call_build_on_injected_bank_categorization_service` in `backend/tests/unit/test_di.py`: pass `bank_categorization_service=MagicMock()`, assert `.build()` was never called

**Checkpoint**: `venv/bin/pytest backend/tests/unit/test_di.py -v` — all 5 tests green.

---

## Phase 4: User Story 2 — Unit Tests: Receipt Confirmation Logic (Priority: P2)

**Goal**: Full unit test coverage of `confirm_receipt`, `reopen_receipt`, `delete_receipt`, `retry_receipt`.

**Independent Test**: `venv/bin/pytest backend/tests/unit/test_receipts.py -v` passes with zero failures.

- [X] T017 [P] [US2] Create `backend/tests/unit/test_receipts.py` with module-level imports and a `make_confirm_request()` helper that builds a minimal `ConfirmReceiptRequest` fixture (vendor, date, total, one product with category)
- [X] T018 [US2] Add test `test_confirm_receipt_applies_vendor_override` in `backend/tests/unit/test_receipts.py`: configure `receipts_scans_repository.get_by_id` to return a scan with OCR result, pass `request.vendor="override"`, assert `receipts_scans_repository.set_result_by_id` was called with the overridden vendor in the model dump
- [X] T019 [US2] Add test `test_confirm_receipt_creates_transaction_with_correct_args` in `backend/tests/unit/test_receipts.py`: verify `transactions_repository.create_transaction` was called with correct `scan_id`, `total`, and `transaction_date` derived from the OCR result date
- [X] T020 [US2] Add test `test_confirm_receipt_normalized_vendor_path` in `backend/tests/unit/test_receipts.py`: pass `request.normalized_vendor="Biedronka"`, configure `vendors_repository.get_vendor_by_name` to return `None` (not found), assert `vendors_repository.insert_vendor` is called and `vendors_repository.insert_alternative_name` is called with the raw OCR vendor name
- [X] T021 [US2] Add test `test_confirm_receipt_standard_vendor_lookup_path` in `backend/tests/unit/test_receipts.py`: pass no `normalized_vendor`, assert `transactions_repository.lookup_vendor_id` is called instead
- [X] T022 [US2] Add test `test_confirm_receipt_analytics_exception_is_swallowed` in `backend/tests/unit/test_receipts.py`: configure `prompt_analytics_repository.upsert` to raise `Exception("boom")`, assert `confirm_receipt` returns a non-None result (confirmation succeeds despite analytics failure)
- [X] T023 [US2] Add test `test_confirm_receipt_returns_none_when_scan_missing` in `backend/tests/unit/test_receipts.py`: configure `receipts_scans_repository.get_by_id` to return `None`, assert `confirm_receipt` returns `None`
- [X] T024 [US2] Add test `test_confirm_receipt_calls_auto_link` in `backend/tests/unit/test_receipts.py`: assert `bank_receipt_links_repository.find_auto_match_bank_tx` is called after successful transaction creation
- [X] T025 [US2] Add test `test_reopen_receipt_deletes_transaction_and_resets_status` in `backend/tests/unit/test_receipts.py`: assert `transactions_repository.delete_by_scan_id` and `receipts_scans_repository.set_status_to_confirm_by_id` are both called with correct `scan_id`
- [X] T026 [US2] Add test `test_delete_receipt_removes_minio_image` in `backend/tests/unit/test_receipts.py`: configure scan with a `minio_object_key`, assert `minio_service.delete_image` is called with that key and `receipts_scans_repository.delete_scan_by_id` is called
- [X] T027 [US2] Add test `test_delete_receipt_returns_false_when_scan_missing` in `backend/tests/unit/test_receipts.py`: configure `receipts_scans_repository.get_by_id` to return `None`, assert result is `False`
- [X] T028 [US2] Add test `test_retry_receipt_returns_false_when_scan_missing` in `backend/tests/unit/test_receipts.py`: configure `receipts_scans_repository.reset_for_retry` to return `None`, assert result is `False`

**Checkpoint**: `venv/bin/pytest backend/tests/unit/test_receipts.py -v` — all tests green.

---

## Phase 5: User Story 3 — Unit Tests: Auto-Link Logic (Priority: P3)

**Goal**: Full unit test coverage of `_auto_link_receipt`, `_auto_link_bank_transactions`, `_auto_link_cash_transaction`.

**Independent Test**: `venv/bin/pytest backend/tests/unit/test_autolink.py -v` passes with zero failures.

- [X] T029 [P] [US3] Create `backend/tests/unit/test_autolink.py` with imports and a helper `make_bank_match()` that returns a mock object with `bank_transaction_id` and `scan_id` attributes
- [X] T030 [US3] Add test `test_auto_link_receipt_bank_has_priority` in `backend/tests/unit/test_autolink.py`: configure `bank_receipt_links_repository.find_auto_match_bank_tx` to return a match; configure `create_link` to return `True`; assert `cash_receipt_links_repository.find_auto_match_cash_tx` is **never** called (bank takes priority and returns early)
- [X] T031 [US3] Add test `test_auto_link_receipt_falls_back_to_cash` in `backend/tests/unit/test_autolink.py`: configure `find_auto_match_bank_tx` to return `None`; configure `cash_receipt_links_repository.find_auto_match_cash_tx` to return a match; assert `cash_receipt_links_repository.create_link` is called
- [X] T032 [US3] Add test `test_auto_link_receipt_merges_tags_on_bank_link` in `backend/tests/unit/test_autolink.py`: configure `receipts_scans_repository.get_tags_for_scan` to return `["a"]` and `bank_transactions_repository.get_tags_for_tx` to return `["b"]`; assert both `update_tags` calls receive `["a", "b"]`
- [X] T033 [US3] Add test `test_auto_link_receipt_exception_is_swallowed` in `backend/tests/unit/test_autolink.py`: configure `find_auto_match_bank_tx` to raise `Exception("db error")`; assert `_auto_link_receipt` completes without re-raising
- [X] T034 [US3] Add test `test_auto_link_bank_transactions_single_match_creates_link` in `backend/tests/unit/test_autolink.py`: pass a list with one `tx_id`; configure `find_receipt_candidates` to return a list of length 1; configure `find_auto_match_receipt` to return a match; assert `create_link` is called and returns `linked=1, skipped=0`
- [X] T035 [US3] Add test `test_auto_link_bank_transactions_multi_candidate_is_skipped` in `backend/tests/unit/test_autolink.py`: configure `find_receipt_candidates` to return a list of length 2; assert `create_link` is **never** called and returns `linked=0, skipped=1`
- [X] T036 [US3] Add test `test_auto_link_bank_transactions_no_match_no_link` in `backend/tests/unit/test_autolink.py`: configure `find_auto_match_receipt` to return `None`; assert `create_link` is never called and `linked=0`
- [X] T037 [US3] Add test `test_auto_link_cash_transaction_creates_link` in `backend/tests/unit/test_autolink.py`: configure `cash_receipt_links_repository.find_auto_match_receipt` to return `{"receipt_transaction_id": 42}`; assert `create_link` is called with correct args and returns `True`

**Checkpoint**: `venv/bin/pytest backend/tests/unit/test_autolink.py -v` — all tests green.

---

## Phase 6: User Story 4 — Unit Tests: Budget Delegation (Priority: P4)

**Goal**: Verify that all budget-related `App` methods correctly forward arguments to the underlying services.

**Independent Test**: `venv/bin/pytest backend/tests/unit/test_budget.py -v` passes with zero failures.

- [X] T038 [P] [US4] Create `backend/tests/unit/test_budget.py` with imports
- [X] T039 [US4] Add test `test_get_monthly_breakdown_delegates_year_and_month` in `backend/tests/unit/test_budget.py`: call `app.get_monthly_breakdown(2025, 3)`, assert `budget_analysis_service.get_monthly_breakdown` was called with `year=2025, month=3`
- [X] T040 [US4] Add test `test_check_affordability_fetches_focus_and_allocations` in `backend/tests/unit/test_budget.py`: configure `budget_analysis_service.get_financial_focus` to return a mock with `id=1, label="savings"` and `budget_goals_repository.get_active_goal_allocations_total` to return `500.0`; assert `budget_analysis_service.check_affordability` is called with `amount_pln`, `financial_focus_label="savings"`, `goal_allocations_pln=500.0`
- [X] T041 [US4] Add test `test_check_affordability_uses_none_focus_when_no_focus_set` in `backend/tests/unit/test_budget.py`: configure `get_financial_focus` to return a mock with `id=None`; assert `check_affordability` is called with `financial_focus_label=None`
- [X] T042 [US4] Add test `test_get_goals_delegates` in `backend/tests/unit/test_budget.py`: assert `app.get_goals()` calls `budget_goals_service.get_goals()` and returns its return value
- [X] T043 [US4] Add test `test_create_goal_delegates_request` in `backend/tests/unit/test_budget.py`: create a mock `CreateFinancialGoalRequest`, call `app.create_goal(req)`, assert `budget_goals_service.create_goal` was called with the same `req` object
- [X] T044 [US4] Add test `test_delete_goal_delegates_goal_id` in `backend/tests/unit/test_budget.py`: call `app.delete_goal(42)`, assert `budget_goals_service.delete_goal` was called with `42`
- [X] T045 [US4] Add test `test_get_ai_recommendations_delegates` in `backend/tests/unit/test_budget.py`: assert `app.get_ai_recommendations()` calls `budget_simulation_service.get_ai_recommendations_from_db()` and returns its return value

**Checkpoint**: `venv/bin/pytest backend/tests/unit/ -v` — all unit tests across all 4 files green.

---

## Phase 7: User Story 5 — Integration Tests: Receipt Processing Pipeline (Priority: P5)

**Goal**: End-to-end smoke tests using real PostgreSQL + MinIO containers (LLM/OCR mocked).

**Independent Test**: `venv/bin/pytest backend/tests/integration/ -v` passes (requires Docker).

- [X] T046 Create `backend/tests/integration/conftest.py`: session-scoped `PostgresContainer("postgres:16-alpine")` fixture and session-scoped `MinioContainer()` fixture; session-scoped `migrated_db` fixture that applies yoyo migrations programmatically (`get_backend(url)` + `read_migrations("migrations")` + `backend.apply_migrations(backend.to_apply(migrations))`)
- [X] T047 Add function-scoped `integration_app` fixture in `backend/tests/integration/conftest.py`: sets env vars (`POSTGRESQL_HOST/PORT/DB/USER/PASSWORD`, `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY`) from container values, constructs `App()` without injection, yields it, calls `app.dispose()` in teardown
- [X] T048 Add function-scoped table-truncation fixture in `backend/tests/integration/conftest.py` (`truncate_tables`): connects via psycopg2 using the container's DSN, truncates all public tables with `CASCADE`, called as auto-use fixture before each integration test
- [X] T049 [P] [US5] Create `backend/tests/integration/test_pipeline.py` with imports and an `ocr_mock_result` helper that returns a minimal valid OCR JSON dict (vendor, date, total, one product)
- [X] T050 [US5] Add test `test_process_single_file_success` in `backend/tests/integration/test_pipeline.py`: use `integration_app`; mock `app.ocr_service.process_image` to return the fixture OCR result; call `app.receipts_scans_repository.add_receipt(filename)` then `app._process_single_file(filename)`; query DB directly to assert status is `PROCESSED` and result is non-null
- [X] T051 [US5] Add test `test_process_single_file_ocr_failure` in `backend/tests/integration/test_pipeline.py`: mock `app.ocr_service.process_image` to raise `RuntimeError("OCR failed")`; call `_process_single_file`; assert status in DB is `FAILED` and error message contains `"OCR failed"`
- [X] T052 [US5] Add test `test_confirm_receipt_persists_transaction` in `backend/tests/integration/test_pipeline.py`: run full pipeline (`add_receipt` → `_process_single_file` with mocked OCR → `confirm_receipt`); query `receipt_transactions` table directly to assert a row exists with correct vendor and total

**Checkpoint**: `venv/bin/pytest backend/tests/integration/ -v` — all 3 tests green (Docker required).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Coverage gate enforcement, CI integration check, and documentation.

- [X] T053 Run full unit test suite with coverage gate: `cd backend && ../venv/bin/pytest tests/unit/ --cov=src --cov-config=.coveragerc --cov-fail-under=80 --cov-report=term-missing`; if coverage is below 80%, identify uncovered lines and add targeted tests in the appropriate test file until gate passes
- [X] T054 [P] Verify backwards compatibility: run `cd backend && ../venv/bin/python -c "from src.app import App; a = App.__new__(App); print('signature OK')"` — confirms default `App()` construction path still works (no required args added)
- [X] T055 [P] Update `backend/AGENTS.md` (or create if missing) to document the `make_app()` factory, the `venv/bin/pytest` commands for unit vs integration tests, and the 80% coverage gate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (DI Refactor)**: Depends on Phase 1 — BLOCKS all unit test phases
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2 — can run in parallel with Phase 3 once Phase 2 is done
- **Phase 5 (US3)**: Depends on Phase 2 — can run in parallel with Phases 3–4
- **Phase 6 (US4)**: Depends on Phase 2 — can run in parallel with Phases 3–5
- **Phase 7 (US5)**: Depends on Phase 2 — Docker must be available
- **Phase 8 (Polish)**: Depends on Phases 3–7

### User Story Dependencies

- **US1 (DI Verification)**: Directly verifies Phase 2 — must run first
- **US2, US3, US4**: All independent of each other; all depend only on Phase 2
- **US5**: Independent; requires Docker

### Parallel Opportunities

- T002, T003, T004 — parallel (different files)
- T006, T007, T008 — sequential (same file, same method)
- T012–T016 — sequential within US1 (same file)
- T017 vs T029 vs T038 — parallel (different test files, after Phase 2)
- T018–T028 — can be split between developers (same file but independent test functions)
- T039–T045 — parallel within US4 (all independent test functions in same file)

---

## Parallel Example: Phases 3–6 (after Phase 2 complete)

```bash
# All four user story test files can be written in parallel:
Task T012–T016: backend/tests/unit/test_di.py        (US1)
Task T017–T028: backend/tests/unit/test_receipts.py  (US2)
Task T029–T037: backend/tests/unit/test_autolink.py  (US3)
Task T038–T045: backend/tests/unit/test_budget.py    (US4)
```

---

## Implementation Strategy

### MVP First (User Stories 1–2 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: DI Refactor (critical)
3. Complete Phase 3: US1 DI verification tests
4. Complete Phase 4: US2 receipt confirmation tests
5. **STOP and VALIDATE**: run `pytest tests/unit/ --cov=src --cov-fail-under=80`
6. If gate passes — US1+US2 is a shippable test increment

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready (no tests yet but App is testable)
2. Phase 3 → DI contract proven
3. Phase 4 → Most complex business logic covered
4. Phase 5 → Auto-link edge cases covered
5. Phase 6 → Budget delegation covered; coverage gate likely met
6. Phase 7 → Full pipeline integration confidence (optional, Docker required)

### Single Developer Sequence

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017–T028 → T029–T037 → T038–T045 → T046–T052 → T053–T055

---

## Notes

- `[P]` tasks touch different files — safe to parallelize
- `make_app()` is the universal unit test entry point — every test starts with it
- `eye_budget_db_context` must be the first param in ALL_PARAMS (it's constructed before repos in `__init__`)
- Integration tests auto-truncate tables via `truncate_tables` auto-use fixture — no manual cleanup needed
- Run `pytest backend/tests/unit/` (no Docker) vs `pytest backend/tests/integration/` (Docker) independently
- Coverage gate (`--cov-fail-under=80`) applies to **unit tests only** — integration tests are excluded from the threshold
