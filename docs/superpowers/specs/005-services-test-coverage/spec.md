# Feature Specification: Backend Services Test Coverage

**Feature Branch**: `005-services-test-coverage`
**Created**: 2026-03-30
**Status**: Draft
**Input**: User description: "chcę zwiększyć pokrycie testami. Kontynuujemy po 003-backend-app-tests. Chcę pokryć testami wszystko, co jest w katalogu services."

## Context

Feature **003-backend-app-tests** established the test infrastructure: dependency injection refactor of the `App` class, unit/integration test organisation, and the `make_app()` factory. That work focused on the *App layer* (routes, orchestration). This feature goes one level deeper and adds dedicated unit tests for every service class in `backend/src/services/`.

Sixteen service files are in scope:

| Service | Role | External deps |
|---------|------|---------------|
| `bank_csv_parser.py` | Parse Pekao SA CSV exports | none |
| `markdown_table.py` | Generate markdown tables | none |
| `text_matching.py` | Match LLM output to OCR regions | none |
| `preprocessing.py` | Resize / convert receipt images | PIL |
| `ocr.py` | Extract receipt data via vision LLM | OpenAI API |
| `categories.py` | Assign category candidates via LLM | OpenAI API |
| `bank_categorization.py` | Assign categories to bank transactions | OpenAI API |
| `products.py` | Normalise product names via LLM | OpenAI API |
| `vendors.py` | Normalise vendor names via LLM | OpenAI API |
| `budget_simulation.py` | Run projections, generate AI recommendations | OpenAI API, DB |
| `budget_analysis.py` | Monthly breakdown, affordability, emergency advice | DB |
| `budget_goals.py` | Goal CRUD, monthly surplus | DB |
| `ground_truth.py` | Ground truth entry management | DB |
| `evaluation.py` | Run OCR accuracy evaluation against ground truth | DB, MinIO, OCR |
| `minio_storage.py` | Upload / download / delete images | MinIO S3 |
| `pusher_service.py` | Push WebSocket events to Soketi | HTTP |
| `text_localization.py` | Detect text regions via PaddleOCR | PaddleOCR |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Pure-logic services are fully covered (Priority: P1)

As a developer, when I change parsing, matching, or table-generation logic I want tests to tell me immediately if I introduced a regression, without needing any running infrastructure.

Services: `bank_csv_parser`, `markdown_table`, `text_matching`.

**Why this priority**: Zero external dependencies, so tests are trivially fast and reliable. These services have the highest testability ratio and deliver the most coverage per line of test code.

**Independent Test**: Run `pytest tests/unit/test_services_pure.py` — all pass with no containers, no network, no mocks needed.

**Acceptance Scenarios**:

1. **Given** a valid Pekao SA CSV byte string (UTF-8), **When** `PekaoCsvParser.parse_bytes()` is called, **Then** it returns a list of parsed transaction rows with correct amounts, dates, and reference numbers.
2. **Given** a CSV with Polish-locale amount strings like `"-1 014,31"`, **When** parsed, **Then** the decimal value `-1014.31` is produced.
3. **Given** a CSV row missing a reference number, **When** parsed, **Then** that row is silently skipped and not included in the result.
4. **Given** CP1250-encoded bytes, **When** parsed, **Then** the parser falls back through the encoding list and decodes successfully.
5. **Given** column lists of different lengths, **When** `MarkdownTableService.table()` is called, **Then** shorter columns are padded with empty cells and the output is a valid markdown table string.
6. **Given** LLM-extracted product names and a list of OCR candidate regions, **When** `TextMatchingService.match()` is called, **Then** each product is paired with its best-scoring candidate region.

---

### User Story 2 — LLM-dependent services are tested with mocked LLM calls (Priority: P2)

As a developer, when I modify a prompt or response-parsing logic I want unit tests to verify the parsing and business logic independently of actual OpenAI API usage.

Services: `ocr`, `categories`, `bank_categorization`, `products`, `vendors`, `budget_simulation`.

**Why this priority**: LLM integration is the core value-add of the product. Regressions here (changed prompt format, broken JSON parsing) should be caught before reaching production.

**Independent Test**: Run `pytest tests/unit/test_services_llm.py` — all pass without real API keys; the OpenAI client is injected as a mock.

**Acceptance Scenarios**:

