import pytest
from unittest.mock import MagicMock, patch

from src.data import (
    SimulationGoalImpact,
    SimulationMonthlyPoint,
    SimulationResultPayload,
    SimulationSuggestion,
)
from src.tasks.run_budget_simulation import run_budget_simulation_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event


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
