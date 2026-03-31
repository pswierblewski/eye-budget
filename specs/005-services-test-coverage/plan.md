# Implementation Plan: Backend Services Test Coverage

**Branch**: `005-services-test-coverage` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/005-services-test-coverage/spec.md`

## Summary

Add dedicated unit tests for all 16 service classes in `backend/src/services/`. This requires refactoring five LLM service constructors to accept optional injected clients (matching the pattern already used in `BudgetSimulationService`), adding `pytest-asyncio` to test dependencies, and writing five new test files grouped by external-dependency type. No database schema changes. No API changes. No frontend changes.

---

## Technical Context

**Language/Version**: Python 3.11.7  
**Primary Dependencies**: pytest ≥8.0, pytest-mock ≥3.14, pytest-cov ≥5.0, pytest-asyncio ≥0.23 (new), unittest.mock (stdlib)  
**Storage**: N/A (tests mock all storage)  
**Testing**: pytest — unit tests only; existing integration tests unchanged  
**Target Platform**: Linux (WSL2 dev, CI runner)  
**Project Type**: backend test suite extension  
**Performance Goals**: Full unit suite < 20 s (SC-002)  
**Constraints**: No real DB, MinIO, OpenAI, Soketi, or PaddleOCR in unit tests  
**Scale/Scope**: 16 services, 5 new test files, ~60–80 new test cases  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ Pass | Constructor injection refactor maintains single-responsibility; no hardcoded secrets |
| II. Testing Standards | ✅ Pass | This feature *is* the testing improvement; all new code is tested by definition |
| III. UX Consistency | ✅ Pass | No frontend changes |
| IV. Performance | ✅ Pass | No new API endpoints; test suite time gate SC-002 ≤20s enforced |
| V. Frontend Architecture | ✅ Pass | No frontend changes |
| VI. Backend Conventions | ✅ Pass | Services continue to use constructor injection; no globals introduced |
| API Contract Integrity | ✅ Pass | No API changes |
| Quality Gates | ✅ Pass | All existing tests must continue to pass (SC-005) |

**No constitution violations. No complexity justification required.**

---

## Project Structure

### Documentation (this feature)

```text
specs/005-services-test-coverage/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 (N/A — no new entities; see note below)
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks — not created here)
```

> **data-model.md**: No new data entities. This feature adds tests and refactors constructors only. `data-model.md` is omitted.

### Source Code Changes

```text
backend/
├── requirements-test.txt          # add pytest-asyncio>=0.23
├── pytest.ini                     # new — coverage config (cov=src/services, fail-under=80)
├── src/
│   └── services/
│       ├── ocr.py                 # add optional client/async_client params
│       ├── categories.py          # add optional client param
│       ├── bank_categorization.py # add optional client/async_client params
│       ├── products.py            # add optional client param
│       └── vendors.py             # add optional client param
└── tests/
    └── unit/
        ├── test_services_pure.py  # new — PekaoCsvParser, MarkdownTableService, TextMatchingService
        ├── test_services_llm.py   # new — OCR, Categories, BankCategorization, Products, Vendors, BudgetSimulation
        ├── test_services_infra.py # new — MinioStorageService, PusherService
        ├── test_services_domain.py# new — BudgetAnalysis, BudgetGoals, GroundTruth, EvaluationService
        └── test_services_image.py # new — PreprocessingService, TextLocalizationService
```

**Structure Decision**: Backend-only, existing directory layout. No new top-level directories.

---

## Phase 0: Research Findings

See [research.md](research.md) for full findings. Key decisions:

### D1 — LLM client injection (5 services need refactor)

`OCRService`, `CategoriesService`, `BankCategorizationService`, `ProductsService`, `VendorsService` all create `OpenAI()` / `AsyncOpenAI()` in `__init__`. Add optional params:

```python
# Pattern (matches BudgetSimulationService — canonical reference)
def __init__(self, ..., client: OpenAI | None = None):
    self.client = client if client is not None else OpenAI()
