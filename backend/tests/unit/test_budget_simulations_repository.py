"""
Unit tests for BudgetSimulationsRepository.
"""
import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime, date

from src.repositories.budget_simulations import BudgetSimulationsRepository


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Create a mock BudgetSimulationsRepository for testing."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = conn
    return repo, cursor


# ------------------------------------------------------------------
# create_simulation tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_create_simulation_happy_path():
    """Test successful simulation creation."""
    # Arrange
    row = (1, "Budget Test", "Coffee", 5.50, "recurring",
           "2024-01-01", "pending", None, None, datetime(2024, 1, 1))
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.create_simulation(
        name="Budget Test",
        expense_name="Coffee",
        amount=5.50,
        expense_type="recurring",
        start_date="2024-01-01"
    )

    # Assert
    assert result is not None
    assert result["id"] == 1
    assert result["name"] == "Budget Test"
    assert result["expense_name"] == "Coffee"
    assert abs(result["expense_amount"] - 5.50) < 0.01
    assert result["expense_type"] == "recurring"
    assert result["status"] == "pending"
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_create_simulation_no_conn():
    """Test create_simulation returns None when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    result = repo.create_simulation(
        name="Budget Test",
        expense_name="Coffee",
        amount=5.50,
        expense_type="recurring",
        start_date="2024-01-01"
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_simulation_db_error():
    """Test create_simulation handles DB errors with rollback."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=_UNSET)
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.create_simulation(
        name="Budget Test",
        expense_name="Coffee",
        amount=5.50,
        expense_type="recurring",
        start_date="2024-01-01"
    )

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_create_simulation_no_row():
    """Test create_simulation returns None when no row returned."""
    # Arrange
    repo, _ = make_repo(fetchone_return=None)

    # Act
    result = repo.create_simulation(
        name="Budget Test",
        expense_name="Coffee",
        amount=5.50,
        expense_type="recurring",
        start_date="2024-01-01"
    )

    # Assert
    assert result is None
    repo.conn.commit.assert_called_once()


# ------------------------------------------------------------------
# get_simulation tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_simulation_happy_path():
    """Test successful simulation retrieval by ID."""
    # Arrange
    row = (1, "Budget Test", "Coffee", 5.50, "recurring",
           "2024-01-01", "completed", '{"key": "value"}', None, datetime(2024, 1, 1))
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.get_simulation(1)

    # Assert
    assert result is not None
    assert result["id"] == 1
    assert result["name"] == "Budget Test"
    assert result["status"] == "completed"
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_simulation_no_conn():
    """Test get_simulation returns None when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    result = repo.get_simulation(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_simulation_not_found():
    """Test get_simulation returns None when simulation not found."""
    # Arrange
    repo, _ = make_repo(fetchone_return=None)

    # Act
    result = repo.get_simulation(999)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_simulation_db_error():
    """Test get_simulation handles DB errors gracefully."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_simulation(1)

    # Assert
    assert result is None


# ------------------------------------------------------------------
# get_all_simulations tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_simulations_happy_path():
    """Test successful retrieval of all simulations."""
    # Arrange
    row1 = (1, "Budget 1", "Coffee", 5.50, "recurring",
            "2024-01-01", "completed", None, None, datetime(2024, 1, 1))
    row2 = (2, "Budget 2", "Lunch", 12.00, "once",
            "2024-01-02", "pending", None, None, datetime(2024, 1, 2))
    repo, cursor = make_repo(fetchall_return=[row1, row2])

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["name"] == "Budget 1"
    assert result[1]["id"] == 2
    assert result[1]["name"] == "Budget 2"


@pytest.mark.unit
def test_get_all_simulations_no_conn():
    """Test get_all_simulations returns empty list when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_simulations_empty():
    """Test get_all_simulations returns empty list when no simulations."""
    # Arrange
    repo, _ = make_repo(fetchall_return=[])

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_simulations_db_error():
    """Test get_all_simulations handles DB errors gracefully."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert result == []


# ------------------------------------------------------------------
# update_simulation_status tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_update_simulation_status_happy_path():
    """Test successful simulation status update."""
    # Arrange
    repo, cursor = make_repo()
    result_data = {"total_savings": 100}

    # Act
    repo.update_simulation_status(
        sim_id=1,
        status="completed",
        result_json=result_data
    )

    # Assert
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()
    cursor.execute.assert_called_once()
    call_args = cursor.execute.call_args
    assert "UPDATE budget_simulations" in call_args[0][0]


@pytest.mark.unit
def test_update_simulation_status_with_error():
    """Test update_simulation_status with error message."""
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.update_simulation_status(
        sim_id=1,
        status="failed",
        error="Calculation error"
    )

    # Assert
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()
    # execute() is called with (sql_string, (params_tuple))
    call_args = cursor.execute.call_args[0]  # Get positional args
    params_tuple = call_args[1]  # The tuple of parameters
    # params: (status, result_json, error, sim_id)
    assert params_tuple[0] == "failed"  # status
    assert params_tuple[1] is None  # result_json is None
    assert params_tuple[2] == "Calculation error"  # error
    assert params_tuple[3] == 1  # sim_id


