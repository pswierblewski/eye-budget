# Celery Task Layer Coverage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add unit tests under `backend/tests/unit/tasks/` for all seven Celery task modules, using `patch`, `make_app()`, `Task.apply(..., throw=True)`, and Pusher assertions — matching `docs/superpowers/specs/2026-04-17-backend-coverage-celery-tasks-design.md`.

**Architecture:** New package `tests/unit/tasks/` with shared `conftest.py` (`TASK_ID`, helpers, autouse fixture forcing `celery_app.conf.result_backend = "cache+memory://"` during tests so `Task.apply()` does not require a Redis result backend). One test module per `src/tasks/*.py`. No changes to production task code. `bind=True` tasks receive a stable `task_id` via `apply(..., task_id=TASK_ID)` so Pusher payloads are predictable. Disposal is asserted via `app.eye_budget_db_context.dispose` (real `App.dispose` is not a `MagicMock`).

**Tech Stack:** Python 3.11, pytest, pytest-cov (existing `pytest.ini`), `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`)

---

## File Map

| File | Responsibility |
|------|----------------|
| `backend/tests/unit/tasks/__init__.py` | Package marker (empty) |
| `backend/tests/unit/tasks/conftest.py` | `TASK_ID`, `triggers_with_event()`, `assert_app_disposed()`, autouse Celery `cache+memory` result backend for `apply()` |
| `backend/tests/unit/tasks/test_advance_goal_progress.py` | `advance_goal_progress_task` |
| `backend/tests/unit/tasks/test_refresh_ai_recommendations.py` | `refresh_ai_recommendations_task` |
| `backend/tests/unit/tasks/test_retry_receipt.py` | `retry_receipt_task` |
| `backend/tests/unit/tasks/test_run_budget_simulation.py` | `run_budget_simulation_task` |
| `backend/tests/unit/tasks/test_process_receipts.py` | `process_receipts_task` |
| `backend/tests/unit/tasks/test_run_evaluation.py` | `run_evaluation_task` |
| `backend/tests/unit/tasks/test_categorize_bank_transactions.py` | `categorize_bank_transactions_task` |

---

## Task 1: Scaffold `tests/unit/tasks/` package

**Files:**
- Create: `backend/tests/unit/tasks/__init__.py`
- Create: `backend/tests/unit/tasks/conftest.py`

- [ ] **Step 1: Create empty `__init__.py`**

Create `backend/tests/unit/tasks/__init__.py` with no content (or a single docstring).

- [ ] **Step 2: Create `conftest.py`**

Create `backend/tests/unit/tasks/conftest.py`:

```python
"""Shared helpers for Celery task unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.celery_app import celery_app
from tests.unit.conftest import make_app

TASK_ID = "test-celery-task-id"


@pytest.fixture(autouse=True)
def _celery_memory_result_backend():
    """Task.apply() still records results; default redis backend may be unavailable in venv."""
    prev = celery_app.conf.result_backend
    celery_app.conf.result_backend = "cache+memory://"
    yield
    celery_app.conf.result_backend = prev


def triggers_with_event(mock_pusher: MagicMock, channel: str, event: str) -> list[tuple]:
    """Return list of (args, kwargs) for trigger calls matching channel + event name."""
    matches = []
    for call in mock_pusher.trigger.call_args_list:
        args, kwargs = call
        if len(args) >= 2 and args[0] == channel and args[1] == event:
            matches.append((args, kwargs))
    return matches


def assert_app_disposed(app) -> None:
    """App.dispose() is real code; eye_budget_db_context is always a MagicMock from make_app()."""
    app.eye_budget_db_context.dispose.assert_called_once()
```

**Note:** After each task test, assert disposal via **`assert_app_disposed(app)`** (not `app.dispose.assert_called_once()`).

- [ ] **Step 3: Run a quick import check**

Run:

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -c "from tests.unit.tasks.conftest import TASK_ID, make_app; print(TASK_ID)"
```

Expected: prints `test-celery-task-id` with exit code 0.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/tasks/__init__.py backend/tests/unit/tasks/conftest.py
git commit -m "test: scaffold unit/tasks package for Celery task tests"
```

---

