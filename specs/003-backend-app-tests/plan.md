# Implementation Plan: Backend App.py Testability & Test Coverage

**Branch**: `003-backend-app-tests` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-backend-app-tests/spec.md`

---

## Summary

Refactor `backend/src/app.py` to support dependency injection (all repositories and services become optional constructor keyword arguments), then add a layered test suite: unit tests (all deps mocked, no Docker) targeting ≥80% coverage with a hard gate, plus integration tests (real PostgreSQL + MinIO via testcontainers-python, LLM/OCR mocked) that exercise the full `_process_single_file` pipeline.

---

## Technical Context

**Language/Version**: Python 3.11.7 (venv at project root `venv/`)
**Primary Dependencies**: FastAPI, psycopg2-binary, pydantic v2, yoyo-migrations 9.0.0, minio client
**Test Dependencies (new)**: pytest ≥8.0, pytest-mock ≥3.14, pytest-cov ≥5.0, testcontainers[postgres,minio] ≥4.13
**Storage**: PostgreSQL (psycopg2-binary), MinIO (S3-compatible)
**Testing**: pytest + pytest-mock + pytest-cov + testcontainers-python
**Target Platform**: Linux (WSL2 / Docker)
**Project Type**: Backend service (FastAPI) in a Next.js + FastAPI monorepo
**Performance Goals**: Unit test suite completes in <10 seconds; integration test session starts in <60 seconds (after first Docker pull)
**Constraints**: Tests run via `venv/bin/pytest` from project root; Docker must be available for integration tests; no real LLM/OCR calls in any test

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### Principle I — Code Quality & Separation of Concerns

| Gate | Status | Note |
|------|--------|------|
| Python code stays in `backend/` | ✅ Pass | Test files go in `backend/tests/` |
| No hardcoded credentials/hostnames | ✅ Pass | testcontainers dynamically assigns ports; env vars used for integration tests |
| Functions/classes single-responsibility | ✅ Pass | DI refactor doesn't add logic — just optional params |

### Principle II — Testing Standards

| Gate | Status | Note |
|------|--------|------|
| New code accompanied by tests | ✅ Pass | This feature IS the test coverage work |
| Tests before/alongside implementation | ✅ Pass | Refactor and tests land in same branch |
| All tests pass before merge | ✅ Pass | 80% hard gate enforced |

### Principle VI — Backend Conventions

| Gate | Status | Note |
|------|--------|------|
| `App` instantiated per request, disposed in `finally` | ✅ Pass | Refactor preserves this entirely |
| `App.__init__` creates context, repos, services | ✅ Pass | Default path unchanged; injection is additive |
| Services receive deps via constructor, no globals | ✅ Pass | DI refactor reinforces this |
| `App.dispose()` always called | ✅ Pass | Integration test fixtures call `app.dispose()` in teardown |

**Verdict**: No violations. No complexity justification required.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-backend-app-tests/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code Changes

```text
backend/
├── src/
│   └── app.py                      ← MODIFIED: DI constructor params
├── tests/                          ← NEW
│   ├── conftest.py                 ← pytest markers, pytest.ini options
│   ├── unit/
│   │   ├── conftest.py             ← make_app() factory
│   │   ├── test_receipts.py        ← confirm_receipt, reopen, delete, retry
│   │   ├── test_bank_cash.py       ← bank/cash CRUD, tag propagation
│   │   ├── test_budget.py          ← budget delegation
│   │   └── test_autolink.py        ← _auto_link_* methods
│   └── integration/
│       ├── conftest.py             ← PostgresContainer + MinioContainer
│       └── test_pipeline.py        ← _process_single_file end-to-end
├── .coveragerc                     ← NEW: coverage config
└── requirements-test.txt           ← NEW: test-only deps
```

**Structure Decision**: `backend/tests/` as sibling to `backend/src/` (clarification Q4). Split into `unit/` and `integration/` subdirectories so unit tests never transitively import Docker fixtures.

---

## Phase 0: Research Summary

See [research.md](research.md) for full details. Key decisions:

| Topic | Decision |
|-------|----------|
| Migration tool | yoyo-migrations (NOT Alembic) — `get_backend()` + `read_migrations()` |
| Container library | `testcontainers[postgres,minio]>=4.13` |
| DI approach | Optional kwargs defaulting to `None`; `EyeBudgetDbContext` NOT injected (env vars instead) |
| Coverage gate | `pytest --cov-fail-under=80`, configured via `.coveragerc` |
| Container lifecycle | session-scoped start; function-scoped table truncation for test isolation |

---

## Phase 1: Design

### Step 1 — Refactor `App.__init__` (DI)

The constructor gains ~31 optional keyword parameters: one for `eye_budget_db_context` and one per repository and service. The auto-construction path (default `None`) is preserved verbatim. Order of operations inside `__init__` is unchanged.

**`EyeBudgetDbContext` must be injectable.** Without it, even when all repos are mocked, `App.__init__` line 103 still runs `EyeBudgetDbContext()` unconditionally, which calls `psycopg2.connect()`. The exception is swallowed, but every unit test would emit noisy failure output and leave `self.conn = None`. Injecting a `MagicMock()` for the context prevents this entirely.

**Pattern for db_context** (first, before any repo):
```python
def __init__(self, eye_budget_db_context=None, receipts_scans_repository=None, ...):
    self.eye_budget_db_context = eye_budget_db_context or EyeBudgetDbContext()