```

For services with async operations (`OCRService`, `BankCategorizationService`):
```python
def __init__(self, ..., client: OpenAI | None = None, async_client: AsyncOpenAI | None = None):
    self.client = client if client is not None else OpenAI()
    self.async_client = async_client if async_client is not None else AsyncOpenAI()
```

Production `App.__init__` requires no changes — `client=None` defaults to the real client.

### D2 — Async coverage

Three services tested for both sync and async: `OCRService`, `BankCategorizationService`, `EvaluationService`.

### D3 — `MarkdownTableService`

ABC with no `@abstractmethod` — can be instantiated directly. No concrete subclass needed.

### D4 — `TextLocalizationService` — subprocess executor pattern

`TextLocalizationService.detect()` uses a module-level `ProcessPoolExecutor` (`_get_executor()`) that spawns a subprocess where PaddleOCR lives. There is no constructor parameter to inject.

**Strategy**: Mock `_get_executor` at module level using `mock.patch`. This is a justified exception to FR-003's no-monkey-patching rule because the subprocess pool is an infrastructure concern, not business logic — there is no other way to prevent subprocess spawning in a unit test.

`detect_async()` simply calls `detect()` in a thread executor; test by patching `instance.detect` directly on the service object.

### D5 — `pytest-asyncio`

Add `pytest-asyncio>=0.23` to `requirements-test.txt`. Use `asyncio_mode = "auto"` in `pytest.ini` to avoid per-test `@pytest.mark.asyncio` decorators.

### D6 — Coverage gate

Create `backend/pytest.ini` with:
```ini
[pytest]
asyncio_mode = auto
addopts = --cov=src/services --cov-report=term-missing --cov-fail-under=80
markers =
    unit: Unit tests (no infrastructure)
    integration: Integration tests (requires Docker)
```

---

## Phase 1: Design

### 1.1 — Service constructor changes (detailed)

#### `OCRService` (ocr.py)
```python
# Before
self.client = OpenAI()
self.async_client = AsyncOpenAI()

# After
self.client = client if client is not None else OpenAI()
self.async_client = async_client if async_client is not None else AsyncOpenAI()
```
Constructor signature: `def __init__(self, model, prompt, client=None, async_client=None)`

#### `CategoriesService` (categories.py)
```python
# After
self.client = client if client is not None else OpenAI()
```
Constructor signature: `def __init__(self, ..., client=None)` — existing params preserved.

#### `BankCategorizationService` (bank_categorization.py)
```python
# After
self.client = client if client is not None else OpenAI()
self.async_client = async_client if async_client is not None else AsyncOpenAI()
```

#### `ProductsService` (products.py)
```python
# After
self.client = client if client is not None else OpenAI()
```

#### `VendorsService` (vendors.py)
```python
# After
self.client = client if client is not None else OpenAI()
```

### 1.2 — Test file structure per file

#### `test_services_pure.py`

```python
# Tests: PekaoCsvParser, MarkdownTableService, TextMatchingService
# No mocks needed — pure logic

class TestPekaoCsvParser:
    def test_parse_valid_utf8(self): ...
    def test_polish_decimal_format(self): ...
    def test_row_missing_reference_skipped(self): ...
    def test_cp1250_encoding_fallback(self): ...
    def test_apostrophe_stripped_from_reference(self): ...
    def test_invalid_amount_row_skipped(self): ...

class TestMarkdownTableService:
    def test_basic_two_column_table(self): ...
    def test_columns_of_different_lengths_padded(self): ...
    def test_single_column_table(self): ...

class TestTextMatchingService:
    def test_products_matched_to_ocr_regions(self): ...
    def test_empty_product_list(self): ...
```

#### `test_services_llm.py`

```python
# Tests: OCRService, CategoriesService, BankCategorizationService,
#        ProductsService, VendorsService, BudgetSimulationService
# All use injected MagicMock() as client

