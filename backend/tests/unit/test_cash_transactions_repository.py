"""
Unit tests for CashTransactionsRepository.
"""
import pytest
import datetime
from unittest.mock import MagicMock
from src.repositories.cash_transactions import CashTransactionsRepository
from src.data import CashTransactionListItem, CashTransactionDetail, ReceiptCategory

_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Factory to create a mocked CashTransactionsRepository."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn
    return repo, cursor


# ==============================================================================
# insert_transaction
# ==============================================================================

@pytest.mark.unit
def test_insert_transaction_happy_path():
    """Test successful insert of a new cash transaction."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))
    booking_date = datetime.date(2026, 4, 15)
    amount = 150.50
    description = "Groceries"
    category_id = 5
    vendor_id = 3

    # Act
    result = repo.insert_transaction(
        booking_date=booking_date,
        amount=amount,
        description=description,
        category_id=category_id,
        vendor_id=vendor_id,
    )

    # Assert
    assert result == 42
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_insert_transaction_no_conn():
    """Test insert_transaction returns None when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None
    booking_date = datetime.date(2026, 4, 15)

    # Act
    result = repo.insert_transaction(
        booking_date=booking_date,
        amount=100.0,
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_insert_transaction_db_error():
    """Test insert_transaction rolls back on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.insert_transaction(
        booking_date=datetime.date(2026, 4, 15),
        amount=100.0,
    )

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_insert_transaction_fetchone_returns_none():
    """Test insert_transaction returns None when fetchone returns None."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.insert_transaction(
        booking_date=datetime.date(2026, 4, 15),
        amount=100.0,
    )

    # Assert
    assert result is None
    repo.conn.commit.assert_called_once()


# ==============================================================================
# update
# ==============================================================================

@pytest.mark.unit
def test_update_happy_path():
    """Test successful update of a cash transaction."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42
    amount = 200.0

    # Act
    result = repo.update(tx_id=tx_id, amount=amount)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()
    call_args = cursor.execute.call_args
    assert "UPDATE cash_transactions SET" in call_args[0][0]
    assert amount in call_args[0][1]


@pytest.mark.unit
def test_update_no_conn():
    """Test update returns False when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.update(tx_id=42, amount=100.0)

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_db_error():
    """Test update rolls back on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.update(tx_id=42, amount=100.0)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_update_no_fields_provided():
    """Test update returns True early when no fields provided."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42

    # Act
    result = repo.update(tx_id=tx_id)

    # Assert
    assert result is True
    cursor.execute.assert_not_called()
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_update_multiple_fields():
    """Test update with multiple fields."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42
    booking_date = datetime.date(2026, 4, 15)
    amount = 200.0
    description = "Updated"

    # Act
    result = repo.update(
        tx_id=tx_id,
        booking_date=booking_date,
        amount=amount,
        description=description,
    )

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    call_args = cursor.execute.call_args
    assert "booking_date = %s" in call_args[0][0]
    assert "amount = %s" in call_args[0][0]
    assert "description = %s" in call_args[0][0]


# ==============================================================================
# update_category
# ==============================================================================

@pytest.mark.unit
def test_update_category_happy_path():
    """Test successful category update."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42
    category_id = 7

    # Act
    repo.update_category(tx_id=tx_id, category_id=category_id)

    # Assert
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_update_category_no_conn():
    """Test update_category returns early when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.update_category(tx_id=42, category_id=7)

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_category_db_error():
    """Test update_category rolls back on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    repo.update_category(tx_id=42, category_id=7)

    # Assert
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_update_category_clear_category():
    """Test update_category with None clears the category."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42

    # Act
    repo.update_category(tx_id=tx_id, category_id=None)

    # Assert
    repo.conn.commit.assert_called_once()
    call_args = cursor.execute.call_args
    assert call_args[0][1] == (None, tx_id)


# ==============================================================================
# delete
# ==============================================================================

@pytest.mark.unit
def test_delete_happy_path():
    """Test successful deletion of a cash transaction."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42

    # Act
    result = repo.delete(tx_id=tx_id)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_delete_no_conn():
    """Test delete returns False when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.delete(tx_id=42)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_db_error():
    """Test delete rolls back on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.delete(tx_id=42)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ==============================================================================
