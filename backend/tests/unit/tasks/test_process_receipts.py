import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.process_receipts import process_receipts_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event


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
