import pytest
from unittest.mock import MagicMock

from src.repositories.bank_transactions import BankTransactionsRepository


def _make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = BankTransactionsRepository.__new__(BankTransactionsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_ids_for_recategorization_sql_includes_refresh_branch():
    repo, cursor = _make_repo()
    cursor.fetchall.return_value = [(1,), (2,)]

    result = repo.get_ids_for_recategorization()

    assert result == [1, 2]
    sql = cursor.execute.call_args[0][0]
    assert "category_candidates IS NULL" in sql
    assert "jsonb_array_length" in sql
    assert "bank_transaction_category_splits" in sql
    assert "receipt_bank_links" in sql


@pytest.mark.unit
def test_get_ids_for_recategorization_returns_empty_on_error():
    repo, cursor = _make_repo()
    cursor.execute.side_effect = Exception("db")

    assert repo.get_ids_for_recategorization() == []