# update_tags
# ==============================================================================

@pytest.mark.unit
def test_update_tags_happy_path():
    """Test successful tags update."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42
    tags = ["food", "groceries"]

    # Act
    result = repo.update_tags(tx_id=tx_id, tags=tags)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_update_tags_no_conn():
    """Test update_tags returns False when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.update_tags(tx_id=42, tags=["tag"])

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_tags_db_error():
    """Test update_tags rolls back on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.update_tags(tx_id=42, tags=["tag"])

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_update_tags_empty_list():
    """Test update_tags with empty list."""
    # Arrange
    repo, cursor = make_repo()
    tx_id = 42

    # Act
    result = repo.update_tags(tx_id=tx_id, tags=[])

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


# ==============================================================================
# get_tags_for_tx
# ==============================================================================

@pytest.mark.unit
def test_get_tags_for_tx_happy_path():
    """Test successful retrieval of tags for a transaction."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(["food", "groceries"],))
    tx_id = 42

    # Act
    result = repo.get_tags_for_tx(tx_id=tx_id)

    # Assert
    assert result == ["food", "groceries"]
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_tags_for_tx_no_conn():
    """Test get_tags_for_tx returns empty list when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.get_tags_for_tx(tx_id=42)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_tags_for_tx_no_row():
    """Test get_tags_for_tx returns empty list when no row found."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_tags_for_tx(tx_id=42)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_tags_for_tx_db_error():
    """Test get_tags_for_tx returns empty list on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_tags_for_tx(tx_id=42)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_tags_for_tx_none_tags():
    """Test get_tags_for_tx when tags column is None."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(None,))

    # Act
    result = repo.get_tags_for_tx(tx_id=42)

    # Assert
    assert result == []


# ==============================================================================
# get_list
# ==============================================================================

@pytest.mark.unit
def test_get_list_happy_path():
    """Test successful retrieval of cash transactions list."""
    # Arrange
    booking_date = datetime.date(2026, 4, 15)
    # Row tuple must match get_list SELECT (indices 0-14)
    row = (
        1,                                  # 0: ct.id
        booking_date,                       # 1: ct.booking_date
        "Groceries",                        # 2: ct.description
        150.50,                             # 3: ct.amount
        "PLN",                              # 4: ct.currency
        "manual",                           # 5: ct.source
        5,                                  # 6: ct.category_id
        "Food",                             # 7: c.name (category_name)
        3,                                  # 8: ct.vendor_id
        "Lidl",                             # 9: v.name (vendor_name)
        ["food", "groceries"],              # 10: ct.tags
        "Groceries / Food",                 # 11: receipt_category_name
        2,                                  # 12: receipt_category_count
        None,                               # 13: settlement_group_id
        1,                                  # 14: total_count (COUNT(*) OVER ())
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list(limit=50, offset=0)

    # Assert
    assert total == 1
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CashTransactionListItem)
    assert item.id == 1
    assert item.amount == 150.50
    assert item.category_name == "Food"
    assert item.tags == ["food", "groceries"]


@pytest.mark.unit
def test_get_list_no_conn():
    """Test get_list returns empty list when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    items, total = repo.get_list()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_list_db_error_propagates():
    """Test get_list re-raises on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act / Assert
    with pytest.raises(Exception, match="DB error"):
        repo.get_list()


