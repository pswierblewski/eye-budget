# Data Model: Backend App.py Tests

**Branch**: `003-backend-app-tests` | **Date**: 2026-03-18

---

## Overview

This feature introduces no new persistent data entities. The "data model" here documents the **test fixture entities** — the objects constructed in tests to exercise `App` — and the **DI surface** (injectable parameters) added to `App.__init__`.

---

## Injectable Dependencies (App constructor parameters)

These are the keyword arguments added to `App.__init__`. Each defaults to `None` (auto-constructed when omitted).

### DB Context (1 — critical for unit tests)

| Parameter name | Type | Why injectable |
|----------------|------|---------------|
| `eye_budget_db_context` | `EyeBudgetDbContext` | `App.__init__` constructs this unconditionally on line 103, immediately triggering `psycopg2.connect()`. Without injection, every unit test emits DB connection errors to stdout even when all repos are mocked. |

### Repositories (17)

| Parameter name | Type | Auto-constructed from |
|----------------|------|-----------------------|
| `receipts_scans_repository` | `ReceiptsScansRepository` | `EyeBudgetDbContext` |
| `transactions_repository` | `TransactionsRepository` | `EyeBudgetDbContext` |
| `bank_transactions_repository` | `BankTransactionsRepository` | `EyeBudgetDbContext` |
| `bank_receipt_links_repository` | `BankReceiptLinksRepository` | `EyeBudgetDbContext` |
| `cash_transactions_repository` | `CashTransactionsRepository` | `EyeBudgetDbContext` |
| `cash_receipt_links_repository` | `CashReceiptLinksRepository` | `EyeBudgetDbContext` |
| `unified_transactions_repository` | `UnifiedTransactionsRepository` | `EyeBudgetDbContext` |
| `budget_analysis_repository` | `BudgetAnalysisRepository` | `EyeBudgetDbContext` |
| `budget_goals_repository` | `BudgetGoalsRepository` | `EyeBudgetDbContext` |
| `budget_simulations_repository` | `BudgetSimulationsRepository` | `EyeBudgetDbContext` |
| `categories_repository` | `CategoriesRepository` | `EyeBudgetDbContext` |
| `vendors_repository` | `VendorsRepository` | `EyeBudgetDbContext` |
| `products_repository` | `ProductsRepository` | `EyeBudgetDbContext` |
| `evaluations_repository` | `EvaluationsRepository` | `EyeBudgetDbContext` |
| `ground_truth_repository` | `GroundTruthRepository` | `EyeBudgetDbContext` |
| `files_repository` | `FilesRepository` | _(no db_context)_ |
| `prompt_analytics_repository` | `PromptAnalyticsRepository` | `EyeBudgetDbContext` |

### Services (12)

| Parameter name | Type | Notes |
|----------------|------|-------|
| `ocr_service` | `OCRService` | External LLM call — always mock in tests |
| `preprocessing_service` | `PreprocessingService` | File I/O — mock in unit tests |
| `minio_service` | `MinioStorageService` | External S3 — use testcontainers MinIO in integration |
| `text_localization_service` | `TextLocalizationService` | PaddleOCR — always mock |
| `text_matching_service` | `TextMatchingService` | — |
| `vendors_service` | `VendorsService` | External LLM call — always mock |
| `products_service` | `ProductsService` | External LLM call — always mock |
| `categories_service` | `CategoriesService` | Calls `build()` — mock in unit tests |
| `bank_categorization_service` | `BankCategorizationService` | Calls `build()` — mock in unit tests |
| `bank_csv_parser` | `PekaoCsvParser` | Pure parser — no mocking needed |
| `budget_analysis_service` | `BudgetAnalysisService` | — |
| `budget_goals_service` | `BudgetGoalsService` | — |
| `budget_simulation_service` | `BudgetSimulationService` | — |
| `evaluation_service` | `EvaluationService` | — |
| `ground_truth_service` | `GroundTruthService` | — |

---

## Test Fixture Entities

### `AppFactory` (unit test helper)

A factory function (not a class) in `tests/unit/conftest.py` that returns an `App` with all dependencies pre-mocked via `MagicMock()`, with selective overrides.

```
AppFactory(
  overrides: dict[str, MagicMock]   # named deps to override
) → App
```

**Usage**: `app = make_app(receipts_scans_repository=custom_mock)`

### `IntegrationApp` (integration test fixture)

The real `App()` constructed in `tests/integration/conftest.py` after env vars are set to point at the testcontainers-managed PostgreSQL and MinIO instances.

**Lifecycle**: function-scoped — new `App()` per test, `app.dispose()` in teardown.

---

## State Transitions Relevant to Tests

### Receipt scan status lifecycle (tested in integration)

```
PENDING → PROCESSING → PROCESSED → TO_CONFIRM → DONE
                     ↘ FAILED
```

### Bank/cash link lifecycle

```
(unlinked) → auto-linked (on import or confirm)
           → manually linked (on user action)
           → unlinked (on user action)
```

---

## Constraints

- `App(ABC)` ABC base class is preserved unchanged (constitution §VI compatibility)
- `EyeBudgetDbContext` is **not** injected — env vars control it (simpler, no interface needed)
- `categories_service.build()` and `bank_categorization_service.build()` are called in `__init__` — when mocked, these calls are silently absorbed by `MagicMock()`