1. **Given** a mocked LLM response returning a valid JSON receipt, **When** `OCRService.process_image()` is called, **Then** a populated transaction model is returned.
2. **Given** a mocked LLM response, **When** `OCRService.process_image_async()` is called, **Then** it returns the same result as the sync variant for equivalent input.
3. **Given** a mocked LLM response returning malformed JSON, **When** any LLM service is called, **Then** a descriptive exception is raised (no silent failure).
4. **Given** a list of bank transaction descriptions, **When** `BankCategorizationService.assign_candidates()` is called with a mocked response, **Then** each transaction receives a list of category candidates.
5. **Given** a list of bank transaction descriptions, **When** `BankCategorizationService.assign_candidates_async()` is called with a mocked response, **Then** it returns the same result as the sync variant.
6. **Given** a list of raw product names, **When** `ProductsService.process_products()` is called with a mocked response, **Then** normalised names are returned in the same order.
7. **Given** a raw vendor string, **When** `VendorsService.process_vendor()` is called with a mocked response, **Then** a normalised vendor name string is returned.
8. **Given** monthly financial data, **When** `BudgetSimulationService.generate_ai_recommendations()` is called with a mocked LLM, **Then** a list of recommendation strings is returned.

---

### User Story 3 — Infrastructure-dependent services are tested with mocked adapters (Priority: P2)

As a developer, when I change how the app stores files or sends WebSocket events I want tests that verify the adapter contracts without needing a running MinIO or Soketi instance.

Services: `minio_storage`, `pusher_service`.

**Why this priority**: Storage and eventing bugs are silent and hard to reproduce in production. Tests with mocked adapters catch interface misuse early.

**Independent Test**: Run `pytest tests/unit/test_services_infra.py` — all pass without real MinIO or Soketi.

**Acceptance Scenarios**:

1. **Given** a mocked storage client, **When** `MinioStorageService.upload_image()` is called with image bytes, **Then** the client's upload method is called once with the correct bucket, key, and content type.
2. **Given** a mocked storage client that raises an exception on upload, **When** `upload_image()` is called, **Then** the exception propagates to the caller without being swallowed.
3. **Given** a mocked storage client returning image bytes, **When** `download_image()` is called, **Then** the same bytes are returned.
4. **Given** a mocked event client, **When** `PusherService.trigger()` is called with a channel and event payload, **Then** the underlying trigger method is invoked with the correct arguments.

---

### User Story 4 — Calculation and domain services are tested for correctness (Priority: P2)

As a developer, when I touch financial calculations or ground-truth management I want deterministic tests that confirm the logic is correct independently of any database.

Services: `budget_analysis`, `budget_goals`, `ground_truth`, `evaluation.calculate_metrics`.

**Why this priority**: Financial calculation bugs have direct user-visible impact (wrong numbers, wrong advice).

**Independent Test**: Run `pytest tests/unit/test_services_domain.py` — all pass with mocked repositories.

**Acceptance Scenarios**:

1. **Given** a set of transaction records, **When** `BudgetAnalysisService.get_monthly_breakdown()` is called with a mocked repository, **Then** totals per category and per month are correctly aggregated.
2. **Given** income and expense amounts, **When** `BudgetGoalsService.get_monthly_surplus()` is called, **Then** the surplus equals income minus total expenses.
3. **Given** a completed OCR transaction and a ground truth transaction, **When** `EvaluationService.calculate_metrics()` is called, **Then** `vendor_correct`, `date_correct`, `total_correct`, and `products_accuracy` reflect the comparison accurately.
4. **Given** mocked repositories and a single ground truth entry, **When** `EvaluationService.run_evaluation_async()` is called, **Then** it completes without error, calls `add_result` exactly once, and returns a valid summary.
5. **Given** an empty extracted product list and an empty ground-truth product list, **When** `calculate_metrics()` computes products accuracy, **Then** accuracy equals 1.0.
6. **Given** a ground truth transaction with `total = 0`, **When** `calculate_metrics()` computes total accuracy, **Then** no division-by-zero error occurs and the result is valid.

---

### User Story 5 — Image-processing services are testable with synthetic data (Priority: P3)

As a developer, I want tests for `preprocessing` and `text_localization` that verify the transform pipeline without requiring real receipt photos or GPU-based OCR inference.

Services: `preprocessing`, `text_localization`.

**Why this priority**: These services sit at the start of the OCR pipeline. Regressions here silently degrade recognition accuracy for all receipts.

**Independent Test**: Run `pytest tests/unit/test_services_image.py` — uses small synthetic images generated in-memory; the OCR engine is mocked.

**Acceptance Scenarios**:

1. **Given** a small valid JPEG file path, **When** `PreprocessingService.preprocess_image()` is called, **Then** a new file path is returned and the output image has the expected maximum dimension.
2. **Given** a mocked OCR engine returning canned bounding boxes, **When** `TextLocalizationService.detect()` is called, **Then** those bounding boxes are returned as the result.
3. **Given** a mocked OCR engine, **When** `detect_async()` is called, **Then** it returns the same result as the synchronous `detect()` for equivalent inputs.

---

### Edge Cases

- CSV rows where the reference number column contains only an apostrophe prefix (Pekao Excel-safe format) — the apostrophe must be stripped, not treated as an empty reference.
- LLM response with extra whitespace or markdown code fences wrapping JSON — the parser must handle these gracefully without raising.
- `MinioStorageService.get_temp_file()` creates a temporary file on disk — tests must clean up the file after asserting.
- `EvaluationService.calculate_metrics()` called with `ground_truth=None` — all comparison fields must be `None`, not raise an exception.
- `MarkdownTableService.table()` called with a single-column list — must produce a valid one-column table without crashing.
- Product name matching where the extracted list is empty but ground truth is non-empty — must return `0.0`, not raise.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A dedicated unit test file MUST exist for each of the five service groups: pure-logic, LLM, infrastructure, domain, and image-processing.
- **FR-002**: All unit tests for services MUST pass without a real database, MinIO instance, Soketi server, OpenAI API key, or PaddleOCR installation.
- **FR-003**: External dependencies (OpenAI client, MinIO client, event-push client, OCR engine) MUST be replaced with `unittest.mock` / `pytest-mock` test doubles; no monkey-patching of module internals.
- **FR-011**: LLM service constructors (`OCRService`, `CategoriesService`, `BankCategorizationService`, `ProductsService`, `VendorsService`, `BudgetSimulationService`) MUST be refactored to accept an optional injected client parameter, defaulting to the real client in production — consistent with the DI pattern established in 003.
- **FR-004**: Each service class MUST have tests covering at least one happy-path scenario and one error or edge-case scenario. For services with both sync and async variants (`OCRService`, `BankCategorizationService`, `EvaluationService`), both variants MUST be tested.
- **FR-005**: `EvaluationService.calculate_metrics()` MUST be tested independently as a pure calculation without triggering the full evaluation pipeline.
- **FR-006**: Tests for `PekaoCsvParser` MUST cover all four supported encodings and the Polish-locale decimal format.
- **FR-007**: All new tests MUST follow the AAA (Arrange / Act / Assert) comment structure established in 003-backend-app-tests.
- **FR-008**: All new test files MUST be placed under `backend/tests/unit/` and named `test_services_<group>.py`.
- **FR-009**: The existing test suite MUST continue to pass after new tests are added (zero regressions).
- **FR-010**: New tests MUST be tagged with the `@pytest.mark.unit` marker already defined in `conftest.py`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 16 service classes have at least one dedicated test; running test collection confirms no service is untested.
- **SC-002**: The full unit test suite (including new service tests) completes in under 20 seconds on the development machine.
- **SC-003**: Statement coverage for `backend/src/services/` reaches ≥ 80 % when measured by the coverage tool.
- **SC-004**: All new unit tests pass with no real external infrastructure (no outbound network calls, no persistent file-system side effects).
- **SC-005**: Zero new failures are introduced in the existing test suite (receipts, autolink, budget, delegation, coverage_boost, di tests).

---

## Clarifications

### Session 2026-03-30

- Q: LLM service constructors — inject client or patch at module level? → A: Refactor LLM service constructors to accept an optional injected client, same pattern used for `App` in 003.
- Q: Async method variants in scope? → A: Yes — test both sync and async variants for all services that expose both (`ocr`, `bank_categorization`, `evaluation`).

---

## Assumptions

- The existing DI infrastructure from 003 (`make_app()`, injectable constructors) is stable and will not be refactored as part of this feature.
- `MarkdownTableService` is used as an ABC base class; tests will instantiate a minimal concrete subclass to exercise the `table()` method.
- `TextLocalizationService` wraps PaddleOCR in a thin adapter; tests will mock the OCR engine initialisation to avoid requiring the GPU dependency in CI.
- `PreprocessingService.preprocess_image()` reads and writes files from disk; tests will use `tempfile.TemporaryDirectory` for isolation.
- Coverage measurement uses `pytest-cov`, already present in the project's test dependencies.
