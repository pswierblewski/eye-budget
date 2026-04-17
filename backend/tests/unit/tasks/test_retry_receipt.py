import pytest
from unittest.mock import MagicMock, patch

from src.tasks.retry_receipt import retry_receipt_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event


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
