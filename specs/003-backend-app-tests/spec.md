# Feature Specification: Backend App.py Testability & Test Coverage

**Feature Branch**: `003-backend-app-tests`
**Created**: 2026-03-18
**Status**: Draft
**Input**: User description: "the project doesn't have any tests written. Analyze backend/src/app.py for testability, refactor if needed, then cover with tests."

---

## Clarifications

### Session 2026-03-18

- Q: What test layers are needed beyond unit tests? → A: Unit tests + integration tests with real PostgreSQL and real MinIO (both in Docker); only LLM/OCR responses are mocked.
- Q: How should Docker containers be managed for integration tests? → A: `testcontainers-python` — containers spun up and torn down automatically by pytest, no manual steps required.
- Q: Should the 80% coverage threshold be a hard gate or soft advisory? → A: Hard gate — test run fails if unit test coverage drops below 80%.
- Q: Where should test files live? → A: `backend/tests/` — sibling directory to `backend/src/`.
- Q: How should the integration test DB schema be applied? → A: Run yoyo migrations at the start of each test session (project uses yoyo-migrations, not Alembic).

---

## Context: Testability Analysis of app.py

Before defining user stories, this feature requires an honest analysis of the current `App` class.

### Current State (Anti-patterns found)

| Problem | Location | Impact on Testing |
|---------|----------|-------------------|
| **God Object** – 1500+ lines, 50+ methods, all concerns in one class | Entire file | Any test must construct the full object |
| **Hard-wired instantiation** – all repos/services created with `self.x = SomeClass()` in `__init__` | Lines 106–152 | Cannot substitute test doubles without monkey-patching |
| **No constructor injection** – callers cannot supply mock dependencies | `__init__` | Unit tests must hit real DB, MinIO, LLM |
| **Inline imports** – `import datetime`, `import json`, `import tempfile` inside methods | Lines 559, 799, 1130, 1201, 1484 | Minor but signals rushed-in logic |
| **Complex orchestration inlined** – `confirm_receipt` is 100 lines of business logic | Lines 514–618 | One method tests 10+ behaviors at once |
| **No protocols/ABCs for dependencies** – nothing to mock against | All dependencies | Test doubles must guess the interface |

### Refactoring Required (before tests)

1. **Dependency Injection** – change `__init__` to accept optional pre-built repos/services; keep auto-build as default. This makes unit tests inject fakes without touching real infrastructure.
2. **Extract domain-scoped mixins or sub-apps** – e.g. `ReceiptApp`, `BankApp`, `CashApp`, `BudgetApp` — each small enough to test in isolation.
3. **Define lightweight protocols** for repositories/services so mocks have a stable contract.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refactor App for Dependency Injection (Priority: P1)

A developer wants to write a unit test for any `App` method without spinning up a real PostgreSQL database, a real MinIO instance, or making real LLM API calls. Today that is impossible because all dependencies are hard-wired in `__init__`.

**Why this priority**: Without this refactor, every test either hits real infrastructure (slow, flaky, expensive) or requires fragile monkey-patching. All subsequent test stories depend on this.

**Independent Test**: Can be validated by instantiating `App` with mock repositories injected through the constructor and calling one method — the method should use the injected mock, not create its own live connection.

**Acceptance Scenarios**:

1. **Given** a developer creates a mock object implementing the `ReceiptsScansRepository` interface, **When** they pass it to `App(receipts_scans_repository=mock)`, **Then** `App` uses the mock instead of creating a live repository.
2. **Given** an `App` is constructed with all default parameters and no arguments, **When** it initialises, **Then** it behaves exactly as before (backwards compatible).
3. **Given** any repository or service argument is passed as `None` or omitted, **When** `App.__init__` runs, **Then** it falls back to constructing the real implementation automatically.

---

### User Story 2 - Unit Tests: Receipt Confirmation Logic (Priority: P2)

A developer wants to verify that `confirm_receipt` correctly applies field overrides, creates the transaction, assigns categories, auto-links to bank/cash transactions, and records analytics — all without a real database.

**Why this priority**: `confirm_receipt` is the most complex and business-critical method in the file. Bugs here cause data loss or incorrect financial records.

