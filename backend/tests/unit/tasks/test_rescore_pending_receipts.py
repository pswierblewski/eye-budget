import pytest
from unittest.mock import MagicMock, patch

from src.data import RescoreReport
from src.tasks.rescore_pending_receipts import rescore_pending_receipts_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event

REPORT = RescoreReport(dry_run=True, total=2, eligible=1, confirmed=0, skipped=0, errors=0, top_reasons=[])


@pytest.mark.unit
class TestRescorePendingReceiptsTask:
    def test_success_emits_done_with_report_and_returns_it(self):
        # Arrange
        app = make_app()

        def fake_rescore(dry_run, on_progress=None):
            on_progress(index=1, total=2)
            return REPORT

        app.rescore_pending_receipts = MagicMock(side_effect=fake_rescore)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.rescore_pending_receipts.App", return_value=app),
            patch("src.tasks.rescore_pending_receipts.PusherService", return_value=mock_pusher),
        ):
            # Act
            result = rescore_pending_receipts_task.apply(kwargs={"dry_run": True}, task_id=TASK_ID, throw=True)

        # Assert
        assert result.get() == REPORT.model_dump()
        assert app.rescore_pending_receipts.call_args.kwargs["dry_run"] is True
        progress = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_progress")
        assert progress[0][0][2] == {"task_id": TASK_ID, "index": 1, "total": 2}
        done = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_done")
        assert done[0][0][2]["report"] == REPORT.model_dump()
        assert_app_disposed(app)

    def test_exception_emits_error_and_reraises(self):
        # Arrange
        app = make_app()
        app.rescore_pending_receipts = MagicMock(side_effect=RuntimeError("db down"))
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.rescore_pending_receipts.App", return_value=app),
            patch("src.tasks.rescore_pending_receipts.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(RuntimeError):
                rescore_pending_receipts_task.apply(kwargs={"dry_run": False}, task_id=TASK_ID, throw=True)

        err = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_error")
        assert "db down" in err[0][0][2]["error"]
        assert_app_disposed(app)
