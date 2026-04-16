import pytest
from unittest.mock import MagicMock
from src.data import VendorItem, VendorMapping
from src.repositories.vendors import VendorsRepository


class ConcreteVendors(VendorsRepository):
    pass


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchone_side_effect=None, fetchall_return=None):
    """Build a VendorsRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    elif fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = conn
    return repo, cursor


# ============================================================================
# get_all_vendors
# ============================================================================

@pytest.mark.unit
def test_get_all_vendors_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, "Aldi"), (2, "Lidl"), (3, "Tesco")])

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert len(result) == 3
    assert isinstance(result[0], VendorItem)
    assert result[0].id == 1
    assert result[0].name == "Aldi"
    assert result[1].id == 2
    assert result[1].name == "Lidl"
    assert result[2].id == 3
    assert result[2].name == "Tesco"


@pytest.mark.unit
def test_get_all_vendors_empty():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_vendors_no_conn_returns_empty():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_vendors_db_error_returns_empty():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert result == []


# ============================================================================
# insert_vendor
# ============================================================================

@pytest.mark.unit
def test_insert_vendor_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.insert_vendor("Aldi")

    # Assert
    assert result == 42
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "vendors" in s for s in sqls)


@pytest.mark.unit
def test_insert_vendor_no_result():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.insert_vendor("Aldi")

    # Assert
    assert result is None
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_insert_vendor_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_vendor("Aldi")

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_insert_vendor_no_conn_returns_none():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.insert_vendor("Aldi")

    # Assert
    assert result is None


# ============================================================================
# get_vendor_by_name
# ============================================================================

@pytest.mark.unit
def test_get_vendor_by_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(7,))

    # Act
    result = repo.get_vendor_by_name("Aldi")

    # Assert
    assert result == 7


@pytest.mark.unit
def test_get_vendor_by_name_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_vendor_by_name("UnknownVendor")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_vendor_by_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.get_vendor_by_name("Aldi")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_vendor_by_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_vendor_by_name("Aldi")

    # Assert
    assert result is None


# ============================================================================
# get_vendor_by_alternative_name
# ============================================================================

@pytest.mark.unit
def test_get_vendor_by_alternative_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(3,))

    # Act
    result = repo.get_vendor_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result == 3


@pytest.mark.unit
def test_get_vendor_by_alternative_name_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_vendor_by_alternative_name("UNKNOWN_VENDOR")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_vendor_by_alternative_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.get_vendor_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_vendor_by_alternative_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_vendor_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result is None


# ============================================================================
# get_normalized_name_by_alternative_name
# ============================================================================

@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("Aldi",))

    # Act
    result = repo.get_normalized_name_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result == "Aldi"


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_normalized_name_by_alternative_name("UNKNOWN_VENDOR")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.get_normalized_name_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_normalized_name_by_alternative_name("ALDI Sp. z o.o.")

    # Assert
    assert result is None


# ============================================================================
# insert_alternative_name
# ============================================================================

@pytest.mark.unit
def test_insert_alternative_name_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.insert_alternative_name("ALDI Sp. z o.o.", 7)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "vendors_alternative_names" in s for s in sqls)


@pytest.mark.unit
def test_insert_alternative_name_conflict_returns_false():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.insert_alternative_name("ALDI Sp. z o.o.", 7)

    # Assert
    assert result is False
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_insert_alternative_name_db_error_returns_false():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_alternative_name("ALDI Sp. z o.o.", 7)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_insert_alternative_name_no_conn_returns_false():
    # Arrange
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = None

    # Act
    result = repo.insert_alternative_name("ALDI Sp. z o.o.", 7)

    # Assert
    assert result is False
