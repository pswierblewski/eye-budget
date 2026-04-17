import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.data import EvaluationRunSummary
from src.tasks.run_evaluation import run_evaluation_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event


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
