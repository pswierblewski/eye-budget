"""
Unit tests for BudgetGoalsRepository.
"""
import pytest
from unittest.mock import MagicMock

from src.repositories.budget_goals import BudgetGoalsRepository


_UNSET = object()

_GOAL_COLUMNS = [
    ("id",),
    ("name",),
    ("target_amount",),
    ("target_date",),
    ("priority_rank",),
    ("monthly_allocation_amount",),
    ("accumulated_progress",),
    ("is_active",),
    ("created_at",),
    ("updated_at",),
]


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Factory function to create a BudgetGoalsRepository with mocked connection."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.description = _GOAL_COLUMNS
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.rowcount = 0
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = conn
    return repo, cursor


# ===== get_all_goals tests =====

@pytest.mark.unit
def test_get_all_goals_returns_empty_list_when_conn_is_none():
    """get_all_goals should return [] when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.get_all_goals()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_goals_returns_list_of_dicts():
    """get_all_goals should return list of dicts with goal data."""
    # Arrange
    row1 = (1, "Goal 1", 5000.0, "2026-12-31", 1, 500.0, 1000.0, True, "2026-01-01", "2026-01-15")
    row2 = (2, "Goal 2", 10000.0, "2027-06-30", 2, 800.0, 2400.0, True, "2026-01-02", "2026-01-16")
    repo, cursor = make_repo(fetchall_return=[row1, row2])

    # Act
    result = repo.get_all_goals()

    # Assert
    assert len(result) == 2
    assert result[0] == {
        "id": 1,
        "name": "Goal 1",
        "target_amount": 5000.0,
        "target_date": "2026-12-31",
        "priority_rank": 1,
        "monthly_allocation_amount": 500.0,
        "accumulated_progress": 1000.0,
        "is_active": True,
        "created_at": "2026-01-01",
        "updated_at": "2026-01-15",
    }
    assert result[1]["id"] == 2
    assert result[1]["name"] == "Goal 2"


@pytest.mark.unit
def test_get_all_goals_returns_empty_list_when_no_goals():
    """get_all_goals should return [] when no goals exist."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_all_goals()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_goals_returns_empty_list_on_exception():
    """get_all_goals should return [] and log error on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_goals()

    # Assert
    assert result == []
    cursor.execute.assert_called_once()


# ===== get_goal tests =====

@pytest.mark.unit
def test_get_goal_returns_none_when_conn_is_none():
    """get_goal should return None when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.get_goal(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_goal_returns_dict_when_goal_found():
    """get_goal should return dict when goal exists."""
    # Arrange
    row = (1, "Goal 1", 5000.0, "2026-12-31", 1, 500.0, 1000.0, True, "2026-01-01", "2026-01-15")
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.get_goal(1)

    # Assert
    assert result == {
        "id": 1,
        "name": "Goal 1",
        "target_amount": 5000.0,
        "target_date": "2026-12-31",
        "priority_rank": 1,
        "monthly_allocation_amount": 500.0,
        "accumulated_progress": 1000.0,
        "is_active": True,
        "created_at": "2026-01-01",
        "updated_at": "2026-01-15",
    }
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_goal_returns_none_when_goal_not_found():
    """get_goal should return None when goal does not exist."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_goal(999)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_goal_returns_none_on_exception():
    """get_goal should return None and log error on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_goal(1)

    # Assert
    assert result is None
    cursor.execute.assert_called_once()


# ===== create_goal tests =====

@pytest.mark.unit
def test_create_goal_returns_none_when_conn_is_none():
    """create_goal should return None when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.create_goal("New Goal", 5000.0, "2026-12-31", 1, 500.0)

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_goal_returns_dict_on_success():
    """create_goal should return dict with created goal data."""
    # Arrange
    row = (1, "New Goal", 5000.0, "2026-12-31", 1, 500.0, 0.0, True, "2026-04-16", "2026-04-16")
    repo, cursor = make_repo(fetchone_return=row)
    conn_mock = repo.conn

    # Act
    result = repo.create_goal("New Goal", 5000.0, "2026-12-31", 1, 500.0)

    # Assert
    assert result == {
        "id": 1,
        "name": "New Goal",
        "target_amount": 5000.0,
        "target_date": "2026-12-31",
        "priority_rank": 1,
        "monthly_allocation_amount": 500.0,
        "accumulated_progress": 0.0,
        "is_active": True,
        "created_at": "2026-04-16",
        "updated_at": "2026-04-16",
    }
    cursor.execute.assert_called_once()
    conn_mock.commit.assert_called_once()


@pytest.mark.unit
def test_create_goal_returns_none_when_no_row_returned():
    """create_goal should return None when INSERT returns no row."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)
    conn_mock = repo.conn

    # Act
    result = repo.create_goal("New Goal", 5000.0, "2026-12-31", 1, 500.0)

    # Assert
    assert result is None
    conn_mock.commit.assert_called_once()


@pytest.mark.unit
def test_create_goal_rolls_back_on_exception():
    """create_goal should rollback and return None on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    conn_mock = repo.conn

    # Act
    result = repo.create_goal("New Goal", 5000.0, "2026-12-31", 1, 500.0)

    # Assert
    assert result is None
    conn_mock.rollback.assert_called_once()


# ===== update_goal tests =====

@pytest.mark.unit
def test_update_goal_returns_none_when_conn_is_none():
    """update_goal should return None when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.update_goal(1, name="Updated")

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_goal_returns_none_when_no_fields():
    """update_goal should return get_goal result when no fields provided."""
    # Arrange
    row = (1, "Goal 1", 5000.0, "2026-12-31", 1, 500.0, 1000.0, True, "2026-01-01", "2026-01-15")
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.update_goal(1)

    # Assert
    assert result is not None
    assert result["id"] == 1


@pytest.mark.unit
def test_update_goal_updates_name_and_commits():
    """update_goal should update fields, commit, and return updated goal."""
    # Arrange
    row = (1, "Updated Goal", 5000.0, "2026-12-31", 1, 500.0, 1000.0, True, "2026-01-01", "2026-04-16")
    repo, cursor = make_repo(fetchone_return=row)
    conn_mock = repo.conn

    # Act
    result = repo.update_goal(1, name="Updated Goal")

    # Assert
    assert result is not None
    assert result["name"] == "Updated Goal"
    conn_mock.commit.assert_called_once()
    # update_goal calls execute twice: UPDATE then get_goal (SELECT)
    assert cursor.execute.call_count == 2


@pytest.mark.unit
def test_update_goal_maps_frontend_field_names_to_db_columns():
    """update_goal should map frontend field names (e.g., target_amount_pln) to DB columns."""
    # Arrange
    row = (1, "Goal 1", 7500.0, "2026-12-31", 1, 500.0, 1000.0, True, "2026-01-01", "2026-04-16")
    repo, cursor = make_repo(fetchone_return=row)
    conn_mock = repo.conn

    # Act
    result = repo.update_goal(1, target_amount_pln=7500.0)

    # Assert
    assert result is not None
    conn_mock.commit.assert_called_once()
    # Verify that the SQL contains the correct column name (target_amount)
    # update_goal calls execute twice: UPDATE then get_goal (SELECT)
    # Check the first call (UPDATE)
    first_call_args = cursor.execute.call_args_list[0]
    sql = first_call_args[0][0]
    assert "target_amount = %s" in sql


@pytest.mark.unit
def test_update_goal_rolls_back_on_exception():
    """update_goal should rollback and return None on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    conn_mock = repo.conn

    # Act
    result = repo.update_goal(1, name="Updated")

    # Assert
    assert result is None
    conn_mock.rollback.assert_called_once()


# ===== soft_delete_goal tests =====

@pytest.mark.unit
def test_soft_delete_goal_returns_false_when_conn_is_none():
    """soft_delete_goal should return False when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.soft_delete_goal(1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_soft_delete_goal_returns_true_when_goal_deleted():
    """soft_delete_goal should return True when rowcount > 0."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1
    conn_mock = repo.conn

    # Act
    result = repo.soft_delete_goal(1)

    # Assert
    assert result is True
    conn_mock.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_soft_delete_goal_returns_false_when_goal_not_found():
    """soft_delete_goal should return False when rowcount == 0."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0
    conn_mock = repo.conn

    # Act
    result = repo.soft_delete_goal(999)

    # Assert
    assert result is False
    conn_mock.commit.assert_called_once()


@pytest.mark.unit
def test_soft_delete_goal_returns_false_and_rolls_back_on_exception():
    """soft_delete_goal should return False, rollback, and log error on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    conn_mock = repo.conn

    # Act
    result = repo.soft_delete_goal(1)

    # Assert
    assert result is False
    conn_mock.rollback.assert_called_once()


# ===== get_active_goal_allocations_total tests =====

@pytest.mark.unit
def test_get_active_goal_allocations_total_returns_zero_when_conn_is_none():
    """get_active_goal_allocations_total should return 0.0 when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.get_active_goal_allocations_total()

    # Assert
    assert result == 0.0


@pytest.mark.unit
def test_get_active_goal_allocations_total_returns_sum_of_allocations():
    """get_active_goal_allocations_total should return SUM of monthly_allocation_amount."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(2300.0,))

    # Act
    result = repo.get_active_goal_allocations_total()

    # Assert
    assert result == 2300.0
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_active_goal_allocations_total_returns_zero_when_no_goals():
    """get_active_goal_allocations_total should return 0.0 when sum is NULL/0."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(0,))

    # Act
    result = repo.get_active_goal_allocations_total()

    # Assert
    assert result == 0.0


@pytest.mark.unit
def test_get_active_goal_allocations_total_returns_zero_on_exception():
    """get_active_goal_allocations_total should return 0.0 and log error on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_active_goal_allocations_total()

    # Assert
    assert result == 0.0
    cursor.execute.assert_called_once()


# ===== advance_monthly_progress_for_all_active_goals tests =====

@pytest.mark.unit
def test_advance_monthly_progress_returns_none_when_conn_is_none():
    """advance_monthly_progress_for_all_active_goals should return None when connection is None."""
    # Arrange
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = None

    # Act
    result = repo.advance_monthly_progress_for_all_active_goals()

    # Assert
    assert result is None


@pytest.mark.unit
def test_advance_monthly_progress_executes_and_commits():
    """advance_monthly_progress_for_all_active_goals should execute UPDATE and commit."""
    # Arrange
    repo, cursor = make_repo()
    conn_mock = repo.conn

    # Act
    result = repo.advance_monthly_progress_for_all_active_goals()

    # Assert
    assert result is None
    cursor.execute.assert_called_once()
    conn_mock.commit.assert_called_once()


@pytest.mark.unit
def test_advance_monthly_progress_rolls_back_on_exception():
    """advance_monthly_progress_for_all_active_goals should rollback and log error on exception."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    conn_mock = repo.conn

    # Act
    result = repo.advance_monthly_progress_for_all_active_goals()

    # Assert
    assert result is None
    conn_mock.rollback.assert_called_once()
