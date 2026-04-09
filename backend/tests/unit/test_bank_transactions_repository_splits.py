import pytest
from unittest.mock import MagicMock, call
from src.repositories.bank_transactions import BankTransactionsRepository


def make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = BankTransactionsRepository.__new__(BankTransactionsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_update_category_deletes_splits_before_setting_category():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.update_category(transaction_id=1, category_id=5)

    # Assert — DELETE from splits must come before UPDATE on bank_transactions
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    delete_idx = next(
        i for i, s in enumerate(executed_sqls)
        if "DELETE" in s and "bank_transaction_category_splits" in s
    )
    update_idx = next(
        i for i, s in enumerate(executed_sqls)
        if "UPDATE" in s and "bank_transactions" in s
    )
    assert delete_idx < update_idx
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_category_rollback_on_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    repo.update_category(transaction_id=1, category_id=5)

    # Assert
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()
