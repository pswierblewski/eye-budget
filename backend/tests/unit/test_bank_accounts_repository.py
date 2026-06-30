import pytest
from unittest.mock import MagicMock
from src.repositories.bank_accounts import BankAccountsRepository


def make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = BankAccountsRepository.__new__(BankAccountsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_list_with_stats_returns_empty_when_no_rows():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    result = repo.list_with_stats()

    # Assert
    assert result == []
    cursor.execute.assert_called_once()
    assert "bank_accounts" in cursor.execute.call_args[0][0]


@pytest.mark.unit
def test_list_with_stats_maps_row_to_model():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = [
        (1, "Pekao SA", "pekao", "blue", 500.0, -200.0, 5)
    ]

    # Act
    result = repo.list_with_stats()

    # Assert
    assert len(result) == 1
    acc = result[0]
    assert acc.id == 1
    assert acc.name == "Pekao SA"
    assert acc.bank_type == "pekao"
    assert acc.color == "blue"
    assert acc.total_income == 500.0
    assert acc.total_expense == -200.0
    assert acc.transaction_count == 5


@pytest.mark.unit
def test_get_by_id_returns_none_when_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = None

    # Act
    result = repo.get_by_id(99)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_returns_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1, "Pekao SA", "pekao", "blue")

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.bank_type == "pekao"


@pytest.mark.unit
def test_create_returns_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (7, "Revolut", "revolut", "purple")

    # Act
    result = repo.create("Revolut", "revolut", "purple")

    # Assert
    assert result.id == 7
    assert result.name == "Revolut"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_returns_none_when_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = None

    # Act
    result = repo.update(99, "New Name", "green")

    # Assert
    assert result is None
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_returns_updated_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1, "Nowa Nazwa", "pekao", "green")

    # Act
    result = repo.update(1, "Nowa Nazwa", "green")

    # Assert
    assert result is not None
    assert result.name == "Nowa Nazwa"
    assert result.color == "green"


@pytest.mark.unit
def test_has_transactions_returns_true_when_count_positive():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (3,)

    # Act
    result = repo.has_transactions(1)

    # Assert
    assert result is True


@pytest.mark.unit
def test_has_transactions_returns_false_when_zero():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (0,)

    # Act
    result = repo.has_transactions(1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_returns_false_when_account_has_transactions():
    # Arrange
    repo, cursor = make_repo()
    # First call: has_transactions check
    cursor.fetchone.side_effect = [(3,)]

    # Act
    result = repo.delete(1)

    # Assert
    assert result is False
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_delete_returns_true_on_success():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.side_effect = [(0,)]  # has_transactions → 0

    # Act
    result = repo.delete(1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    executed = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s for s in executed)


@pytest.mark.unit
def test_create_rollback_on_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act / Assert — should not raise
    try:
        repo.create("Test", "pekao", "blue")
    except Exception:
        pass

    repo.conn.rollback.assert_called()
