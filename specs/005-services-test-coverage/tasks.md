# Tasks: Backend Services Test Coverage

**Input**: Design documents from `specs/005-services-test-coverage/`  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ quickstart.md ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1–US5)

## Path Conventions

Backend-only feature. All paths relative to `/home/pawel/eye-budget/`.

---

## Phase 1: Setup

**Purpose**: Add test infrastructure required by all subsequent phases.

- [X] T001 Add `pytest-asyncio>=0.23` as new line in `backend/requirements-test.txt`
- [X] T002 Create `backend/pytest.ini` with content: `[pytest]`, `asyncio_mode = auto`, `addopts = --cov=src/services --cov-report=term-missing --cov-fail-under=80`, `markers =` block defining `unit` and `integration` markers (matching existing conftest.py markers)

**Checkpoint**: `pip install -r requirements-test.txt` installs pytest-asyncio without errors; `pytest --co` exits without config errors.

---

## Phase 2: Foundational — LLM Service DI Refactors

**Purpose**: Five LLM services create their OpenAI clients internally, blocking constructor-injection testing. Refactor them to accept optional injected clients — required before US2 test file can be written.

**⚠️ CRITICAL**: T009 (US2) cannot be written until this phase is complete. T008, T010–T012 are independent of this phase and can proceed in parallel.

- [X] T003 [P] Refactor `OCRService.__init__` in `backend/src/services/ocr.py`: add `client: OpenAI | None = None` and `async_client: AsyncOpenAI | None = None` parameters; assign `self.client = client if client is not None else OpenAI()` and `self.async_client = async_client if async_client is not None else AsyncOpenAI()` — replace the current hard-coded instantiation lines
- [X] T004 [P] Refactor `CategoriesService.__init__` in `backend/src/services/categories.py`: add `client: OpenAI | None = None` parameter; replace hard-coded `OpenAI()` with `client if client is not None else OpenAI()`
- [X] T005 [P] Refactor `BankCategorizationService.__init__` in `backend/src/services/bank_categorization.py`: add `client: OpenAI | None = None` and `async_client: AsyncOpenAI | None = None` parameters; replace hard-coded `OpenAI()` / `AsyncOpenAI()` with the conditional pattern
- [X] T006 [P] Refactor `ProductsService.__init__` in `backend/src/services/products.py`: add `client: OpenAI | None = None` parameter; replace hard-coded `OpenAI()` with the conditional pattern
- [X] T007 [P] Refactor `VendorsService.__init__` in `backend/src/services/vendors.py`: add `client: OpenAI | None = None` parameter; replace hard-coded `OpenAI()` with the conditional pattern

**Checkpoint**: `python -m pytest -m unit` (existing tests) still pass — no regressions from refactors. Production `App.__init__` unchanged (all new params default to `None`).

---

## Phase 3: User Story 1 — Pure-Logic Services (Priority: P1) 🎯 MVP

**Goal**: Unit tests for `PekaoCsvParser`, `MarkdownTableService`, and `TextMatchingService` — no mocks needed.

**Independent Test**: `python -m pytest backend/tests/unit/test_services_pure.py -v` — all pass with no infrastructure.

**Note**: Can start after Phase 1 (no dependency on Phase 2 refactors).

