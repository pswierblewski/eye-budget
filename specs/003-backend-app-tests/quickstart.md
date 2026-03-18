# Quickstart: Running App.py Tests

**Branch**: `003-backend-app-tests`

---

## Prerequisites

- Python 3.11+ venv at `venv/` (project root)
- Docker (for integration tests only)
- `.env` with PostgreSQL credentials (for integration tests only)

---

## Install test dependencies

```bash
cd backend
../venv/bin/pip install pytest>=8.0 pytest-mock>=3.14 pytest-cov>=5.0 "testcontainers[postgres,minio]>=4.13"
```

Or after `requirements-test.txt` is added:

```bash
cd backend
../venv/bin/pip install -r requirements-test.txt
```

---

## Run unit tests (no Docker required)

```bash
cd backend
../venv/bin/pytest tests/unit/ -v
```

With coverage enforcement (fails if below 80%):

```bash
cd backend
../venv/bin/pytest tests/unit/ -v \
  --cov=src \
  --cov-config=.coveragerc \
  --cov-fail-under=80 \
  --cov-report=term-missing
```

---

## Run integration tests (Docker required)

```bash
cd backend
../venv/bin/pytest tests/integration/ -v
```

> Containers start automatically. First run downloads Docker images (~30s). Subsequent runs are fast.

---

## Run all tests

```bash
cd backend
../venv/bin/pytest tests/ -v \
  --cov=src \
  --cov-config=.coveragerc \
  --cov-fail-under=80 \
  --cov-report=term-missing
```

---

## Run a single test file

```bash
cd backend
../venv/bin/pytest tests/unit/test_receipts.py -v
```

## Run a single test by name

```bash
cd backend
../venv/bin/pytest tests/unit/test_receipts.py::test_confirm_receipt_applies_overrides -v
```

---

## Directory layout after implementation

```
backend/
├── tests/
│   ├── conftest.py              # markers, shared helpers
│   ├── unit/
│   │   ├── conftest.py          # make_app() factory, MagicMock helpers
│   │   ├── test_receipts.py     # confirm_receipt, reopen, delete
│   │   ├── test_bank_cash.py    # bank/cash CRUD, tag propagation
│   │   ├── test_budget.py       # budget delegation methods
│   │   └── test_autolink.py     # _auto_link_* methods
│   └── integration/
│       ├── conftest.py          # PostgresContainer + MinioContainer fixtures
│       └── test_pipeline.py     # _process_single_file end-to-end
├── .coveragerc                  # coverage config (fail_under=80)
└── requirements-test.txt        # test-only pip deps
```