class TestOCRService:
    def test_process_image_happy_path(self, mock_client): ...
    async def test_process_image_async_happy_path(self, mock_async_client): ...
    def test_process_image_malformed_json_raises(self, mock_client): ...

class TestCategoriesService:
    def test_assign_candidates_happy_path(self, mock_client): ...
    def test_assign_candidates_malformed_json_raises(self, mock_client): ...

class TestBankCategorizationService:
    def test_assign_candidates_happy_path(self, mock_client): ...
    async def test_assign_candidates_async_happy_path(self, mock_async_client): ...

class TestProductsService:
    def test_process_products_happy_path(self, mock_client): ...

class TestVendorsService:
    def test_process_vendor_happy_path(self, mock_client): ...

class TestBudgetSimulationService:
    def test_generate_ai_recommendations(self, mock_client): ...
    def test_run_projection(self, mock_repo): ...
```

#### `test_services_infra.py`

```python
class TestMinioStorageService:
    def test_upload_image_calls_put_object(self, mock_minio): ...
    def test_upload_image_propagates_exception(self, mock_minio): ...
    def test_download_image_returns_bytes(self, mock_minio): ...
    def test_get_temp_file_creates_and_cleans_up(self, mock_minio, tmp_path): ...

class TestPusherService:
    def test_trigger_calls_pusher_client(self, mock_pusher): ...
```

#### `test_services_domain.py`

```python
class TestBudgetAnalysisService:
    def test_get_monthly_breakdown(self, mock_repo): ...
    def test_check_affordability(self, mock_repo): ...

class TestBudgetGoalsService:
    def test_get_monthly_surplus(self, mock_repo): ...
    def test_create_goal(self, mock_repo): ...

class TestGroundTruthService:
    def test_create(self, mock_repo): ...
    def test_create_from_confirmed_receipt(self, mock_deps): ...

class TestEvaluationServiceCalculateMetrics:
    def test_all_fields_match_ground_truth(self): ...
    def test_ground_truth_none_returns_none_fields(self): ...
    def test_products_accuracy_both_empty(self): ...
    def test_total_zero_no_division_error(self): ...
    def test_products_accuracy_no_match(self): ...

class TestEvaluationServiceAsync:
    async def test_run_evaluation_async_single_entry(self, mock_deps): ...
    async def test_run_evaluation_async_empty_ground_truth(self, mock_deps): ...
```

#### `test_services_image.py`

```python
class TestPreprocessingService:
    def test_preprocess_image_returns_new_path(self, tmp_path): ...
    def test_preprocess_image_output_within_max_dimension(self, tmp_path): ...

class TestTextLocalizationService:
    def test_detect_returns_parsed_lines(self): ...   # mocks _get_executor
    def test_detect_broken_pool_retries(self): ...
    async def test_detect_async_delegates_to_detect(self): ...  # mocks instance.detect
```

### 1.3 — `pytest.ini` (new file in `backend/`)

```ini
[pytest]
asyncio_mode = auto
addopts = --cov=src/services --cov-report=term-missing --cov-fail-under=80
markers =
    unit: Unit tests (no infrastructure)
    integration: Integration tests (requires Docker)
```

> **Note**: The existing integration tests run with `-m integration` and are unaffected by the coverage gate on `src/services` since they test the pipeline end-to-end and likely exceed 80%.

### 1.4 — `requirements-test.txt` update

Add:
```
pytest-asyncio>=0.23
```

---

## Contracts

No new API endpoints or public interfaces. This section is not applicable.

---

## Complexity Tracking

> No constitution violations — table not required.

---

## Post-Phase 1 Constitution Re-check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ | Constructor refactors maintain single responsibility |
| II. Testing Standards | ✅ | All 16 services covered; async variants tested |
| VI. Backend Conventions | ✅ | Services receive deps via constructor injection — no globals |

All gates pass.