- [X] T008 [US1] Create `backend/tests/unit/test_services_pure.py` with `@pytest.mark.unit` on all test classes; implement:
  - `TestPekaoCsvParser`:
    - `test_parse_valid_utf8` — Arrange: build a minimal valid Pekao CSV string with one transaction row (UTF-8); Act: call `PekaoCsvParser().parse_bytes()`; Assert: returns one `BankTransactionRow` with correct `amount`, `booking_date`, `reference_number`
    - `test_polish_decimal_format` — Arrange: amount string `"-1 014,31"`; Act: parse; Assert: `amount == Decimal("-1014.31")`
    - `test_row_missing_reference_skipped` — Arrange: CSV row with empty `Numer referencyjny`; Act: parse; Assert: result list is empty
    - `test_cp1250_encoding_fallback` — Arrange: encode minimal valid CSV as CP1250 bytes; Act: parse; Assert: returns one row without raising
    - `test_apostrophe_stripped_from_reference` — Arrange: reference number `'ABC123` (apostrophe prefix); Act: parse; Assert: `reference_number == "ABC123"`
    - `test_invalid_amount_skipped` — Arrange: amount string `"not_a_number"`; Act: parse; Assert: result list is empty
  - `TestMarkdownTableService`:
    - `test_basic_two_column_table` — Arrange: two equal-length column lists; Act: `MarkdownTableService().table()`; Assert: output contains header row, delimiter row, body rows
    - `test_columns_of_different_lengths_padded` — Arrange: col1 has 3 items, col2 has 2; Act: call `table()`; Assert: second column's last cell is empty string (no IndexError)
    - `test_single_column_table` — Arrange: one column with two items; Act: call `table()`; Assert: valid markdown output, no crash
  - `TestTextMatchingService`:
    - `test_products_matched_to_regions` — Arrange: list of product names and list of OCR bounding-box candidates; Act: `TextMatchingService().match()`; Assert: each product paired with a region (result length equals product count)
    - `test_empty_product_list` — Arrange: empty product list, non-empty OCR candidates; Act: `match()`; Assert: returns empty list

**Checkpoint**: `pytest backend/tests/unit/test_services_pure.py -v` — 11 tests pass, ~0s infrastructure overhead.

---

## Phase 4: User Story 2 — LLM-Dependent Services (Priority: P2)

**Goal**: Unit tests for all six LLM services using injected `MagicMock` clients.

**Independent Test**: `python -m pytest backend/tests/unit/test_services_llm.py -v` — all pass, no real API calls.

**Depends on**: Phase 2 (T003–T007) — service constructors must accept injected clients.

- [X] T009 [US2] Create `backend/tests/unit/test_services_llm.py` with `@pytest.mark.unit` on all test classes; implement:
  - `TestOCRService` (uses `client = MagicMock()`, `async_client = MagicMock()`):
    - `test_process_image_happy_path` — Arrange: mock client returns valid JSON receipt via `chat.completions.create()`; Act: `OCRService(client=mock).process_image("path")`; Assert: returns populated `TransactionModel`
    - `test_process_image_async_happy_path` — `async def` test; Arrange: mock async_client returns same JSON; Act: `await OCRService(async_client=mock).process_image_async("path")`; Assert: same result shape as sync variant
    - `test_process_image_malformed_json_raises` — Arrange: mock returns `"{not valid json}"`; Act/Assert: `pytest.raises(Exception)` (any descriptive exception, not silent `None`)
  - `TestCategoriesService` (uses `client = MagicMock()`):
    - `test_assign_candidates_happy_path` — Arrange: mock returns valid category JSON; Act: `CategoriesService(client=mock).assign_category_candidates(products)`; Assert: returns list of category candidate strings
    - `test_assign_candidates_malformed_json_raises` — Arrange: mock returns malformed JSON; Assert: raises
  - `TestBankCategorizationService` (uses sync + async mocks):
    - `test_assign_candidates_happy_path` — sync path with mocked client; Assert: returns categories per transaction
    - `test_assign_candidates_async_happy_path` — `async def` test; same result via async path
  - `TestProductsService`:
    - `test_process_products_happy_path` — Arrange: mock returns normalised names list; Act: `ProductsService(client=mock).process_products(raw_names)`; Assert: normalised names in same order as input
  - `TestVendorsService`:
    - `test_process_vendor_happy_path` — Arrange: mock returns normalised vendor string; Act: `VendorsService(client=mock).process_vendor("raw")`; Assert: returns non-empty string
  - `TestBudgetSimulationService` (uses mocked `openai_client` + mocked repo):
    - `test_generate_ai_recommendations` — Arrange: mock LLM returns recommendation strings; Act: `service.generate_ai_recommendations(financial_data)`; Assert: returns list of strings
    - `test_run_projection_calls_repo` — Arrange: mock repo returns sample transactions; Act: `service.run_projection(params)`; Assert: repo `get_monthly_breakdown` called at least once