@pytest.mark.unit
def test_update_simulation_status_no_conn():
    """Test update_simulation_status returns early when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    repo.update_simulation_status(sim_id=1, status="completed")

    # Assert - Should return without doing anything (no-op)


@pytest.mark.unit
def test_update_simulation_status_db_error():
    """Test update_simulation_status handles DB errors with rollback."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    repo.update_simulation_status(sim_id=1, status="completed")

    # Assert
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ------------------------------------------------------------------
# delete_simulation tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_delete_simulation_happy_path():
    """Test successful simulation deletion."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete_simulation(1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_delete_simulation_not_found():
    """Test delete_simulation returns False when no rows affected."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete_simulation(999)

    # Assert
    assert result is False
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_simulation_no_conn():
    """Test delete_simulation returns False when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    result = repo.delete_simulation(1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_simulation_db_error():
    """Test delete_simulation handles DB errors with rollback."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.delete_simulation(1)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ------------------------------------------------------------------
# get_current_recommendations tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_current_recommendations_happy_path():
    """Test successful retrieval of current recommendations."""
    # Arrange
    row = (1, datetime(2024, 1, 1), date(2024, 1, 31),
           '[{"insight": "save more"}]', True, 6)
    repo, _ = make_repo(fetchone_return=row)

    # Act
    result = repo.get_current_recommendations()

    # Assert
    assert result is not None
    assert result["id"] == 1
    assert result["is_current"] is True
    assert result["months_of_data"] == 6
    # recommendations_json is returned as-is from DB (string)
    assert result["recommendations_json"] == '[{"insight": "save more"}]'


@pytest.mark.unit
def test_get_current_recommendations_no_conn():
    """Test get_current_recommendations returns None when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    result = repo.get_current_recommendations()

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_current_recommendations_not_found():
    """Test get_current_recommendations returns None when none exist."""
    # Arrange
    repo, _ = make_repo(fetchone_return=None)

    # Act
    result = repo.get_current_recommendations()

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_current_recommendations_db_error():
    """Test get_current_recommendations handles DB errors gracefully."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_current_recommendations()

    # Assert
    assert result is None


# ------------------------------------------------------------------
# save_recommendations tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_save_recommendations_happy_path():
    """Test successful recommendations save."""
    # Arrange
    repo, cursor = make_repo()
    insights = [{"category": "food", "recommendation": "reduce by 10%"}]

    # Act
    repo.save_recommendations(
        insights_json=insights,
        data_through_date="2024-01-31",
        months_of_data=6
    )

    # Assert
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()
    assert cursor.execute.call_count == 2


@pytest.mark.unit
def test_save_recommendations_no_conn():
    """Test save_recommendations returns early when no connection."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = None

    # Act
    repo.save_recommendations(
        insights_json=[],
        data_through_date="2024-01-31",
        months_of_data=6
    )

    # Assert - Should return without errors (no-op)


@pytest.mark.unit
def test_save_recommendations_db_error():
    """Test save_recommendations handles DB errors with rollback."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    repo.save_recommendations(
        insights_json=[{"key": "value"}],
        data_through_date="2024-01-31",
        months_of_data=6
    )

    # Assert
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ------------------------------------------------------------------
# _row_to_dict tests
# ------------------------------------------------------------------

@pytest.mark.unit
def test_row_to_dict_with_datetime():
    """Test _row_to_dict converts datetime to ISO format."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    row = (1, "Test", "Coffee", 5.50, "recurring",
           date(2024, 1, 1), "pending", None, None, datetime(2024, 1, 1, 10, 30))

    # Act
    result = repo._row_to_dict(row)

    # Assert
    assert result["id"] == 1
    assert result["name"] == "Test"
    assert abs(result["expense_amount"] - 5.50) < 0.01
    assert isinstance(result["created_at"], str)
    assert "2024-01-01" in result["created_at"]


@pytest.mark.unit
def test_row_to_dict_with_result_json():
    """Test _row_to_dict preserves result_json string."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    row = (1, "Test", "Coffee", 5.50, "recurring",
           date(2024, 1, 1), "completed", '{"savings": 100}', None, datetime(2024, 1, 1))

    # Act
    result = repo._row_to_dict(row)

    # Assert
    assert result["result_json"] == '{"savings": 100}'


@pytest.mark.unit
def test_row_to_dict_with_error_message():
    """Test _row_to_dict preserves error message."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    row = (1, "Test", "Coffee", 5.50, "recurring",
           date(2024, 1, 1), "failed", None, "Calculation error", datetime(2024, 1, 1))

    # Act
    result = repo._row_to_dict(row)

    # Assert
    assert result["error_message"] == "Calculation error"


@pytest.mark.unit
def test_dispose():
    """Test dispose method does nothing."""
    # Arrange
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)

    # Act
    repo.dispose()

    # Assert - dispose should be a no-op