## Task 2: `advance_goal_progress_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_advance_goal_progress.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_advance_goal_progress.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from src.tasks.advance_goal_progress import advance_goal_progress_task
from tests.unit.tasks.conftest import assert_app_disposed, make_app


@pytest.mark.unit
class TestAdvanceGoalProgressTask:
    def test_calls_repository_and_disposes(self):
        # Arrange
        app = make_app()
        app.budget_goals_repository.advance_monthly_progress_for_all_active_goals = MagicMock()

        with patch("src.tasks.advance_goal_progress.App", return_value=app):
            # Act
            advance_goal_progress_task.apply(args=[], kwargs={}, throw=True)

        # Assert
        app.budget_goals_repository.advance_monthly_progress_for_all_active_goals.assert_called_once()
        assert_app_disposed(app)

    def test_repository_error_propagates_and_disposes(self):
        # Arrange
        app = make_app()
        app.budget_goals_repository.advance_monthly_progress_for_all_active_goals.side_effect = RuntimeError(
            "db error"
        )

        with patch("src.tasks.advance_goal_progress.App", return_value=app):
            # Act / Assert
            with pytest.raises(RuntimeError, match="db error"):
                advance_goal_progress_task.apply(args=[], kwargs={}, throw=True)

        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_advance_goal_progress.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_advance_goal_progress.py
git commit -m "test: unit tests for advance_goal_progress Celery task"
```

---

## Task 3: `refresh_ai_recommendations_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_refresh_ai_recommendations.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_refresh_ai_recommendations.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from src.data import AIInsightItem, AIRecommendationsResponse
from src.tasks.refresh_ai_recommendations import refresh_ai_recommendations_task
from tests.unit.tasks.conftest import assert_app_disposed, triggers_with_event, make_app


@pytest.mark.unit
class TestRefreshAiRecommendationsTask:
    def test_happy_path_triggers_done_and_returns_payload(self):
        # Arrange
        app = make_app()
        app.budget_simulation_service.generate_ai_recommendations.return_value = AIRecommendationsResponse(
            insights=[AIInsightItem(title="t", body="b", amount_pln=None, insight_type="info")],
            generated_at="2024-01-01T00:00:00",
            data_through_date=None,
            months_of_data=3,
            has_sufficient_data=True,
        )
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.refresh_ai_recommendations.App", return_value=app),
            patch("src.tasks.refresh_ai_recommendations.PusherService", return_value=mock_pusher),
        ):
            # Act
            result = refresh_ai_recommendations_task.apply(args=[], kwargs={}, throw=True).result

        # Assert
        assert result == {"has_sufficient_data": True}
        done = triggers_with_event(mock_pusher, "budget-channel", "budget.recommendations.done")
        assert len(done) == 1
        payload = done[0][0][2]
        assert "generated_at" in payload
        assert_app_disposed(app)

    def test_service_error_propagates_and_disposes(self):
        # Arrange
        app = make_app()
        app.budget_simulation_service.generate_ai_recommendations.side_effect = RuntimeError("openai down")
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.refresh_ai_recommendations.App", return_value=app),
            patch("src.tasks.refresh_ai_recommendations.PusherService", return_value=mock_pusher),
        ):
            # Act / Assert
            with pytest.raises(RuntimeError, match="openai down"):
                refresh_ai_recommendations_task.apply(args=[], kwargs={}, throw=True)

        mock_pusher.trigger.assert_not_called()
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_refresh_ai_recommendations.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_refresh_ai_recommendations.py
git commit -m "test: unit tests for refresh_ai_recommendations Celery task"
```

---

## Task 4: `retry_receipt_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_retry_receipt.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_retry_receipt.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from src.tasks.retry_receipt import retry_receipt_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, triggers_with_event, make_app