**Independent Test**: With mock repositories injected, call `confirm_receipt` with various request combinations and assert the correct repository methods were called with the correct arguments.

**Acceptance Scenarios**:

1. **Given** a scan exists with an OCR result, **When** `confirm_receipt` is called with vendor/date/total overrides, **Then** the overrides are applied before the transaction is created and the raw result is updated in the repository.
2. **Given** `request.normalized_vendor` is provided, **When** `confirm_receipt` runs, **Then** the vendor is looked up or created and the raw name is inserted as an alternative name.
3. **Given** `request.normalized_vendor` is absent, **When** `confirm_receipt` runs, **Then** the vendor is resolved via the standard lookup path.
4. **Given** a product has a matching category candidate, **When** the user selects a different category, **Then** the correction is recorded in prompt analytics.
5. **Given** the analytics step throws an exception, **When** `confirm_receipt` runs, **Then** the exception is swallowed (non-fatal) and confirmation still succeeds.

---

### User Story 3 - Unit Tests: Auto-Link Logic (Priority: P3)

A developer wants to verify that `_auto_link_receipt`, `_auto_link_bank_transactions`, and `_auto_link_cash_transaction` correctly link transactions and merge tags — without real DB calls.

**Why this priority**: Auto-linking is invisible to the user and therefore likely to regress silently. Tag merging is stateful logic that is easy to break.

**Independent Test**: With mock repositories, call each auto-link method and assert the correct link-creation and tag-update calls are made or not made depending on match results.

**Acceptance Scenarios**:

1. **Given** a matching bank transaction exists, **When** `_auto_link_receipt` runs, **Then** a bank link is created and tags from both sides are merged and written back to both records.
2. **Given** no bank match exists but a cash match does, **When** `_auto_link_receipt` runs, **Then** a cash link is created instead.
3. **Given** multiple receipt candidates exist for a bank transaction, **When** `_auto_link_bank_transactions` runs, **Then** the transaction is skipped (not linked, counted as `needs_manual_link`).
4. **Given** the auto-link call throws, **When** any auto-link method runs, **Then** the exception is logged and swallowed; it never propagates to the caller.

---

### User Story 4 - Unit Tests: Budget Analysis Delegation (Priority: P4)

A developer wants to verify that `App`'s budget-related methods correctly delegate to the underlying services and pass parameters without modification.

**Why this priority**: Budget methods are thin delegation wrappers. Tests here primarily guard against typos in argument forwarding and catch regressions after refactors.

**Independent Test**: Mock `budget_analysis_service` and `budget_goals_service`, call each App budget method, and assert the service was called with the expected arguments.

**Acceptance Scenarios**:

1. **Given** a mock `budget_analysis_service`, **When** `get_monthly_breakdown(2025, 3)` is called, **Then** the service receives exactly `year=2025, month=3`.
2. **Given** `check_affordability` is called, **When** it runs, **Then** it fetches the current financial focus and active goal allocations before delegating to the service.

---

### User Story 5 - Integration Tests: Receipt Processing Pipeline (Priority: P5)

A developer wants a smoke-level integration test that exercises the full `_process_single_file` flow against a real (test) database, confirming the pipeline succeeds end-to-end.

**Why this priority**: Lower priority because it requires real infrastructure, but provides high confidence that the pieces work together. Can be skipped in CI if infrastructure is not available.

**Independent Test**: Spin up the test database and a mock MinIO + OCR stub, call `_process_single_file` with a test image, and assert the scan ends in PROCESSED status with a populated result.

**Acceptance Scenarios**:

1. **Given** a valid image file in the input directory, **When** `_process_single_file` is called, **Then** the scan status transitions PROCESSING → PROCESSED and `result` is non-null.
2. **Given** the OCR service raises an exception, **When** `_process_single_file` is called, **Then** the scan status is set to FAILED and the error message is stored.

---

### Edge Cases

