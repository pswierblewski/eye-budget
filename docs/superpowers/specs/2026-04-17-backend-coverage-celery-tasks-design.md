# Design: Backend Code Coverage — Celery Task Unit Tests

**Date:** 2026-04-17  
**Scope:** `backend/src/tasks/*.py` (seven Celery task modules)  
**Goal:** Add fast unit tests for task orchestration (`App` lifecycle, Pusher events, error paths) without broker, Redis, or real DB — consistent with existing `docs/superpowers` coverage work (pytest, `MagicMock` / `AsyncMock`, `patch`, `@pytest.mark.unit`, AAA comments).

---

## 1. Current State

| Module | `bind=True` | Pusher |
|--------|-------------|--------|
| `process_receipts.py` | yes | `receipt.progress`, `receipt.done`, `receipt.error` |
| `run_evaluation.py` | yes | `evaluation.progress`, `evaluation.done`, `evaluation.error` |
| `categorize_bank_transactions.py` | yes | `categorization.progress`, `categorization.done`, `categorization.error` |
| `retry_receipt.py` | yes | `receipt.done`, `receipt.error` |
| `run_budget_simulation.py` | yes | `budget.simulation.done`, `budget.simulation.failed` |
| `refresh_ai_recommendations.py` | no | `budget.recommendations.done` |
| `advance_goal_progress.py` | no | none (repository + `print` only) |

All tasks that construct `App()` follow **try / except / finally: `dispose()`** (same pattern as HTTP handlers in `main.py`). Six modules instantiate `PusherService()` and call `trigger`.

**Explicitly deferred** in earlier specs: `src/tasks/` needed a different mocking strategy than repositories/services alone; this design addresses that.

---

## 2. Test Strategy

### Layer

- **Unit tests only** — no Celery broker, no global `task_always_eager` setting required for coverage goals, no PostgreSQL/MinIO.
- **`@pytest.mark.unit`** on every test; **AAA** (`# Arrange`, `# Act`, `# Assert`).

### Layout (decision: package under `tests/unit/tasks/`)

- **`backend/tests/unit/tasks/__init__.py`** — marks the directory as a package (empty or minimal).
- **`backend/tests/unit/tasks/conftest.py`** — shared fixtures/helpers, e.g.:
  - constant **`TASK_ID`** (or fixture) passed to **`apply(..., task_id=TASK_ID)`** for `bind=True` tasks so Pusher payloads stay predictable,
  - optional helper to **`assert_pusher_trigger`** (channel, event name, partial payload checks),
  - thin import of **`make_app`** from `tests/unit/conftest.py` if that reduces boilerplate.
- **One test module per task file**, mirroring `src/tasks/`:
  - `test_process_receipts.py`
  - `test_run_evaluation.py`
  - `test_categorize_bank_transactions.py`
  - `test_retry_receipt.py`
  - `test_run_budget_simulation.py`
  - `test_refresh_ai_recommendations.py`
  - `test_advance_goal_progress.py`

This matches the **repository** convention (one module → one focused test file) while keeping Celery-specific DRY in **`tasks/conftest.py`**.

### Mocking rules (aligned with superpowers service/repo specs)

- **Patch where the symbol is looked up** — always under the task module, e.g. `patch("src.tasks.process_receipts.App")`, `patch("src.tasks.process_receipts.PusherService")`.
- **`App`:** `return_value=make_app(...)` from `tests/unit/conftest.py`; configure specific mocks on the returned instance as needed per test. Assert **`dispose`** on the same instance the task created (the mock returned by patched `App`).
- **`PusherService`:** `return_value=MagicMock()`; assert **`trigger`** calls (channel, event name, important payload keys; avoid brittle full dict equality when values include timestamps or large `model_dump()` unless stable).
- **Invoking the task:** the object exported from the module is a Celery **`Task`**, not a plain Python function. Use **`task.apply(args=[...], kwargs={...}, task_id=<stable id>, throw=True)`** for **`bind=True`** tasks — this runs the body **in-process** (no broker) and sets **`self.request.id`** correctly. Tasks **without** `bind=True` use **`apply(args=[], kwargs={}, throw=True)`** (no `task_id` required unless useful for logging). Do not assume `task(mock_self, ...)` works on a `Task` instance.
- **Async:** tasks using `asyncio.run(...)` — mock async dependencies with **`AsyncMock`** so the event loop completes deterministically (same spirit as service tests).

### No production refactors for DI

Do not add optional `app_factory` / `pusher_factory` parameters to task signatures for this phase; rely on **`patch`** like cross-cutting `patch("os.path.exists", ...)` in service tests.

---

## 3. Scenarios (minimum per task)

| Task | Happy path | Error / branch |
|------|------------|----------------|
| `process_receipts` | pipeline completes → `receipt.done` | exception → `receipt.error`, re-raise, `dispose` |
| `run_evaluation` | summary returned → `evaluation.done` (+ return value) | exception → `evaluation.error` |
| `categorize_bank_transactions` | processing completes → `categorization.done`; progress fired (e.g. one id, mocked async path) | exception in outer try → `categorization.error` |
| `retry_receipt` | `retry_receipt` True → `receipt.done`; False → `receipt.error` with fixed message | exception → `receipt.error` with `str(exc)` |
| `run_budget_simulation` | sim exists → status updates + `budget.simulation.done` | missing sim or failure → `failed` status + `budget.simulation.failed` |
| `refresh_ai_recommendations` | service returns → `budget.recommendations.done` + return dict | exception: no Pusher error event in code — assert re-raise and `dispose` |
| `advance_goal_progress` | `advance_monthly_progress_for_all_active_goals` called | exception → re-raise, `dispose` |

---

## 4. Out of Scope

- `celery_app` configuration, beat schedule, Redis integration
- End-to-end Pusher/Soketi
- `main.py` / FastAPI routes
- Changing production task signatures for testability

---

## 5. Verification

After implementation:

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/tasks/ -m unit -q
cd backend && ../venv/bin/python -m pytest tests/unit/tasks/ -m unit --cov=src/tasks --cov-report=term-missing
```

Coverage is informational unless the project later reintroduces a `fail_under` gate for `src/tasks/` specifically.

---

## 6. Next Step

After this spec is reviewed and approved, use the **writing-plans** skill to produce an implementation plan (file list, patch examples, ordering of test modules).
