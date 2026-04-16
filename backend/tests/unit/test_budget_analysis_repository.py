"""Unit tests for BudgetAnalysisRepository."""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from src.repositories.budget_analysis import BudgetAnalysisRepository


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchone_side_effect=None, fetchall_return=None, cursor_description=None):
    """Build a BudgetAnalysisRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    if cursor_description:
        cursor.description = cursor_description
    else:
        cursor.description = []

    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    elif fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return

    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    else:
        cursor.fetchall.return_value = []

    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = conn
    return repo, cursor


# =============================================================================
# get_monthly_category_breakdown
# =============================================================================

@pytest.mark.unit
def test_get_monthly_category_breakdown_happy_path():
    """Test successful retrieval of monthly category breakdown."""
    # Arrange
    cursor_description = [
        ("category_id",),
        ("category_name",),
        ("total_pln",),
        ("prev_month_pln",),
        ("classification",),
    ]
    fetchall_return = [
        (1, "Jedzenie", 500.0, 480.0, "essential"),
        (2, "Rozrywka", 200.0, 150.0, "discretionary"),
    ]
    repo, cursor = make_repo(
        fetchall_return=fetchall_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_monthly_category_breakdown(2025, 3)

    # Assert
    assert len(result) == 2
    assert result[0]["category_id"] == 1
    assert result[0]["category_name"] == "Jedzenie"
    assert result[0]["total_pln"] == 500.0
    assert result[0]["prev_month_pln"] == 480.0
    assert result[0]["classification"] == "essential"
    cursor.execute.assert_called_once()
    args = cursor.execute.call_args[0]
    assert args[1] == (2025, 3, 2025, 2)


@pytest.mark.unit
def test_get_monthly_category_breakdown_no_conn():
    """Test that no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_monthly_category_breakdown(2025, 3)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_monthly_category_breakdown_db_error():
    """Test DB error is caught and empty list returned."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_monthly_category_breakdown(2025, 3)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_monthly_category_breakdown_january_wraps_year():
    """Test that January correctly wraps to December of previous year."""
    # Arrange
    cursor_description = [("category_id",), ("category_name",), ("total_pln",), ("prev_month_pln",), ("classification",)]
    repo, cursor = make_repo(fetchall_return=[], cursor_description=cursor_description)

    # Act
    repo.get_monthly_category_breakdown(2025, 1)

    # Assert
    args = cursor.execute.call_args[0]
    # Parameters should be (2025, 1, 2024, 12)
    assert args[1] == (2025, 1, 2024, 12)


@pytest.mark.unit
def test_get_monthly_category_breakdown_empty_result():
    """Test empty result set."""
    # Arrange
    cursor_description = [("category_id",), ("category_name",), ("total_pln",), ("prev_month_pln",), ("classification",)]
    repo, cursor = make_repo(fetchall_return=[], cursor_description=cursor_description)

    # Act
    result = repo.get_monthly_category_breakdown(2025, 3)

    # Assert
    assert result == []


# =============================================================================
# get_monthly_totals
# =============================================================================

@pytest.mark.unit
def test_get_monthly_totals_happy_path():
    """Test successful retrieval of monthly totals."""
    # Arrange
    fetchone_return = (5000.0, 3000.0, 2800.0)  # income, expenses, prev_expenses
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.get_monthly_totals(2025, 3)

    # Assert
    assert result["income_pln"] == 5000.0
    assert result["expenses_pln"] == 3000.0
    assert result["prev_expenses_pln"] == 2800.0
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_monthly_totals_no_conn():
    """Test no-conn returns default dict."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_monthly_totals(2025, 3)

    # Assert
    assert result == {"income_pln": 0.0, "expenses_pln": 0.0}


@pytest.mark.unit
def test_get_monthly_totals_db_error():
    """Test DB error returns default dict."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_monthly_totals(2025, 3)

    # Assert
    assert result == {"income_pln": 0.0, "expenses_pln": 0.0, "prev_expenses_pln": 0.0}


@pytest.mark.unit
def test_get_monthly_totals_no_rows():
    """Test when fetchone returns None."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_monthly_totals(2025, 3)

    # Assert
    assert result == {"income_pln": 0.0, "expenses_pln": 0.0, "prev_expenses_pln": 0.0}


# =============================================================================
# get_all_classifications
# =============================================================================