**Checkpoint**: `pytest backend/tests/unit/test_services_llm.py -v` — all tests pass; `vcr` / network call verification confirms zero outbound requests.

---

## Phase 5: User Story 3 — Infrastructure Services (Priority: P2)

**Goal**: Unit tests for `MinioStorageService` and `PusherService` using mocked adapters.

**Independent Test**: `python -m pytest backend/tests/unit/test_services_infra.py -v`

**Note**: Independent of Phase 2 — can start after Phase 1.

- [X] T010 [P] [US3] Create `backend/tests/unit/test_services_infra.py` with `@pytest.mark.unit` on all test classes; implement:
  - `TestMinioStorageService` (use `MagicMock()` for the Minio client, injected at construction or via `service.client = mock`):
    - `test_upload_image_calls_put_object` — Arrange: `mock_minio = MagicMock()`; Act: `service.upload_image(key, data, content_type)`; Assert: `mock_minio.put_object` called once with correct bucket, key, content type
    - `test_upload_image_propagates_exception` — Arrange: `mock_minio.put_object.side_effect = Exception("storage error")`; Assert: `pytest.raises(Exception)` propagates (not swallowed)
    - `test_download_image_returns_bytes` — Arrange: mock `get_object` returns object with `.read()` returning `b"data"`; Act: `service.download_image(key)`; Assert: `== b"data"`
    - `test_get_temp_file_creates_file` — Arrange: mock `get_object` returns binary stream; Act: `path = service.get_temp_file(key)`; Assert: `os.path.exists(path)` is True; cleanup: `os.remove(path)`
  - `TestPusherService` (use `MagicMock()` for the pusher client):
    - `test_trigger_calls_pusher` — Arrange: `mock_pusher = MagicMock()`; inject into `PusherService`; Act: `service.trigger(channel, event, data)`; Assert: underlying trigger method called with correct channel, event, data

**Checkpoint**: `pytest backend/tests/unit/test_services_infra.py -v` — 5 tests pass.

---

## Phase 6: User Story 4 — Domain and Calculation Services (Priority: P2)

**Goal**: Unit tests for `BudgetAnalysisService`, `BudgetGoalsService`, `GroundTruthService`, and `EvaluationService` (metrics + async orchestration).

**Independent Test**: `python -m pytest backend/tests/unit/test_services_domain.py -v`

**Note**: Independent of Phase 2 — can start after Phase 1.

