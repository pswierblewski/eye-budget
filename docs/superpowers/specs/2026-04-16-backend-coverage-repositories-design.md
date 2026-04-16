# Design: Backend Code Coverage — Repository Unit Tests

**Date:** 2026-04-16
**Scope:** Backend (`src/`)
**Goal:** Expand coverage measurement to all of `src/` and write unit tests for uncovered repositories

---

## 1. Config Change

**File:** `backend/pytest.ini`

```ini
# Before
addopts = --cov=src/services --cov-report=term-missing --cov-fail-under=80

# After
addopts = --cov=src --cov-report=term-missing
```

Two effects:
- Coverage scope expands from `src/services/` to the entire `src/`
- Threshold removed — no quality gate (coverage is built up incrementally)

---

## 2. Repository Tests — Strategy

### Already covered
- `bank_transaction_splits.py` → `test_bank_transaction_splits_repository.py`
- `categories.py` → `test_categories_repository.py`
- `bank_transactions.py` → `test_bank_transactions_repository_splits.py` (partial — only split interaction)

### To add — 15 files
`transactions`, `cash_transactions`, `unified_transactions`, `bank_receipt_links`, `cash_receipt_links`, `receipts_scans`, `products`, `vendors`, `evaluations`, `files`, `ground_truth`, `budget_goals`, `budget_simulations`, `budget_analysis`, `prompt_analytics`

### Mocking pattern (consistent with existing tests)

```python
from unittest.mock import MagicMock
from src.repositories.some_repo import SomeRepository

def make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = SomeRepository.__new__(SomeRepository)
    repo.conn = conn
    return repo, cursor
```

Special case — `TransactionsRepository` is an ABC:
```python
from src.repositories.transactions import TransactionsRepository

class ConcreteTransactions(TransactionsRepository):
    pass

def make_repo():
    conn = MagicMock()
    # ... same pattern
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = conn
    return repo, cursor
```

### Test scenarios per method (minimum 3)

1. **Happy path** — returns correct data, `conn.commit()` called
2. **No-conn guard** — `repo.conn = None`, method returns `None` / `False` / `[]`
3. **DB error** — `cursor.execute.side_effect = Exception(...)`, `conn.rollback()` called

### Test file naming

`tests/unit/test_<module_name>_repository.py` — one file per repository module.

### Code style

- `@pytest.mark.unit` on every test
- AAA comment structure: `# Arrange`, `# Act`, `# Assert`
- Assert SQL keywords where meaningful (e.g. `assert any("INSERT" in s for s in executed_sqls)`)

---

## 3. Priority Order

| Priority | Files | Rationale |
|----------|-------|-----------|
| 1 | `products`, `vendors`, `files`, `prompt_analytics` | Few methods, simple CRUD |
| 2 | `receipts_scans`, `bank_receipt_links`, `cash_receipt_links`, `cash_transactions` | Medium complexity, same pattern |
| 3 | `budget_goals`, `budget_simulations`, `budget_analysis` | More methods, JOINs |
| 4 | `transactions` (ABC), `unified_transactions`, `evaluations`, `ground_truth` | Highest complexity |

Estimated output: ~15 new test files, ~120–180 new tests.

---

## 4. Expected Coverage Outcome

| Before | After |
|--------|-------|
| `src/services/` only: **80.96%** | All `src/`: estimated **55–65%** |

Remaining gaps (out of scope — separate sessions):
- `src/tasks/` — Celery tasks require a different mocking strategy
- `src/app.py`, `src/main.py` — FastAPI routes, better suited for integration tests
- Weak services: `evaluation.py` (62.6%), `bank_categorization.py` (61.9%), `ground_truth.py` (64.3%)
- `test_coverage_boost.py` — rewrite as meaningful tests (separate session)

---

## 5. Out of Scope

- `src/tasks/` (Celery tasks)
- `src/app.py`, `src/main.py` (FastAPI routes)
- Service coverage improvements
- Rewriting `test_coverage_boost.py`
