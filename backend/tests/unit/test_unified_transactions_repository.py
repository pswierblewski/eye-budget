"""
Unit tests for UnifiedTransactionsRepository.

Tests cover:
- get_list: unified transaction listing with pagination and filtering
- get_analytics: aggregated analytics summary (totals, monthly, vendors, categories, MoM)
"""
import pytest
import datetime
from unittest.mock import MagicMock
from src.repositories.unified_transactions import UnifiedTransactionsRepository
from src.data import (
    UnifiedTransaction,
    AnalyticsSummary,
    MonthlySummary,
    CategoryBreakdown,
    VendorBreakdown,
    MonthOverMonth,
    ReceiptCategory,
)

_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Factory to create a mocked UnifiedTransactionsRepository."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn
    return repo, cursor


# ==============================================================================
# get_list
# ==============================================================================

@pytest.mark.unit
def test_get_list_happy_path():
    """Test get_list returns unified transactions with total count."""
    # Arrange
    row = (
        1,                          # id
        'bank',                     # source_type
        datetime.date(2026, 4, 1),  # date
        -50.00,                     # amount
        'Supermarket payment',      # description
        'Tesco',                    # vendor_name
        5,                          # category_id
        'Groceries',                # category_name
        ['food'],                   # tags
        None,                       # status
        False,                      # has_receipt
        None,                       # receipt_scan_id
        'PLN',                      # currency
        None,                       # receipt_category_name
        None,                       # receipt_category_count
        None,                       # receipt_categories
        1,                          # total_count (window function)
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result, total = repo.get_list()

    # Assert
    assert len(result) == 1
    assert total == 1
    assert result[0].id == 1
    assert result[0].source_type == 'bank'
    assert result[0].amount == -50.00
    assert result[0].description == 'Supermarket payment'
    cursor.execute.assert_called_once()
    call_args = cursor.execute.call_args
    assert 'FROM (' in call_args[0][0]  # Verify UNION ALL query


@pytest.mark.unit
def test_get_list_empty_db():
    """Test get_list returns empty list and 0 when database is empty."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result, total = repo.get_list()

    # Assert
    assert result == []
    assert total == 0


@pytest.mark.unit
def test_get_list_no_conn():
    """Test get_list returns ([], 0) when no database connection."""
    # Arrange
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = None

    # Act
    result, total = repo.get_list()

    # Assert
    assert result == []
    assert total == 0


@pytest.mark.unit
def test_get_list_db_error_returns_empty():
    """Test get_list returns ([], 0) and handles exception on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB connection lost")
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result, total = repo.get_list()

    # Assert
    assert result == []
    assert total == 0


@pytest.mark.unit
def test_get_list_with_filters():
    """Test get_list applies filters (status, date_from, amount_min)."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(
        status='done',
        date_from='2026-01-01',
        date_to='2026-12-31',
        amount_min=-100.0,
        limit=10,
        offset=0
    )

    # Assert
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    params = call_args[0][1]
    assert 'WHERE' in sql
    assert 'status = %s' in sql
    assert 'date >= %s' in sql
    assert 'date <= %s' in sql
    assert 'amount >= %s' in sql
    assert 'done' in params


@pytest.mark.unit
def test_get_list_with_search():
    """Test get_list applies ILIKE search filter."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(search='tesco')

    # Assert
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    params = call_args[0][1]
    assert 'ILIKE' in sql
    assert '%tesco%' in params


@pytest.mark.unit
def test_get_list_with_pagination():
    """Test get_list respects limit and offset."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(limit=25, offset=50)

    # Assert
    call_args = cursor.execute.call_args
    params = call_args[0][1]
    assert params[-2] == 25  # limit
    assert params[-1] == 50  # offset


@pytest.mark.unit
def test_get_list_with_sorting():
    """Test get_list applies custom sort order."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(sort_by='amount', sort_dir='asc')

    # Assert
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    assert 'amount ASC' in sql
    assert 'NULLS LAST' in sql


@pytest.mark.unit
def test_get_list_converts_date_to_isoformat():
    """Test get_list converts date objects to ISO strings."""
    # Arrange
    row = (
        1,
        'receipt',
        datetime.date(2026, 4, 15),
        -35.50,
        'Lidl receipt',
        'Lidl',
        None,
        None,
        [],
        'to_confirm',
        False,
        99,
        'PLN',
        None,
        None,
        None,
        1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result, _ = repo.get_list()

    # Assert
    assert result[0].date == '2026-04-15'
    assert isinstance(result[0].date, str)


@pytest.mark.unit
def test_get_list_handles_tags_as_list():
    """Test get_list converts tags array to Python list."""
    # Arrange
    row = (
        1,
        'bank',
        datetime.date(2026, 4, 1),
        -50.0,
        'Test',
        'Vendor',
        1,
        'Food',
        ['groceries', 'urgent'],  # tags as array
        None,
        False,
        None,
        'PLN',
        None,
        None,
        None,
        1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result, _ = repo.get_list()

    # Assert
    assert result[0].tags == ['groceries', 'urgent']


@pytest.mark.unit
def test_get_list_handles_none_tags():
    """Test get_list converts None tags to empty list."""
    # Arrange
    row = (
        1,
        'bank',
        datetime.date(2026, 4, 1),
        -50.0,
        'Test',
        'Vendor',
        1,
        'Food',
        None,  # tags is None
        None,
        False,
        None,
        'PLN',
        None,
        None,
        None,
        1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result, _ = repo.get_list()

    # Assert
    assert result[0].tags == []


@pytest.mark.unit
def test_get_list_handles_receipt_categories_json():
    """Test get_list converts JSON receipt_categories to ReceiptCategory objects."""
    # Arrange
    receipt_cats = [
        {'id': 10, 'name': 'Food / Groceries', 'product_count': 5},
        {'id': 20, 'name': 'Household', 'product_count': 2},
    ]
    row = (
        1,
        'bank',
        datetime.date(2026, 4, 1),
        -50.0,
        'Test',
        'Vendor',
        1,
        'Food',
        [],
        None,
        True,
        99,
        'PLN',
        'Food / Groceries',
        2,  # count of distinct categories
        receipt_cats,  # receipt_categories
        1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result, _ = repo.get_list()

    # Assert
    assert len(result[0].receipt_categories) == 2
    assert result[0].receipt_categories[0].id == 10
    assert result[0].receipt_categories[0].name == 'Food / Groceries'
    assert result[0].receipt_categories[0].product_count == 5


@pytest.mark.unit
def test_get_list_direction_expense():
    """Test get_list filters direction='expense' (amount < 0)."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(direction='expense')

    # Assert
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    assert 'amount < 0' in sql


@pytest.mark.unit
def test_get_list_direction_income():
    """Test get_list filters direction='income' (amount > 0)."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_list(direction='income')

    # Assert
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    assert 'amount > 0' in sql


# ==============================================================================
# get_analytics
# ==============================================================================

@pytest.mark.unit
def test_get_analytics_no_conn():
    """Test get_analytics returns empty AnalyticsSummary when no connection."""
    # Arrange
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.get_analytics()

    # Assert
    assert isinstance(result, AnalyticsSummary)
    assert result.total_expense == 0
    assert result.total_income == 0
    assert result.transaction_count == 0
    assert result.monthly_totals == []
    assert result.by_vendor == []
    assert result.by_category == []
    assert result.month_over_month.current == 0
    assert result.month_over_month.previous == 0
    assert result.month_over_month.change_pct == 0


@pytest.mark.unit
def test_get_analytics_db_error():
    """Test get_analytics returns empty AnalyticsSummary on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB connection lost")
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_analytics()

    # Assert
    assert isinstance(result, AnalyticsSummary)
    assert result.total_expense == 0
    assert result.transaction_count == 0


@pytest.mark.unit
def test_get_analytics_happy_path():
    """Test get_analytics returns complete summary with data."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # Set up multiple responses
    fetchone_values = [
        (100.5, 50.0, 10),  # totals
        (150.0, 80.0),      # mom
    ]
    fetchall_values = [
        [],                       # monthly
        [('Tesco', 100.5)],       # by_vendor
        [('Groceries', 50.0)],    # by_category
    ]

    cursor.fetchone.side_effect = fetchone_values
    cursor.fetchall.side_effect = fetchall_values

    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_analytics()

    # Assert
    assert isinstance(result, AnalyticsSummary)
    assert result.total_expense == 100.5
    assert result.total_income == 50.0
    assert result.transaction_count == 10
    assert len(result.by_vendor) == 1
    assert result.by_vendor[0].vendor_name == 'Tesco'
    assert len(result.by_category) == 1
    assert result.by_category[0].name == 'Groceries'


@pytest.mark.unit
def test_get_analytics_with_date_range():
    """Test get_analytics applies custom date range."""
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.side_effect = [
        (100.0, 50.0, 5),
        (0, 0),
    ]
    cursor.fetchall.side_effect = [[], [], []]

    # Act
    repo.get_analytics(
        date_from='2026-01-01',
        date_to='2026-03-31'
    )

    # Assert
    # Verify that custom dates were passed to execute
    call_args_list = cursor.execute.call_args_list
    assert len(call_args_list) > 0
    # First call should have custom dates
    first_call_params = call_args_list[0][0][1]
    assert '2026-01-01' in first_call_params


@pytest.mark.unit
def test_get_analytics_monthly_totals():
    """Test get_analytics aggregates monthly expenses and income."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    monthly_data = [
        ('2026-03', 150.0, 50.0),
        ('2026-04', 200.0, 75.0),
    ]

    cursor.fetchone.side_effect = [
        (350.0, 125.0, 20),  # totals
        (200.0, 150.0),      # mom
    ]
    cursor.fetchall.side_effect = [
        monthly_data,  # monthly_rows
        [],            # by_vendor
        [],            # by_category
    ]

    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_analytics()

    # Assert
    assert len(result.monthly_totals) == 2
    assert result.monthly_totals[0].month == '2026-03'
    assert result.monthly_totals[0].expense == 150.0
    assert result.monthly_totals[0].income == 50.0
    assert result.monthly_totals[1].month == '2026-04'


@pytest.mark.unit
def test_get_analytics_month_over_month_calculation():
    """Test get_analytics calculates month-over-month change percentage."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    cursor.fetchone.side_effect = [
        (0, 0, 0),           # totals
        (200.0, 100.0),      # mom: current=200, previous=100 -> 100% increase
    ]
    cursor.fetchall.side_effect = [[], [], []]

    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_analytics()

    # Assert
    assert result.month_over_month.current == 200.0
    assert result.month_over_month.previous == 100.0
    assert result.month_over_month.change_pct == 100.0


@pytest.mark.unit
def test_get_analytics_month_over_month_zero_previous():
    """Test get_analytics MoM change_pct is 0 when previous month is 0."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    cursor.fetchone.side_effect = [
        (0, 0, 0),      # totals
        (150.0, 0),     # mom: current=150, previous=0
    ]
    cursor.fetchall.side_effect = [[], [], []]

    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_analytics()

    # Assert
    assert result.month_over_month.change_pct == 0.0


@pytest.mark.unit
def test_get_analytics_default_date_range():
    """Test get_analytics uses default date range when not specified."""
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.side_effect = [
        (0, 0, 0),
        (0, 0),
    ]
    cursor.fetchall.side_effect = [[], [], []]

    # Act
    repo.get_analytics()  # No date params

    # Assert
    # Verify that execute was called (dates were computed)
    assert cursor.execute.call_count > 0