- [X] T011 [P] [US4] Create `backend/tests/unit/test_services_domain.py` with `@pytest.mark.unit` on all test classes; implement:
  - `TestBudgetAnalysisService` (repos injected as `MagicMock()`):
    - `test_get_monthly_breakdown_aggregates_correctly` — Arrange: mock repo returns fixed transaction list; Act: `service.get_monthly_breakdown(year, month)`; Assert: returned totals match expected aggregation
    - `test_check_affordability` — Arrange: mock repo returns income/expense data; Act: `service.check_affordability(amount, category)`; Assert: returns bool or structured result indicating affordability
  - `TestBudgetGoalsService` (repos injected as `MagicMock()`):
    - `test_get_monthly_surplus_equals_income_minus_expenses` — Arrange: mock repo returns income 5000, expenses 3000; Act: `service.get_monthly_surplus(year, month)`; Assert: result == 2000
    - `test_create_goal_calls_repo` — Arrange: mock repo; Act: `service.create_goal(goal_data)`; Assert: repo `create` called once with correct data
  - `TestGroundTruthService` (repos and services injected as `MagicMock()`):
    - `test_create_stores_entry` — Arrange: mock repo; Act: `service.create(entry_data)`; Assert: repo `create` called once
    - `test_create_from_confirmed_receipt` — Arrange: mock receipt repo returns receipt with products; Act: `service.create_from_confirmed_receipt(receipt_id)`; Assert: ground truth repo `create` called with data derived from receipt
  - `TestEvaluationServiceCalculateMetrics` (pure method — no mocks needed):
    - `test_all_fields_match_ground_truth` — Arrange: build `TransactionModel` and identical ground truth; Act: `EvaluationService(...).calculate_metrics(txn, 100, ground_truth=gt)`; Assert: `vendor_correct=True`, `date_correct=True`, `total_correct=True`, `products_accuracy=1.0`
    - `test_ground_truth_none_returns_none_fields` — Arrange: any transaction, `ground_truth=None`; Assert: `vendor_correct is None`, `date_correct is None`, `total_correct is None`
    - `test_products_accuracy_both_empty` — Arrange: transaction with no products, GT with no products; Assert: `products_accuracy=1.0`
    - `test_total_zero_ground_truth_no_division_error` — Arrange: GT transaction with `total=0`, extracted `total=0`; Act/Assert: no exception raised; `total_accuracy=1.0`
    - `test_products_accuracy_no_match` — Arrange: extracted products empty, GT has one product; Assert: `products_accuracy=0.0`
  - `TestEvaluationServiceAsync` (all deps injected as `MagicMock()`):
    - `test_run_evaluation_async_single_entry` — `async def`; Arrange: mock `ground_truth_repository.get_all` returns one entry; mock `minio_service.get_temp_file` returns tmp path; mock `preprocessing_service.preprocess_image` returns same path; mock `ocr_service.process_image_async` returns valid JSON dict; Act: `await service.run_evaluation_async()`; Assert: `evaluations_repository.add_result` called exactly once; returned summary has `total_files=1`, `successful=1`
    - `test_run_evaluation_async_empty_ground_truth` — `async def`; Arrange: mock returns empty list; Act: `await service.run_evaluation_async()`; Assert: returns summary with `total_files=0`; `add_result` never called

**Checkpoint**: `pytest backend/tests/unit/test_services_domain.py -v` — all tests pass.

---

## Phase 7: User Story 5 — Image-Processing Services (Priority: P3)

**Goal**: Unit tests for `PreprocessingService` (PIL-based) and `TextLocalizationService` (subprocess PaddleOCR).

**Independent Test**: `python -m pytest backend/tests/unit/test_services_image.py -v`

- [X] T012 [P] [US5] Create `backend/tests/unit/test_services_image.py` with `@pytest.mark.unit` on all test classes; implement:
  - `TestPreprocessingService` — no mocks needed; use `tmp_path` fixture and create a 1×1 JPEG in-memory using `PIL.Image`:
    - `test_preprocess_returns_new_path` — Arrange: create `input.jpg` in `tmp_path` (1×1 white JPEG); Act: `path = PreprocessingService().preprocess_image(str(input_path))`; Assert: `os.path.exists(path)` and `path != str(input_path)`
    - `test_preprocess_output_within_max_dimension` — Arrange: same 1×1 input; Act: preprocess; Assert: open output with PIL; both dimensions `<= PreprocessingService.MAX_SIZE` (or whatever constant the service uses)
  - `TestTextLocalizationService` — mock `_get_executor` to avoid subprocess spawning:
    - `test_detect_returns_parsed_lines` — Arrange: `mock.patch("backend.src.services.text_localization._get_executor")` returns a mock executor whose `submit().result()` returns canned PaddleOCR legacy format (list of `[polygon, [text, score]]` items); Act: `TextLocalizationService().detect("fake_path")`; Assert: returns non-empty list of `(polygon, text, score)` tuples
    - `test_detect_broken_pool_retries_once` — Arrange: first `submit().result()` raises `BrokenProcessPool`; second returns valid result; Act: `detect()`; Assert: no exception raised; returned list is valid
    - `test_detect_async_delegates_to_detect` — `async def`; Arrange: patch `instance.detect = MagicMock(return_value=[canned_line])`; Act: `await service.detect_async("path")`; Assert: `instance.detect` called once; result equals canned output

