# Research: Backend App.py Testability & Test Coverage

**Branch**: `003-backend-app-tests` | **Date**: 2026-03-18

---

## Decision 1: Test Package Selection

**Decision**: `pytest` + `pytest-mock` + `pytest-cov` + `testcontainers[postgres,minio]`

**Rationale**: pytest is the de-facto Python test runner, pytest-mock wraps `unittest.mock` ergonomically, pytest-cov enforces coverage gates, and testcontainers-python manages Docker containers automatically without shell scripts.

**Alternatives considered**:
- `unittest` stdlib only — rejected: no fixture scoping, verbose, poor DI/mock ergonomics
- `factory_boy` for fixtures — deferred: overkill for first test suite iteration

**Concrete package names**:
```
pytest>=8.0
pytest-mock>=3.14
pytest-cov>=5.0
testcontainers[postgres,minio]>=4.13
```

---

## Decision 2: `testcontainers-python` Import Paths

**Decision**: Use `testcontainers.postgres.PostgresContainer` and `testcontainers.minio.MinioContainer`

```python
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer
```

**Container startup (session-scoped)**:
```python
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer() as minio:
        yield minio
```

---

## Decision 3: yoyo Migrations — Programmatic API

**Decision**: Use `yoyo.get_backend()` + `read_migrations()` to apply migrations against the test container's DB.

**Project uses**: `yoyo-migrations==9.0.0` (NOT Alembic — important correction from initial spec).

```python
from yoyo import get_backend, read_migrations

@pytest.fixture(scope="session")
def migrated_db_url(postgres_container):
    url = postgres_container.get_connection_url()
    # yoyo expects postgresql:// not postgresql+psycopg2://
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    backend = get_backend(url)
    migrations = read_migrations("migrations")      # path relative to where pytest runs
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    return url
```

**Key yoyo API**:
- `get_backend(uri)` — connects yoyo to a DB
- `read_migrations(path)` — reads `.sql` files from the migration directory
- `backend.to_apply(migrations)` — returns unapplied subset
- `backend.apply_migrations(...)` — applies them
- `backend.lock()` — advisory lock (important for parallel CI)

---

## Decision 4: Dependency Injection Refactor Strategy

**Decision**: Make all repositories and services optional constructor keyword arguments in `App.__init__`. Default `None` → auto-construct (backwards compatible).

**`EyeBudgetDbContext` must also be injectable**:
`App.__init__` line 103 runs `self.eye_budget_db_context = EyeBudgetDbContext()` unconditionally before any repository is constructed. `EyeBudgetDbContext.__init__` immediately calls `psycopg2.connect()`. Even though the exception is caught and swallowed, every unit test would print `"Failed to connect to database: ..."` to stdout and leave `conn = None`. Injecting a `MagicMock()` prevents this entirely.

For integration tests, env vars are set to match the container before `App()` is called — no injection needed there.

**Minimal refactor pattern**:
```python
class App(ABC):
    def __init__(self,
                 receipts_scans_repository=None,
                 transactions_repository=None,
                 # ... all other repos/services ...
                 ):
        self.eye_budget_db_context = EyeBudgetDbContext()
        self.receipts_scans_repository = (
            receipts_scans_repository
            or ReceiptsScansRepository(self.eye_budget_db_context)
        )
        # ... etc
```

**For unit tests** — inject `MagicMock()` for `eye_budget_db_context` AND all repos/services:
```python
def make_app(**overrides):
    """Factory that returns App with all deps mocked — including db_context."""
    defaults = {name: MagicMock() for name in ["eye_budget_db_context"] + ALL_REPO_NAMES + ALL_SERVICE_NAMES}
    defaults.update(overrides)
    return App(**defaults)
```

**For integration tests** — set env vars, let `App()` construct normally:
```python
os.environ["POSTGRESQL_HOST"] = container.get_container_host_ip()
os.environ["POSTGRESQL_PORT"] = str(container.get_exposed_port(5432))
# ... etc
app = App()   # builds normally against test container
```

---

## Decision 5: Coverage Configuration

**Decision**: `pytest-cov` hard-gate at 80%, unit tests only, `__init__` and `dispose` excluded.

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
    if __name__ == .__main__.
```

**Run command** (from `backend/` directory):
```bash
../../venv/bin/pytest tests/unit/ --cov=src --cov-config=.coveragerc --cov-fail-under=80 --cov-report=term-missing
```

---

## Decision 6: conftest.py Layout

**Decision**: Two-level conftest structure — unit tests have zero Docker dependency.

```
backend/tests/
├── conftest.py               # Shared: pytest.ini markers, common helpers
├── unit/
│   ├── conftest.py           # MagicMock factories, no Docker
│   ├── test_receipts.py
│   ├── test_bank_cash.py
│   ├── test_budget.py
│   └── test_autolink.py
└── integration/
    ├── conftest.py           # PostgresContainer + MinioContainer (session-scoped)
    └── test_pipeline.py
```

**Root conftest markers**:
```python
# backend/tests/conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: pure unit test, no Docker")
    config.addinivalue_line("markers", "integration: requires Docker")
```

---

## Resolved Unknowns

| Item | Resolution |
|------|------------|
| Migration tool | yoyo-migrations (not Alembic) — `get_backend()` + `read_migrations()` |
| Container library | `testcontainers[postgres,minio]>=4.13` |
| DB env var injection | Set `POSTGRESQL_HOST/PORT/DB/USER/PASSWORD` before `App()` in integration fixtures |
| `App(ABC)` ABC usage | Keep ABC — it's a pattern from the codebase even though no abstract methods; refactor doesn't touch base class |
| MinIO test bucket | Create via `minio_client.make_bucket("test-bucket")` in fixture |