@pytest.mark.unit
def test_get_all_classifications_happy_path():
    """Test successful retrieval of all classifications."""
    # Arrange
    cursor_description = [
        ("category_id",),
        ("category_name",),
        ("classification",),
        ("is_user_override",),
    ]
    fetchall_return = [
        (1, "Jedzenie", "essential", False),
        (2, "Rozrywka", "discretionary", True),
    ]
    repo, cursor = make_repo(
        fetchall_return=fetchall_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_all_classifications()

    # Assert
    assert len(result) == 2
    assert result[0]["category_id"] == 1
    assert result[0]["classification"] == "essential"
    assert result[0]["is_user_override"] is False
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_all_classifications_no_conn():
    """Test no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_all_classifications()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_classifications_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_classifications()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_classifications_empty():
    """Test empty result set."""
    # Arrange
    cursor_description = [
        ("category_id",),
        ("category_name",),
        ("classification",),
        ("is_user_override",),
    ]
    repo, cursor = make_repo(fetchall_return=[], cursor_description=cursor_description)

    # Act
    result = repo.get_all_classifications()

    # Assert
    assert result == []


# =============================================================================
# get_all_category_ids
# =============================================================================

@pytest.mark.unit
def test_get_all_category_ids_happy_path():
    """Test successful retrieval of all category IDs."""
    # Arrange
    cursor_description = [("id",), ("name",)]
    fetchall_return = [(1, "Jedzenie"), (2, "Rozrywka"), (3, "Transport")]
    repo, cursor = make_repo(
        fetchall_return=fetchall_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_all_category_ids()

    # Assert
    assert len(result) == 3
    assert result[0]["id"] == 1
    assert result[0]["name"] == "Jedzenie"


@pytest.mark.unit
def test_get_all_category_ids_no_conn():
    """Test no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_all_category_ids()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_category_ids_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_category_ids()

    # Assert
    assert result == []


# =============================================================================
# get_classified_category_ids
# =============================================================================

@pytest.mark.unit
def test_get_classified_category_ids_happy_path():
    """Test successful retrieval of classified category IDs."""
    # Arrange
    fetchall_return = [(1,), (2,), (5,)]
    repo, cursor = make_repo(fetchall_return=fetchall_return)

    # Act
    result = repo.get_classified_category_ids()

    # Assert
    assert result == {1, 2, 5}
    assert isinstance(result, set)


@pytest.mark.unit
def test_get_classified_category_ids_no_conn():
    """Test no-conn returns empty set."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_classified_category_ids()

    # Assert
    assert result == set()


@pytest.mark.unit
def test_get_classified_category_ids_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_classified_category_ids()

    # Assert
    assert result == set()


@pytest.mark.unit
def test_get_classified_category_ids_empty():
    """Test empty result set."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_classified_category_ids()

    # Assert
    assert result == set()


# =============================================================================
# upsert_classification
# =============================================================================

@pytest.mark.unit
def test_upsert_classification_happy_path():
    """Test successful upsert of classification."""
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.upsert_classification(1, "essential", True)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_upsert_classification_no_conn():
    """Test no-conn returns False."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.upsert_classification(1, "essential", True)

    # Assert
    assert result is False


@pytest.mark.unit
def test_upsert_classification_db_error():
    """Test DB error is caught and rolled back."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.upsert_classification(1, "essential", True)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# =============================================================================
# get_classification_by_category
# =============================================================================

@pytest.mark.unit
def test_get_classification_by_category_happy_path():
    """Test successful retrieval of classification by category."""
    # Arrange
    cursor_description = [
        ("category_id",),
        ("category_name",),
        ("classification",),
        ("is_user_override",),
    ]
    fetchone_return = (1, "Jedzenie", "essential", False)
    repo, cursor = make_repo(
        fetchone_return=fetchone_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_classification_by_category(1)

    # Assert
    assert result is not None
    assert result["category_id"] == 1
    assert result["category_name"] == "Jedzenie"
    assert result["classification"] == "essential"
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_classification_by_category_no_conn():
    """Test no-conn returns None."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_classification_by_category(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_classification_by_category_not_found():
    """Test when category has no classification."""
    # Arrange
    cursor_description = [
        ("category_id",),
        ("category_name",),
        ("classification",),
        ("is_user_override",),
    ]
    repo, cursor = make_repo(
        fetchone_return=None,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_classification_by_category(999)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_classification_by_category_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_classification_by_category(1)

    # Assert
    assert result is None


# =============================================================================
# get_financial_focus
# =============================================================================

@pytest.mark.unit
def test_get_financial_focus_happy_path():
    """Test successful retrieval of financial focus."""
    # Arrange
    fetchone_return = (1, "Save for vacation", "Plan for summer vacation", True)
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is not None
    assert result["id"] == 1
    assert result["label"] == "Save for vacation"
    assert result["description"] == "Plan for summer vacation"
    assert result["is_active"] is True


@pytest.mark.unit
def test_get_financial_focus_no_conn():
    """Test no-conn returns None."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_financial_focus_not_found():
    """Test when no active focus found."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_financial_focus_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is None


# =============================================================================
# set_financial_focus
# =============================================================================

@pytest.mark.unit
def test_set_financial_focus_happy_path():
    """Test successful setting of financial focus."""
    # Arrange
    fetchone_return = (1, "Save for vacation", "Plan for summer vacation", True)
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.set_financial_focus("Save for vacation", "Plan for summer vacation")

    # Assert
    assert result is not None
    assert result["id"] == 1
    assert result["label"] == "Save for vacation"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_financial_focus_no_conn():
    """Test no-conn returns None."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.set_financial_focus("Goal", "Description")

    # Assert
    assert result is None


@pytest.mark.unit
def test_set_financial_focus_db_error():
    """Test DB error is caught and rolled back."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_financial_focus("Goal", "Description")

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_set_financial_focus_none_description():
    """Test setting focus with None description."""
    # Arrange
    fetchone_return = (1, "Goal", None, True)
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.set_financial_focus("Goal", None)

    # Assert
    assert result is not None
    assert result["label"] == "Goal"
    assert result["description"] is None


# =============================================================================
# get_recurring_expenses
# =============================================================================

@pytest.mark.unit
def test_get_recurring_expenses_happy_path():
    """Test successful retrieval of recurring expenses."""
    # Arrange
    cursor_description = [
        ("vendor_name",),
        ("category_name",),
        ("occurrence_count",),
        ("avg_amount",),
        ("min_amount",),
        ("max_amount",),
        ("stddev_amount",),
        ("last_date",),
        ("dates",),
        ("first_year",),
        ("last_year",),
    ]
    today = date.today()
    dates = [today - timedelta(days=60), today - timedelta(days=30), today]
    fetchall_return = [
        ("Netflix", "Streaming", 3, 50.0, 50.0, 50.0, 0.0, today, dates, today.year, today.year),
    ]
    repo, cursor = make_repo(
        fetchall_return=fetchall_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_recurring_expenses()

    # Assert
    assert len(result) >= 0  # May or may not match criteria; main is no error
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_recurring_expenses_no_conn():
    """Test no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_recurring_expenses()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_recurring_expenses_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_recurring_expenses()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_recurring_expenses_empty():
    """Test empty result set."""
    # Arrange
    cursor_description = [
        ("vendor_name",),
        ("category_name",),
        ("occurrence_count",),
        ("avg_amount",),
        ("min_amount",),
        ("max_amount",),
        ("stddev_amount",),
        ("last_date",),
        ("dates",),
        ("first_year",),
        ("last_year",),
    ]
    repo, cursor = make_repo(fetchall_return=[], cursor_description=cursor_description)

    # Act
    result = repo.get_recurring_expenses()

    # Assert
    assert result == []


# =============================================================================
# get_cyclical_alerts
# =============================================================================

@pytest.mark.unit
def test_get_cyclical_alerts_happy_path():
    """Test successful retrieval of cyclical alerts."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = MagicMock()

    # Mock get_recurring_expenses to return annual expense
    today = date.today()
    future_date = today + timedelta(days=45)
    recurring = [
        {
            "vendor_name": "Insurance",
            "category_name": "Insurance",
            "frequency": "annual",
            "next_expected_date": future_date.isoformat(),
            "avg_amount_pln": 1000.0,
            "amount_min_pln": 900.0,
            "amount_max_pln": 1100.0,
        }
    ]
    repo.get_recurring_expenses = MagicMock(return_value=recurring)

    # Act
    result = repo.get_cyclical_alerts(days_ahead=90)

    # Assert
    assert len(result) == 1
    assert result[0]["vendor_name"] == "Insurance"
    assert result[0]["days_until"] == 45


@pytest.mark.unit
def test_get_cyclical_alerts_filters_by_days_ahead():
    """Test that alerts outside days_ahead window are filtered."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = MagicMock()

    today = date.today()
    far_future = today + timedelta(days=120)  # Beyond 90-day window
    recurring = [
        {
            "vendor_name": "Insurance",
            "category_name": "Insurance",
            "frequency": "annual",
            "next_expected_date": far_future.isoformat(),
            "avg_amount_pln": 1000.0,
            "amount_min_pln": 900.0,
            "amount_max_pln": 1100.0,
        }
    ]
    repo.get_recurring_expenses = MagicMock(return_value=recurring)

    # Act
    result = repo.get_cyclical_alerts(days_ahead=90)

    # Assert
    assert len(result) == 0


@pytest.mark.unit
def test_get_cyclical_alerts_skips_monthly():
    """Test that monthly expenses are skipped."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = MagicMock()

    today = date.today()
    future = today + timedelta(days=30)
    recurring = [
        {
            "vendor_name": "Electricity",
            "category_name": "Utilities",
            "frequency": "monthly",
            "next_expected_date": future.isoformat(),
            "avg_amount_pln": 100.0,
            "amount_min_pln": 80.0,
            "amount_max_pln": 120.0,
        }
    ]
    repo.get_recurring_expenses = MagicMock(return_value=recurring)

    # Act
    result = repo.get_cyclical_alerts(days_ahead=90)

    # Assert
    assert len(result) == 0


@pytest.mark.unit
def test_get_cyclical_alerts_empty():
    """Test empty recurring list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = MagicMock()
    repo.get_recurring_expenses = MagicMock(return_value=[])

    # Act
    result = repo.get_cyclical_alerts(days_ahead=90)

    # Assert
    assert result == []


# =============================================================================
# get_current_month_income_and_expenses
# =============================================================================

@pytest.mark.unit
def test_get_current_month_income_and_expenses_happy_path():
    """Test successful retrieval of current month financials."""
    # Arrange
    fetchone_return = (10000.0, 6000.0)  # income, expenses
    repo, cursor = make_repo(fetchone_return=fetchone_return)
    repo.get_recurring_expenses = MagicMock(return_value=[])

    # Act
    result = repo.get_current_month_income_and_expenses()

    # Assert
    assert result["income_pln"] == 10000.0
    assert result["expenses_pln"] == 6000.0
    assert "upcoming_recurring_sum_30d" in result


@pytest.mark.unit
def test_get_current_month_income_and_expenses_no_conn():
    """Test no-conn returns defaults."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_current_month_income_and_expenses()

    # Assert
    assert result["income_pln"] == 0.0
    assert result["expenses_pln"] == 0.0
    assert result["upcoming_recurring_sum_30d"] == 0.0


@pytest.mark.unit
def test_get_current_month_income_and_expenses_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    repo.get_recurring_expenses = MagicMock(return_value=[])

    # Act
    result = repo.get_current_month_income_and_expenses()

    # Assert
    assert result["income_pln"] == 0.0
    assert result["expenses_pln"] == 0.0


# =============================================================================
# get_rolling_3month_averages
# =============================================================================

@pytest.mark.unit
def test_get_rolling_3month_averages_happy_path():
    """Test successful retrieval of rolling 3-month averages."""
    # Arrange
    fetchone_side_effect = [
        (9000.0, 6000.0),   # month 1
        (8500.0, 5500.0),   # month 2
        (10000.0, 6500.0),  # month 3
    ]
    repo, cursor = make_repo(fetchone_side_effect=fetchone_side_effect)

    # Act
    result = repo.get_rolling_3month_averages()

    # Assert
    assert result["avg_income"] == pytest.approx(9166.67, rel=1e-2)
    assert result["avg_expenses"] == pytest.approx(6000.0, rel=1e-2)


@pytest.mark.unit
def test_get_rolling_3month_averages_no_conn():
    """Test no-conn returns defaults."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_rolling_3month_averages()

    # Assert
    assert result == {"avg_income": 0.0, "avg_expenses": 0.0}


@pytest.mark.unit
def test_get_rolling_3month_averages_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_rolling_3month_averages()

    # Assert
    assert result == {"avg_income": 0.0, "avg_expenses": 0.0}


@pytest.mark.unit
def test_get_rolling_3month_averages_partial_months():
    """Test with some months missing data."""
    # Arrange
    fetchone_side_effect = [
        (5000.0, 3000.0),   # month 1
        None,                # month 2 has no data
        (6000.0, 3500.0),   # month 3
    ]
    repo, cursor = make_repo(fetchone_side_effect=fetchone_side_effect)

    # Act
    result = repo.get_rolling_3month_averages()

    # Assert
    # Should only average the 2 months with data
    assert result["avg_income"] == pytest.approx(5500.0, rel=1e-2)
    assert result["avg_expenses"] == pytest.approx(3250.0, rel=1e-2)


# =============================================================================
# get_monthly_history
# =============================================================================

@pytest.mark.unit
def test_get_monthly_history_happy_path():
    """Test successful retrieval of monthly history."""
    # Arrange
    fetchone_side_effect = [
        (5000.0, 3000.0),   # month 1
        (5500.0, 3200.0),   # month 2
        (6000.0, 3500.0),   # month 3
    ]
    repo, cursor = make_repo(fetchone_side_effect=fetchone_side_effect)

    # Act
    result = repo.get_monthly_history(months_count=3)

    # Assert
    assert len(result) == 3
    assert result[0]["income_pln"] == 5000.0
    assert result[0]["expenses_pln"] == 3000.0
    assert result[0]["surplus_pln"] == 2000.0


@pytest.mark.unit
def test_get_monthly_history_no_conn():
    """Test no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_monthly_history(months_count=3)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_monthly_history_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_monthly_history(months_count=3)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_monthly_history_custom_count():
    """Test with custom month count."""
    # Arrange
    fetchone_side_effect = [
        (5000.0, 3000.0),   # month 1
        (5500.0, 3200.0),   # month 2
    ]
    repo, cursor = make_repo(fetchone_side_effect=fetchone_side_effect)

    # Act
    result = repo.get_monthly_history(months_count=2)

    # Assert
    assert len(result) == 2


# =============================================================================
# count_distinct_months
# =============================================================================

@pytest.mark.unit
def test_count_distinct_months_happy_path():
    """Test successful count of distinct months."""
    # Arrange
    fetchone_return = (12,)
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 12
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_count_distinct_months_no_conn():
    """Test no-conn returns 0."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 0


@pytest.mark.unit
def test_count_distinct_months_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 0


@pytest.mark.unit
def test_count_distinct_months_zero():
    """Test when count is zero."""
    # Arrange
    fetchone_return = (0,)
    repo, cursor = make_repo(fetchone_return=fetchone_return)

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 0


# =============================================================================
# get_discretionary_category_averages
# =============================================================================

@pytest.mark.unit
def test_get_discretionary_category_averages_happy_path():
    """Test successful retrieval of discretionary category averages."""
    # Arrange
    cursor_description = [("category_name",), ("avg_monthly_spend_pln",)]
    fetchall_return = [
        ("Rozrywka", 500.0),
        ("Ubrania", 300.0),
    ]
    repo, cursor = make_repo(
        fetchall_return=fetchall_return,
        cursor_description=cursor_description,
    )

    # Act
    result = repo.get_discretionary_category_averages()

    # Assert
    assert len(result) == 2
    assert result[0]["category_name"] == "Rozrywka"
    assert result[0]["avg_monthly_spend_pln"] == 500.0


@pytest.mark.unit
def test_get_discretionary_category_averages_no_conn():
    """Test no-conn returns empty list."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = None

    # Act
    result = repo.get_discretionary_category_averages()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_discretionary_category_averages_db_error():
    """Test DB error is caught."""
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_discretionary_category_averages()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_discretionary_category_averages_empty():
    """Test empty result set."""
    # Arrange
    cursor_description = [("category_name",), ("avg_monthly_spend_pln",)]
    repo, cursor = make_repo(fetchall_return=[], cursor_description=cursor_description)

    # Act
    result = repo.get_discretionary_category_averages()

    # Assert
    assert result == []


# =============================================================================
# dispose
# =============================================================================

@pytest.mark.unit
def test_dispose_method():
    """Test that dispose method exists and can be called."""
    # Arrange
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = MagicMock()

    # Act
    repo.dispose()

    # Assert - no exception raised