**Checkpoint**: `pytest backend/tests/unit/test_services_image.py -v` — 5 tests pass without PaddleOCR installed.

---

## Final Phase: Validation & Polish

**Purpose**: Verify the full unit suite passes the coverage gate and no regressions exist.

- [X] T013 Run `cd backend && python -m pytest -m unit -v` — verify all new and existing unit tests pass; confirm coverage report printed shows `src/services` ≥ 80%; if below, identify uncovered lines and add targeted test cases to the relevant test file until gate passes

**Checkpoint**: `pytest -m unit` exits with code 0; coverage report shows ≥ 80% for `src/services`; `pytest -m integration` still passes (no regressions in pipeline test).

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (T001, T002)
    └── Phase 2 (T003–T007) [all parallel]   ← blocks T009 only
    └── Phase 3 (T008)                         ← can start with Phase 2
    └── Phase 5 (T010)                         ← can start with Phase 2
    └── Phase 6 (T011)                         ← can start with Phase 2
    └── Phase 7 (T012)                         ← can start with Phase 2
Phase 2 complete
    └── Phase 4 (T009)
All phases complete
    └── Final (T013)
```

### User Story Dependencies

| Story | Depends On | Parallel With |
|-------|-----------|---------------|
| US1 (T008) | Phase 1 | T003–T007, T010, T011, T012 |
| US2 (T009) | Phase 2 (T003–T007) | T010, T011, T012 |
| US3 (T010) | Phase 1 | T008, T009, T011, T012 |
| US4 (T011) | Phase 1 | T008, T009, T010, T012 |
| US5 (T012) | Phase 1 | T008, T009, T010, T011 |

### Parallel Execution Example (single session — optimal order)

```bash
# Step 1 — Sequential setup
T001 → T002

# Step 2 — Parallel batch (5 refactors + US1 test + US3/US4/US5 tests)
T003, T004, T005, T006, T007   # service DI refactors (all independent files)
T008                            # US1 pure-logic tests (no dependency on refactors)
T010, T011, T012               # US3, US4, US5 tests (no dependency on refactors)

# Step 3 — After Phase 2 completes
T009                            # US2 LLM tests (requires refactored constructors)

# Step 4 — Final validation
T013
```

---

## Parallel Example: Phase 2 Refactors

```text
# All 5 can be dispatched simultaneously (different service files):
Task T003: Add optional client params to backend/src/services/ocr.py
Task T004: Add optional client params to backend/src/services/categories.py
Task T005: Add optional client params to backend/src/services/bank_categorization.py
Task T006: Add optional client params to backend/src/services/products.py
Task T007: Add optional client params to backend/src/services/vendors.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001, T002)
2. Complete Phase 3 (T008)
3. **STOP and validate**: `pytest backend/tests/unit/test_services_pure.py -v` — 11 tests pass
4. Pure-logic services are now regression-safe

### Incremental Delivery

1. Setup (Phase 1) → Foundation ready
2. US1 (Phase 3) → Pure-logic services covered → demo-able
3. Phase 2 refactors → unblocks US2
4. US2 (Phase 4) + US3 (Phase 5) + US4 (Phase 6) in parallel → LLM + infra + domain covered
5. US5 (Phase 7) → image pipeline covered
6. Validation (T013) → coverage gate confirmed

---

## Notes

- [P] tasks = different files, no unresolved dependencies — safe to run in parallel
- [Story] label maps each task to the user story from spec.md for traceability
- `MarkdownTableService` inherits `ABC` but has no `@abstractmethod` — can be instantiated directly
- `TextLocalizationService` uses module-level subprocess executor — `mock.patch` on `_get_executor` is the justified exception to the no-monkey-patching rule (architecture constraint, not business logic)
- All `async def` tests use `asyncio_mode = auto` from `pytest.ini` (no `@pytest.mark.asyncio` decorator needed)
- Temp files created by `test_get_temp_file_creates_file` must be cleaned up within the test
