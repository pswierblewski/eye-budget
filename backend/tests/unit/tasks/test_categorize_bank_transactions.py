import pytest
from unittest.mock import MagicMock, patch

from src.tasks.categorize_bank_transactions import (
    categorize_bank_transactions_task,
    emit_categorization_transaction_updated,
)
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event


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

        def _asyncio_run_raises(coro):
            coro.close()
            raise RuntimeError("cannot start loop")

        with (
            patch("src.tasks.categorize_bank_transactions.App", return_value=app),
            patch("src.tasks.categorize_bank_transactions.PusherService") as pusher_cls,
            patch(
                "src.tasks.categorize_bank_transactions.asyncio.run",
                side_effect=_asyncio_run_raises,
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


@pytest.mark.unit
class TestEmitCategorizationTransactionUpdated:
    def test_emits_top_candidate_from_candidates_list(self):
        mock_pusher = MagicMock()
        candidates = [
            {"category_id": 1, "category_name": "A", "category_score": 0.5},
            {"category_id": 2, "category_name": "B", "category_score": 0.9},
        ]
        emit_categorization_transaction_updated(mock_pusher, 42, candidates)

        mock_pusher.trigger.assert_called_once_with(
            "bank-transactions",
            "categorization.transaction_updated",
            {
                "bank_transaction_id": 42,
                "ai_top_candidate": {
                    "category_id": 2,
                    "category_name": "B",
                    "category_score": 0.9,
                },
            },
        )

    def test_emits_null_ai_top_when_no_valid_candidate(self):
        mock_pusher = MagicMock()
        emit_categorization_transaction_updated(mock_pusher, 7, [])

        mock_pusher.trigger.assert_called_once_with(
            "bank-transactions",
            "categorization.transaction_updated",
            {"bank_transaction_id": 7, "ai_top_candidate": None},
        )
