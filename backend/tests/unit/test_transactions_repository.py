import pytest
from datetime import date
from unittest.mock import MagicMock

from src.data import ReceiptTransaction, ReceiptTransactionItem
from src.repositories.transactions import TransactionsRepository


_UNSET = object()


class ConcreteTransactions(TransactionsRepository):
    """Minimal concrete subclass for testing the ABC."""
    pass


def make_repo(fetchone_return=_UNSET, fetchone_side_effect=None, fetchall_return=None):
    """Build a TransactionsRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    elif fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return

    cursor.fetchall.return_value = fetchall_return or []
    cursor.rowcount = 1  # default; tests can override

    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = conn
    return repo, cursor


# ============================================================================
# lookup_vendor_id tests
# ============================================================================

@pytest.mark.unit
def test_lookup_vendor_id_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(5,))

    # Act
    result = repo.lookup_vendor_id("LIDL Sp. z o.o.")

    # Assert
    assert result == 5
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_lookup_vendor_id_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.lookup_vendor_id("NonExistent Vendor")

    # Assert
    assert result is None
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_lookup_vendor_id_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.lookup_vendor_id("Any Vendor")

    # Assert
    assert result is None


@pytest.mark.unit
def test_lookup_vendor_id_db_error():
    # Arrange
    repo, _ = make_repo()
    repo.conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("DB error")

    # Act
    result = repo.lookup_vendor_id("Bad Vendor")

    # Assert
    assert result is None




# ============================================================================
# lookup_product_id tests
# ============================================================================

@pytest.mark.unit
def test_lookup_product_id_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(12,))

    # Act
    result = repo.lookup_product_id("Mleko 3.2% 1L")

    # Assert
    assert result == 12
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_lookup_product_id_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.lookup_product_id("NonExistent Product")

    # Assert
    assert result is None


@pytest.mark.unit
def test_lookup_product_id_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.lookup_product_id("Any Product")

    # Assert
    assert result is None


@pytest.mark.unit
def test_lookup_product_id_db_error():
    # Arrange
    repo, _ = make_repo()
    repo.conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("DB error")

    # Act
    result = repo.lookup_product_id("Bad Product")

    # Assert
    assert result is None


# ============================================================================
# create_transaction tests
# ============================================================================

@pytest.mark.unit
def test_create_transaction_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.create_transaction(
        scan_id=10,
        vendor_id=5,
        raw_vendor_name="LIDL",
        transaction_date=date(2026, 4, 15),
        total=99.50
    )

    # Assert
    assert result == 42
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_create_transaction_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.create_transaction(
        scan_id=10,
        vendor_id=None,
        raw_vendor_name="Unknown",
        transaction_date=date(2026, 4, 15),
        total=50.0
    )

    # Assert
    assert result == -1


@pytest.mark.unit
def test_create_transaction_db_error_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("INSERT failed")

    # Act
    result = repo.create_transaction(
        scan_id=10,
        vendor_id=5,
        raw_vendor_name="LIDL",
        transaction_date=date(2026, 4, 15),
        total=99.50
    )

    # Assert
    assert result == -1
    repo.conn.rollback.assert_called_once()


# ============================================================================
# create_transaction_item tests
# ============================================================================

@pytest.mark.unit
def test_create_transaction_item_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.create_transaction_item(
        transaction_id=42,
        product_id=12,
        raw_product_name="Mleko",
        category_id=3,
        quantity=2.0,
        unit_price=5.50,
        price=11.0
    )

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_create_transaction_item_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.create_transaction_item(
        transaction_id=42,
        product_id=None,
        raw_product_name="Chleb",
        category_id=3,
        quantity=1.0,
        unit_price=None,
        price=5.0
    )

    # Assert
    assert result is False


@pytest.mark.unit
def test_create_transaction_item_db_error_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("INSERT failed")

    # Act
    result = repo.create_transaction_item(
        transaction_id=42,
        product_id=12,
        raw_product_name="Mleko",
        category_id=3,
        quantity=1.0,
        unit_price=5.50,
        price=5.50
    )

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ============================================================================
# get_by_scan_id tests
# ============================================================================

@pytest.mark.unit
def test_get_by_scan_id_happy_path():
    # Arrange — fetchone returns tx_row, fetchall returns items
    tx_row = (
        42,                    # id
        5,                     # vendor_id
        "LIDL",                # raw_vendor_name
        "2026-04-15",          # date
        99.50,                 # total
        "Lidl"                 # normalized_vendor_name
    )
    item_rows = [
        (1, 12, "Mleko", 3, "2.0", "5.50", "11.0", "Milk"),
        (2, 13, "Chleb", 4, "1.0", None, "3.0", "Bread"),
    ]

    repo, _ = make_repo(
        fetchone_return=tx_row,
        fetchall_return=item_rows
    )

    # Act
    result = repo.get_by_scan_id(10)

    # Assert
    assert isinstance(result, ReceiptTransaction)
    assert result.id == 42
    assert result.vendor_id == 5
    assert result.raw_vendor_name == "LIDL"
    assert result.normalized_vendor_name == "Lidl"
    assert result.date == "2026-04-15"
    assert abs(result.total - 99.50) < 0.01
    assert len(result.items) == 2
    assert result.items[0].id == 1
    assert result.items[0].raw_product_name == "Mleko"
    assert result.items[0].normalized_product_name == "Milk"
    assert abs(result.items[0].quantity - 2.0) < 0.01
    assert abs(result.items[0].unit_price - 5.50) < 0.01
    assert abs(result.items[0].price - 11.0) < 0.01
    assert result.items[1].unit_price is None


@pytest.mark.unit
def test_get_by_scan_id_not_found():
    # Arrange — fetchone returns None (no transaction)
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_scan_id(999)

    # Assert
    assert result is None
    # Should only execute first query (for transaction)
    assert cursor.execute.call_count == 1


@pytest.mark.unit
def test_get_by_scan_id_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.get_by_scan_id(10)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_scan_id_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("SELECT failed")

    # Act
    result = repo.get_by_scan_id(10)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_scan_id_empty_items():
    # Arrange — transaction found but no items
    tx_row = (
        42, 5, "LIDL", "2026-04-15", 99.50, "Lidl"
    )
    repo, cursor = make_repo(
        fetchone_return=tx_row,
        fetchall_return=[]
    )

    # Act
    result = repo.get_by_scan_id(10)

    # Assert
    assert isinstance(result, ReceiptTransaction)
    assert result.id == 42
    assert len(result.items) == 0


# ============================================================================
# update_transaction_item tests
# ============================================================================

@pytest.mark.unit
def test_update_transaction_item_happy_path():
    # Arrange — update succeeds (rowcount=1), then refetch returns updated row
    updated_row = (
        1, 13, "Mleko", 5, "2.0", "6.0", "12.0", "Milk"
    )
    repo, cursor = make_repo(fetchone_return=updated_row)
    cursor.rowcount = 1

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"category_id": 5, "product_id": 13}
    )

    # Assert
    assert isinstance(result, ReceiptTransactionItem)
    assert result.id == 1
    assert result.category_id == 5
    assert result.product_id == 13
    assert result.normalized_product_name == "Milk"
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_update_transaction_item_rowcount_zero():
    # Arrange — update affects 0 rows (item not found)
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.update_transaction_item(
        item_id=999,
        fields={"category_id": 5}
    )

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_update_transaction_item_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"category_id": 5}
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_transaction_item_empty_fields():
    # Arrange — fields dict is empty
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = MagicMock()

    # Act
    result = repo.update_transaction_item(item_id=1, fields={})

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_transaction_item_no_allowed_fields():
    # Arrange — fields dict contains only disallowed keys
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = MagicMock()

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"id": 999, "transaction_id": 42}  # not in allowed set
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_transaction_item_db_error_and_rollback():
    # Arrange
    repo, _ = make_repo()
    repo.conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("UPDATE failed")

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"category_id": 5}
    )

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_update_transaction_item_filters_none_values():
    # Arrange — some fields are None and should be filtered out
    updated_row = (
        1, 12, "Mleko", 5, "2.0", None, "10.0", "Milk"
    )
    repo, cursor = make_repo(fetchone_return=updated_row)
    cursor.rowcount = 1

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"category_id": 5, "unit_price": None, "product_id": 12}
    )

    # Assert
    assert isinstance(result, ReceiptTransactionItem)
    # Verify that the SQL only updated allowed non-None fields
    execute_calls = cursor.execute.call_args_list
    assert len(execute_calls) == 2  # UPDATE + SELECT
    update_sql = execute_calls[0][0][0]
    assert "UPDATE" in update_sql
    assert "unit_price" not in update_sql  # None was filtered out


@pytest.mark.unit
def test_update_transaction_item_refetch_returns_none():
    # Arrange — update succeeds but refetch returns None (race condition)
    repo, cursor = make_repo(fetchone_return=None)
    cursor.rowcount = 1

    # Act
    result = repo.update_transaction_item(
        item_id=1,
        fields={"category_id": 5}
    )

    # Assert
    assert result is None
    # commit is called for UPDATE, but result is None because refetch failed
    repo.conn.commit.assert_called_once()


# ============================================================================
# delete_transaction_item tests
# ============================================================================

@pytest.mark.unit
def test_delete_transaction_item_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete_transaction_item(item_id=1)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_delete_transaction_item_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete_transaction_item(item_id=999)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_delete_transaction_item_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.delete_transaction_item(item_id=1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_transaction_item_db_error_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DELETE failed")

    # Act
    result = repo.delete_transaction_item(item_id=1)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ============================================================================
# delete_by_scan_id tests
# ============================================================================

@pytest.mark.unit
def test_delete_by_scan_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_by_scan_id(scan_id=10)

    # Assert
    assert result is True
    assert cursor.execute.call_count == 2  # items DELETE + transaction DELETE
    repo.conn.commit.assert_called_once()
    repo.conn.rollback.assert_not_called()


@pytest.mark.unit
def test_delete_by_scan_id_no_conn():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = None

    # Act
    result = repo.delete_by_scan_id(scan_id=10)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_by_scan_id_db_error_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DELETE failed")

    # Act
    result = repo.delete_by_scan_id(scan_id=10)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ============================================================================
# dispose tests
# ============================================================================

@pytest.mark.unit
def test_dispose_does_nothing():
    # Arrange
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = MagicMock()

    # Act
    repo.dispose()

    # Assert — should not raise, does nothing