```

**Pattern** (applied uniformly to all ~30 repo/service deps):
```python
self.receipts_scans_repository = (
    receipts_scans_repository
    or ReceiptsScansRepository(self.eye_budget_db_context)
)
```

Services that call `build()` (`categories_service`, `bank_categorization_service`):
```python
self.categories_service = categories_service or CategoriesService(self.eye_budget_db_context)
if categories_service is None:         # only build when auto-constructed
    self.categories_service.build()
```

### Step 2 — Test Infrastructure

**`backend/requirements-test.txt`**:
```
pytest>=8.0
pytest-mock>=3.14
pytest-cov>=5.0
testcontainers[postgres,minio]>=4.13
```

**`backend/.coveragerc`**:
```ini
[run]
source = src
omit =
    src/__init__.py
    */tests/*
    */migrations/*

[report]
fail_under = 80
precision = 1
exclude_lines =
    def dispose
    def __init__
    pragma: no cover
    if __name__ == .__main__.
```

**`backend/tests/conftest.py`** (root — markers only):
```python
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: pure unit test, no Docker")
    config.addinivalue_line("markers", "integration: requires Docker")
```

### Step 3 — Unit Test Fixtures (`tests/unit/conftest.py`)

`make_app()` factory — builds an `App` with all deps as `MagicMock()`, with selective overrides:

```python
from unittest.mock import MagicMock
from src.app import App

ALL_PARAMS = [
    # db context — must be mocked to prevent psycopg2.connect() during unit tests
    "eye_budget_db_context",
    # repositories
    "receipts_scans_repository", "transactions_repository",
    "bank_transactions_repository", "bank_receipt_links_repository",
    "cash_transactions_repository", "cash_receipt_links_repository",
    "unified_transactions_repository", "budget_analysis_repository",
    "budget_goals_repository", "budget_simulations_repository",
    "categories_repository", "vendors_repository", "products_repository",
    "evaluations_repository", "ground_truth_repository",
    "files_repository", "prompt_analytics_repository",
    # services
    "ocr_service", "preprocessing_service", "minio_service",
    "text_localization_service", "text_matching_service",
    "vendors_service", "products_service", "categories_service",
    "bank_categorization_service", "bank_csv_parser",
    "budget_analysis_service", "budget_goals_service",
    "budget_simulation_service", "evaluation_service", "ground_truth_service",
]

def make_app(**overrides):
    defaults = {p: MagicMock() for p in ALL_PARAMS}
    defaults.update(overrides)
    return App(**defaults)
```

### Step 4 — Integration Test Fixtures (`tests/integration/conftest.py`)

Session-scoped containers + yoyo migration application + per-test env var injection:

```python
import os, pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer
from yoyo import get_backend, read_migrations

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer() as minio:
        yield minio

@pytest.fixture(scope="session")
def migrated_db(postgres_container):
    url = postgres_container.get_connection_url()
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    backend = get_backend(url)
    migrations_path = os.path.join(os.path.dirname(__file__), "../../migrations")
    migrations = read_migrations(migrations_path)
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    return postgres_container

@pytest.fixture
def integration_app(migrated_db, minio_container):
    pg = migrated_db
    os.environ.update({
        "POSTGRESQL_HOST": pg.get_container_host_ip(),
        "POSTGRESQL_PORT": str(pg.get_exposed_port(5432)),
        "POSTGRESQL_DB":   pg.dbname,
        "POSTGRESQL_USER": pg.username,
        "POSTGRESQL_PASSWORD": pg.password,
        "MINIO_ENDPOINT":  f"{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        "MINIO_ACCESS_KEY": minio_container.access_key,
        "MINIO_SECRET_KEY": minio_container.secret_key,
    })
    from src.app import App
    app = App()
    yield app
    app.dispose()
```

### Step 5 — Unit Test Coverage Plan

| File | Methods covered | Key assertions |
|------|----------------|----------------|
| `test_receipts.py` | `confirm_receipt`, `reopen_receipt`, `delete_receipt`, `retry_receipt`, `get_receipt_by_id` | Correct repo methods called with correct args; override application; analytics non-fatal; auto-link triggered |
| `test_bank_cash.py` | `import_bank_csv`, `categorize_bank_transactions`, `link_bank_to_receipt`, `unlink_bank_transaction`, `create_cash_transaction`, `update_receipt_tags`, `update_bank_transaction_tags`, `update_cash_transaction_tags` | Tag merge logic; link creation; category skip when linked |
| `test_budget.py` | `get_monthly_breakdown`, `check_affordability`, `get_goals`, `create_goal`, `update_goal`, `delete_goal`, `create_simulation`, `get_simulation`, `get_ai_recommendations` | Correct delegation with correct args |
| `test_autolink.py` | `_auto_link_receipt`, `_auto_link_bank_transactions`, `_auto_link_cash_transaction` | Bank priority over cash; multi-candidate skip; exception swallowing; tag merge |

### Step 6 — Integration Test Coverage Plan

| File | Scenario | What is real |
|------|----------|-------------|
| `test_pipeline.py` | `_process_single_file` success path | PostgreSQL, MinIO; OCR mocked to return fixture JSON |
| `test_pipeline.py` | `_process_single_file` OCR failure | PostgreSQL, MinIO; OCR raises exception |
| `test_pipeline.py` | `confirm_receipt` full round-trip | PostgreSQL, MinIO; full DB write verified |

---

## Complexity Tracking

No constitution violations. No complexity justification needed.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `EyeBudgetDbContext(ABC)` constructor connects immediately — unit tests that don't inject all repos may trigger a real DB connection attempt | Ensure all repos are injected via `make_app()` factory; `EyeBudgetDbContext` is only constructed when no dep injection is provided |
| testcontainers MinIO API may differ from production MinIO env var names | Document mapping in integration conftest; keep MinIO env var names consistent with existing `.env.example` |
| `categories_service.build()` side-effect in `__init__` — mocked service must not fail on `build()` call | `MagicMock()` absorbs `build()` silently — no action needed |
| yoyo `get_backend()` psycopg2 URL format may need prefix stripping | Handled in research: strip `postgresql+psycopg2://` prefix |
