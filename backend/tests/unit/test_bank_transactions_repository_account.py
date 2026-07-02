import pytest
from unittest.mock import MagicMock
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
def test_insert_transactions_includes_account_id_in_sql():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1,)  # RETURNING id
    row = MagicMock()
    row.reference_number = "REF001"
    row.booking_date = "2026-01-01"
    row.value_date = None
    row.counterparty = None
    row.counterparty_address = None
    row.source_account = None
    row.target_account = None
    row.description = "Test"
    row.amount = MagicMock(__float__=lambda s: -10.0)
    row.currency = "PLN"
    row.operation_type = None

    # Act
    repo.insert_transactions([row], account_id=3)

    # Assert — account_id must appear in the INSERT SQL and params
    sql = cursor.execute.call_args[0][0]
    params = cursor.execute.call_args[0][1]
    assert "account_id" in sql
    assert 3 in params


@pytest.mark.unit
def test_get_list_adds_account_id_filter_to_where():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    repo.get_list(account_id=2)

    # Assert
    sql = cursor.execute.call_args[0][0]
    params = cursor.execute.call_args[0][1]
    assert "account_id" in sql
    assert 2 in params


@pytest.mark.unit
def test_get_list_no_account_id_filter_omits_clause():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    repo.get_list()

    # Assert — account_id filter should NOT appear in params
    params = cursor.execute.call_args[0][1]
    assert 2 not in params