- What happens when `confirm_receipt` is called on a scan with no OCR result?
- How does `_auto_link_receipt` behave when the bank link creation fails (returns `False`)?
- What if `get_all_tags` is called when the DB connection is not established?
- What if `update_receipt_tags` is called on a receipt that has both a bank and a cash link simultaneously?
- What if `create_simulation` is called with an invalid `expense_type`?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `App` class MUST accept optional pre-constructed repositories and services via constructor parameters to enable dependency injection for testing.
- **FR-002**: All repositories and all services MUST be injectable via constructor keywords, each defaulting to `None` (auto-constructed when not provided).
- **FR-003**: Existing production behaviour MUST remain unchanged when `App()` is constructed with no arguments.
- **FR-004**: Unit tests MUST cover `confirm_receipt` for at least: override application, vendor resolution (both paths), product category assignment, analytics recording, and auto-link trigger.
- **FR-005**: Unit tests MUST cover all three auto-link methods (`_auto_link_receipt`, `_auto_link_bank_transactions`, `_auto_link_cash_transaction`) including the no-match and exception paths.
- **FR-006**: Unit tests MUST cover all budget delegation methods, asserting correct argument forwarding to the underlying services.
- **FR-007**: Unit tests MUST be runnable without any real database, MinIO, or LLM service available (all infrastructure fully mocked).
- **FR-007b**: Integration tests MUST run against a real PostgreSQL instance and a real MinIO instance, both managed automatically via `testcontainers-python` (no manual `docker` commands required); LLM and OCR responses are always mocked in integration tests.
- **FR-007c**: The integration test session fixture MUST run yoyo migrations against the test PostgreSQL container before any integration test executes, ensuring the schema always matches production.
- **FR-008**: Tests MUST use the standard Python `unittest.mock` library (or `pytest-mock`) for creating doubles — no monkey-patching of the production module.
- **FR-009**: Each test file MUST correspond to a logical domain (receipts, bank, cash, budget) rather than one monolithic test file, organised under `backend/tests/unit/` and `backend/tests/integration/`.
- **FR-010**: The refactored `App.__init__` MUST preserve the existing service-wiring order (categories build, bank categorization build) to avoid breaking startup contracts.
- **FR-011**: Tests MUST be run using the existing Python virtual environment in the project root (`venv/`).

### Key Entities

- **App**: The main application class — orchestrates all repositories and services. Target of both refactoring and testing.
- **Repository**: Each database-access object injected into `App`. Must have a stable interface for mocking.
- **Service**: Each domain-logic object (OCR, vendors, categories, budget). Must be injectable.
- **Test Double**: A mock, stub, or fake object used in tests to replace a real dependency.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All unit tests pass without any running database, object storage, or external API.
- **SC-001b**: Integration tests pass against real PostgreSQL and MinIO containers started automatically by `testcontainers-python`; LLM/OCR are stubbed.
- **SC-002**: `App` can be instantiated in tests with all dependencies replaced by mocks in under 50ms.
- **SC-003**: Unit test suite covers at least 80% statement coverage for `app.py` methods (excluding trivial delegation wrappers and `__init__` wiring); this threshold is enforced as a hard gate — the test run fails if coverage falls below 80%.
- **SC-004**: The full unit test suite completes in under 10 seconds on developer hardware.
- **SC-005**: No existing production behaviour is broken — all existing API endpoint behaviour remains identical after the refactor.
- **SC-006**: Tests are organised in at least 4 domain-scoped files (receipts, bank/cash, budget, auto-link) making it easy to find tests related to a specific area.

---

## Assumptions

- The project uses Python 3.11+ and `pytest` is the preferred test runner.
- `unittest.mock.MagicMock` or `pytest-mock`'s `mocker` fixture will be used for test doubles.
- The refactoring is limited to `app.py` constructor signature — no method bodies are changed unless required to remove untestable patterns.
- Integration tests use `testcontainers-python` to manage PostgreSQL and MinIO containers; Docker must be available on the host running the tests.
- yoyo migrations are assumed to exist and to be the authoritative source of the DB schema.
- No new abstractions (ABCs/Protocols) are required unless they naturally emerge from the dependency injection refactor.
- The virtual environment at `venv/` in the project root is used for running tests (`venv/bin/pytest`).
