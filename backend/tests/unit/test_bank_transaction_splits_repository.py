import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from src.data import BankTransactionSplit, SplitItem
from src.repositories.bank_transaction_splits import BankTransactionSplitsRepository


def make_repo(fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_upsert_splits_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, 5, "Jedzenie", 120.0), (2, 7, "Chemia", 80.0)])
    splits = [SplitItem(category_id=5, amount=120.0), SplitItem(category_id=7, amount=80.0)]

    # Act
    result = repo.upsert_splits(tx_id=1, splits=splits)

    # Assert
    assert len(result) == 2
    assert result[0].category_name == "Jedzenie"
    assert result[0].amount == 120.0
    assert result[1].category_id == 7
    repo.conn.commit.assert_called_once()
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s and "bank_transaction_category_splits" in s for s in executed_sqls)
    assert any("UPDATE" in s and "category_id = NULL" in s for s in executed_sqls)
    assert any("INSERT" in s and "bank_transaction_category_splits" in s for s in executed_sqls)


@pytest.mark.unit
def test_upsert_splits_no_conn_returns_empty():
    # Arrange
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = None

    # Act
    result = repo.upsert_splits(tx_id=1, splits=[SplitItem(category_id=5, amount=100.0)])

    # Assert
    assert result == []


@pytest.mark.unit
def test_upsert_splits_db_error_rolls_back():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.upsert_splits(tx_id=1, splits=[SplitItem(category_id=5, amount=100.0)])

    # Assert
    assert result == []
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_splits_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_splits(tx_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s and "bank_transaction_category_splits" in s for s in executed_sqls)


@pytest.mark.unit
def test_delete_splits_no_conn_returns_false():
    # Arrange
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = None

    # Act
    result = repo.delete_splits(tx_id=1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_splits_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, 5, "Jedzenie", 120.0)])

    # Act
    result = repo.get_splits(tx_id=42)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], BankTransactionSplit)
    assert result[0].id == 1
    assert result[0].category_name == "Jedzenie"
    assert result[0].amount == 120.0


@pytest.mark.unit
def test_get_splits_empty_returns_empty_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_splits(tx_id=99)

    # Assert
    assert result == []
