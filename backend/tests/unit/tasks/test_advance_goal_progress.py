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