@pytest.mark.unit
def test_get_list_empty_result():
    """Test get_list with no rows returned."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    items, total = repo.get_list()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_list_with_tag_filter():
    """Test get_list with tag filter."""
    # Arrange
    row = (
        1, datetime.date(2026, 4, 15), "Groceries", 150.50, "PLN", "manual",
        5, "Food", 3, "Lidl", ["food"], "Groceries / Food", 1, None, 1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list(tag="food")

    # Assert
    assert total == 1
    call_args = cursor.execute.call_args
    assert "%s = ANY(ct.tags)" in call_args[0][0]
    assert "food" in call_args[0][1]


@pytest.mark.unit
def test_get_list_with_sort():
    """Test get_list with sort parameters."""
    # Arrange
    row = (
        1, datetime.date(2026, 4, 15), "Groceries", 150.50, "PLN", "manual",
        5, "Food", 3, "Lidl", [], None, None, None, 1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list(sort_by="amount", sort_dir="asc")

    # Assert
    call_args = cursor.execute.call_args
    assert "ct.amount" in call_args[0][0]
    assert "ASC" in call_args[0][0]


@pytest.mark.unit
def test_get_list_null_tags():
    """Test get_list when tags are None."""
    # Arrange
    row = (
        1, datetime.date(2026, 4, 15), "Groceries", 150.50, "PLN", "manual",
        5, "Food", 3, "Lidl", None, None, None, None, 1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list()

    # Assert
    assert len(items) == 1
    assert items[0].tags == []


@pytest.mark.unit
def test_get_list_null_receipt_category_count():
    """Test get_list when receipt_category_count is None."""
    # Arrange
    row = (
        1, datetime.date(2026, 4, 15), "Groceries", 150.50, "PLN", "manual",
        5, "Food", 3, "Lidl", [], None, None, None, 1,
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list()

    # Assert
    assert items[0].receipt_category_count is None


# ==============================================================================
# get_by_id
# ==============================================================================

@pytest.mark.unit
def test_get_by_id_happy_path():
    """Test successful retrieval of cash transaction detail."""
    # Arrange
    booking_date = datetime.date(2026, 4, 15)
    main_row = (
        42,                         # 0: ct.id
        booking_date,               # 1: ct.booking_date
        "Groceries",                # 2: ct.description
        150.50,                     # 3: ct.amount
        "PLN",                      # 4: ct.currency
        "manual",                   # 5: ct.source
        5,                          # 6: ct.category_id
        "Food",                     # 7: c.name (category_name)
        3,                          # 8: ct.vendor_id
        "Lidl",                     # 9: v.name (vendor_name)
        None,                       # 10: settlement_group_id
        ["food"],                   # 11: ct.tags
        10,                         # 12: ct.receipt_scan_id
    )
    category_row = (7, "Groceries / Food", 5)

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.side_effect = [main_row, None]
    cursor.fetchall.return_value = [category_row]

    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_by_id(tx_id=42)

    # Assert
    assert result is not None
    assert isinstance(result, CashTransactionDetail)
    assert result.id == 42
    assert result.amount == 150.50
    assert result.category_name == "Food"
    assert result.tags == ["food"]
    assert result.receipt_scan_id == 10


@pytest.mark.unit
def test_get_by_id_no_conn():
    """Test get_by_id returns None when no connection."""
    # Arrange
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = None

    # Act
    result = repo.get_by_id(tx_id=42)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_not_found():
    """Test get_by_id returns None when transaction not found."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_id(tx_id=42)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_db_error_propagates():
    """Test get_by_id re-raises on DB error."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act / Assert
    with pytest.raises(Exception, match="DB error"):
        repo.get_by_id(tx_id=42)


@pytest.mark.unit
def test_get_by_id_with_receipt_categories():
    """Test get_by_id populates receipt_categories."""
    # Arrange
    booking_date = datetime.date(2026, 4, 15)
    main_row = (
        42, booking_date, "Groceries", 150.50, "PLN", "manual",
        5, "Food", 3, "Lidl", None, ["food"], 10,
    )
    category_rows = [
        (7, "Groceries / Food", 5),
        (8, "Beverages / Coffee", 3),
    ]

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = main_row
    cursor.fetchall.return_value = category_rows

    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn

    # Act
    result = repo.get_by_id(tx_id=42)

    # Assert
    assert result is not None
    assert result.receipt_categories is not None
    assert len(result.receipt_categories) == 2
    assert result.receipt_categories[0].id == 7
    assert result.receipt_categories[0].product_count == 5