@pytest.mark.unit
class TestRetryReceiptTask:
    def test_success_triggers_done(self):
        # Arrange
        app = make_app()
        app.retry_receipt = MagicMock(return_value=True)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.retry_receipt.App", return_value=app),
            patch("src.tasks.retry_receipt.PusherService", return_value=mock_pusher),
        ):
            # Act
            retry_receipt_task.apply(args=(7,), kwargs={}, task_id=TASK_ID, throw=True)

        # Assert
        done = triggers_with_event(mock_pusher, "receipts", "receipt.done")
        assert len(done) == 1
        assert done[0][0][2]["scan_id"] == 7
        assert done[0][0][2]["task_id"] == TASK_ID
        assert_app_disposed(app)

    def test_failure_triggers_error_with_fixed_message(self):
        # Arrange
        app = make_app()
        app.retry_receipt = MagicMock(return_value=False)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.retry_receipt.App", return_value=app),
            patch("src.tasks.retry_receipt.PusherService", return_value=mock_pusher),
        ):
            # Act
            retry_receipt_task.apply(args=(8,), kwargs={}, task_id=TASK_ID, throw=True)

        # Assert
        err = triggers_with_event(mock_pusher, "receipts", "receipt.error")
        assert len(err) == 1
        assert err[0][0][2]["error"] == "Scan not found or file missing"
        assert_app_disposed(app)

    def test_exception_triggers_error_and_reraises(self):
        # Arrange
        app = make_app()
        app.retry_receipt = MagicMock(side_effect=ValueError("missing file"))
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.retry_receipt.App", return_value=app),
            patch("src.tasks.retry_receipt.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(ValueError, match="missing file"):
                retry_receipt_task.apply(args=(9,), kwargs={}, task_id=TASK_ID, throw=True)

        err = triggers_with_event(mock_pusher, "receipts", "receipt.error")
        assert len(err) == 1
        assert "missing file" in err[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_retry_receipt.py -m unit -v --no-cov
```

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_retry_receipt.py
git commit -m "test: unit tests for retry_receipt Celery task"
```

---

## Task 5: `run_budget_simulation_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_run_budget_simulation.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_run_budget_simulation.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from src.data import (
    SimulationGoalImpact,
    SimulationMonthlyPoint,
    SimulationResultPayload,
    SimulationSuggestion,
)
from src.tasks.run_budget_simulation import run_budget_simulation_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, triggers_with_event, make_app


def _minimal_sim_row():
    return {
        "expense_amount": 100.0,
        "expense_type": "one_time",
        "expense_start_date": "2024-06-01",
    }


def _minimal_result_payload():
    return SimulationResultPayload(
        projection=[
            SimulationMonthlyPoint(month="2024-01", baseline_surplus_pln=1.0, simulated_surplus_pln=0.5)
        ],
        goal_impacts=[
            SimulationGoalImpact(
                goal_id=1,
                goal_name="g",
                baseline_completion_date=None,
                simulated_completion_date=None,
                delay_months=0,
            )
        ],
        ai_summary="s",
        ai_implications="i",
        ai_suggestions=[
            SimulationSuggestion(description="d", monthly_saving_pln=10.0, months_required=2)
        ],
    )


@pytest.mark.unit
class TestRunBudgetSimulationTask:
    def test_happy_path_updates_status_and_triggers_done(self):
        # Arrange
        app = make_app()
        app.budget_simulations_repository.get_simulation.return_value = _minimal_sim_row()
        app.budget_simulation_service.run_projection.return_value = _minimal_result_payload()
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.run_budget_simulation.App", return_value=app),
            patch("src.tasks.run_budget_simulation.PusherService", return_value=mock_pusher),
        ):
            # Act
            run_budget_simulation_task.apply(args=(42,), kwargs={}, task_id=TASK_ID, throw=True)

        # Assert
        assert app.budget_simulations_repository.update_simulation_status.call_count >= 2
        done = triggers_with_event(mock_pusher, "budget-channel", "budget.simulation.done")
        assert len(done) == 1
        assert done[0][0][2]["simulation_id"] == 42
        assert done[0][0][2]["status"] == "done"
        assert_app_disposed(app)

    def test_missing_simulation_triggers_failed(self):
        # Arrange
        app = make_app()
        app.budget_simulations_repository.get_simulation.return_value = None
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.run_budget_simulation.App", return_value=app),
            patch("src.tasks.run_budget_simulation.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(ValueError, match="not found"):
                run_budget_simulation_task.apply(args=(99,), kwargs={}, task_id=TASK_ID, throw=True)

        failed = triggers_with_event(mock_pusher, "budget-channel", "budget.simulation.failed")
        assert len(failed) == 1
        assert "not found" in failed[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_run_budget_simulation.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_run_budget_simulation.py
git commit -m "test: unit tests for run_budget_simulation Celery task"
```

---

## Task 6: `process_receipts_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_process_receipts.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_process_receipts.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.process_receipts import process_receipts_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, triggers_with_event, make_app


@pytest.mark.unit
class TestProcessReceiptsTask:
    def test_happy_path_triggers_done(self):
        # Arrange
        app = make_app()
        app._run_production_async = AsyncMock(return_value=None)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.process_receipts.App", return_value=app),
            patch("src.tasks.process_receipts.PusherService", return_value=mock_pusher),
        ):
            # Act
            process_receipts_task.apply(args=[], kwargs={}, task_id=TASK_ID, throw=True)

        # Assert
        done = triggers_with_event(mock_pusher, "receipts", "receipt.done")
        assert len(done) == 1
        assert done[0][0][2]["task_id"] == TASK_ID
        app._run_production_async.assert_awaited_once()
        assert_app_disposed(app)

    def test_pipeline_error_triggers_error_and_reraises(self):
        # Arrange
        app = make_app()
        app._run_production_async = AsyncMock(side_effect=RuntimeError("pipeline failed"))
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.process_receipts.App", return_value=app),
            patch("src.tasks.process_receipts.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(RuntimeError, match="pipeline failed"):
                process_receipts_task.apply(args=[], kwargs={}, task_id=TASK_ID, throw=True)

        err = triggers_with_event(mock_pusher, "receipts", "receipt.error")
        assert len(err) == 1
        assert "pipeline failed" in err[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_process_receipts.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_process_receipts.py
git commit -m "test: unit tests for process_receipts Celery task"
```

---

## Task 7: `run_evaluation_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_run_evaluation.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_run_evaluation.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.data import EvaluationRunSummary
from src.tasks.run_evaluation import run_evaluation_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, triggers_with_event, make_app


def _minimal_summary():
    return EvaluationRunSummary(
        run_id=1,
        model_used="gpt-test",
        total_files=0,
        successful=0,
        failed=0,
        success_rate=0.0,
        avg_processing_time_ms=0.0,
        avg_field_completeness=0.0,
        avg_consistency_rate=0.0,
        results=[],
    )


@pytest.mark.unit
class TestRunEvaluationTask:
    def test_happy_path_triggers_done_and_returns_dump(self):
        # Arrange
        app = make_app()
        summary = _minimal_summary()
        app.evaluation_service.run_evaluation_async = AsyncMock(return_value=summary)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.run_evaluation.App", return_value=app),
            patch("src.tasks.run_evaluation.PusherService", return_value=mock_pusher),
        ):
            # Act
            result = run_evaluation_task.apply(
                args=[], kwargs={"entry_ids": [10]}, task_id=TASK_ID, throw=True
            ).result

        # Assert
        assert result == summary.model_dump()
        done = triggers_with_event(mock_pusher, f"evaluation-{TASK_ID}", "evaluation.done")
        assert len(done) == 1
        assert done[0][0][2]["task_id"] == TASK_ID
        assert done[0][0][2]["summary"] is not None
        app.evaluation_service.run_evaluation_async.assert_awaited_once()
        assert_app_disposed(app)

    def test_error_triggers_evaluation_error_and_reraises(self):
        # Arrange
        app = make_app()
        app.evaluation_service.run_evaluation_async = AsyncMock(side_effect=RuntimeError("eval boom"))
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.run_evaluation.App", return_value=app),
            patch("src.tasks.run_evaluation.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(RuntimeError, match="eval boom"):
                run_evaluation_task.apply(args=[], kwargs={}, task_id=TASK_ID, throw=True)

        err = triggers_with_event(mock_pusher, f"evaluation-{TASK_ID}", "evaluation.error")
        assert len(err) == 1
        assert "eval boom" in err[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_run_evaluation.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_run_evaluation.py
git commit -m "test: unit tests for run_evaluation Celery task"
```

---

## Task 8: `categorize_bank_transactions_task`

**Files:**
- Create: `backend/tests/unit/tasks/test_categorize_bank_transactions.py`

- [ ] **Step 1: Add test module**

Create `backend/tests/unit/tasks/test_categorize_bank_transactions.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from src.tasks.categorize_bank_transactions import categorize_bank_transactions_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, triggers_with_event, make_app


@pytest.mark.unit
class TestCategorizeBankTransactionsTask:
    def test_happy_path_triggers_done_and_progress(self):
        # Arrange
        app = make_app()
        # No transaction row -> skips LLM but still emits progress per id
        app.bank_transactions_repository.get_by_id.return_value = None
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.categorize_bank_transactions.App", return_value=app),
            patch("src.tasks.categorize_bank_transactions.PusherService", return_value=mock_pusher),
        ):
            # Act
            categorize_bank_transactions_task.apply(
                args=([101],), kwargs={}, task_id=TASK_ID, throw=True
            )

        # Assert
        progress = triggers_with_event(mock_pusher, "bank-transactions", "categorization.progress")
        assert len(progress) >= 1
        assert progress[-1][0][2]["task_id"] == TASK_ID
        done = triggers_with_event(mock_pusher, "bank-transactions", "categorization.done")
        assert len(done) == 1
        assert done[0][0][2]["total"] == 1
        assert_app_disposed(app)

    def test_outer_error_triggers_categorization_error(self):
        # Arrange
        app = make_app()

        with (
            patch("src.tasks.categorize_bank_transactions.App", return_value=app),
            patch("src.tasks.categorize_bank_transactions.PusherService") as pusher_cls,
            patch(
                "src.tasks.categorize_bank_transactions.asyncio.run",
                side_effect=RuntimeError("cannot start loop"),
            ),
        ):
            mock_pusher = MagicMock()
            pusher_cls.return_value = mock_pusher

            with pytest.raises(RuntimeError, match="cannot start loop"):
                categorize_bank_transactions_task.apply(
                    args=([1],), kwargs={}, task_id=TASK_ID, throw=True
                )

        err = triggers_with_event(mock_pusher, "bank-transactions", "categorization.error")
        assert len(err) == 1
        assert "cannot start loop" in err[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 2: Run tests**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/test_categorize_bank_transactions.py -m unit -v --no-cov
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/tasks/test_categorize_bank_transactions.py
git commit -m "test: unit tests for categorize_bank_transactions Celery task"
```

---

## Task 9: Full unit suite + coverage

**Files:**
- None (verification only)

- [ ] **Step 1: Run all new tests without coverage noise**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/ -m unit -v --no-cov
```

Expected: 16 passed (2+2+3+2+2+2+2+2).

- [ ] **Step 2: Run with task coverage**

```bash
cd /home/pawel/eye-budget/backend && ../venv/bin/python -m pytest tests/unit/tasks/ -m unit --cov=src/tasks --cov-report=term-missing -q
```

Expected: all pass; `src/tasks/` lines show high coverage (exact % depends on branches like `print` in `advance_goal_progress` / `categorize`).

- [ ] **Step 3: Optional final commit**

Only if you fixed imports or typos during verification:

```bash
git add -A backend/tests/unit/tasks/
git commit -m "test: fix Celery task unit tests after verification"
```

---

## Plan self-review

1. **Spec coverage:** Package layout, `apply` + `task_id`, `patch` targets, Pusher assertions, all seven tasks with happy + error rows from spec table — each maps to Tasks 1–8/9. `evaluation.progress` / `receipt.progress` not asserted explicitly (spec minimum was done + error + dispose); add later if you want stricter coverage.
2. **Placeholders:** None intended; all file paths and code blocks are complete.
3. **Consistency:** `TASK_ID` used wherever `bind=True` and Pusher includes `task_id`; `make_app` + `assert_app_disposed(app)` throughout. **`App.retry_receipt`** is a real method — replace with **`MagicMock`** on the instance for success/failure tests, not `.return_value` on the bound method.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-17-backend-coverage-celery-tasks.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — run Tasks 1–9 in this session with checkpoints between commits.

Which approach do you want?
