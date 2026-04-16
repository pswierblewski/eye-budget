import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.repositories.prompt_analytics import PromptAnalyticsRepository


class ConcretePromptAnalytics(PromptAnalyticsRepository):
    pass


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Build a PromptAnalyticsRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcretePromptAnalytics.__new__(ConcretePromptAnalytics)
    repo.conn = conn
    return repo, cursor


# ============================================================================
# upsert
# ============================================================================

@pytest.mark.unit
def test_upsert_happy_path():
    # Arrange
    repo, cursor = make_repo()
    details = {
        "category_corrections": [{"ai_category_name": "Food", "user_category_name": "Groceries"}],
        "product_name_corrections": [{"ai_normalized_name": "apple", "user_normalized_name": "apple pie"}],
    }

    # Act
    result = repo.upsert(
        scan_id=1,
        vendor_name="Aldi",
        category_corrections_count=1,
        product_name_corrections_count=1,
        ocr_product_count=5,
        confirmed_product_count=6,
        details=details,
    )

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT INTO prompt_analytics" in s and "ON CONFLICT" in s for s in sqls)


@pytest.mark.unit
def test_upsert_no_conn_returns_false():
    # Arrange
    repo = ConcretePromptAnalytics.__new__(ConcretePromptAnalytics)
    repo.conn = None
    details = {}

    # Act
    result = repo.upsert(
        scan_id=1,
        vendor_name="Aldi",
        category_corrections_count=0,
        product_name_corrections_count=0,
        ocr_product_count=5,
        confirmed_product_count=5,
        details=details,
    )

    # Assert
    assert result is False


@pytest.mark.unit
def test_upsert_db_error_returns_false_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB constraint error")
    details = {}

    # Act
    result = repo.upsert(
        scan_id=1,
        vendor_name="Aldi",
        category_corrections_count=0,
        product_name_corrections_count=0,
        ocr_product_count=5,
        confirmed_product_count=5,
        details=details,
    )

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_upsert_with_none_vendor_name():
    # Arrange
    repo, cursor = make_repo()
    details = {}

    # Act
    result = repo.upsert(
        scan_id=2,
        vendor_name=None,
        category_corrections_count=0,
        product_name_corrections_count=0,
        ocr_product_count=3,
        confirmed_product_count=3,
        details=details,
    )

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


# ============================================================================
# get_all
# ============================================================================

@pytest.mark.unit
def test_get_all_happy_path():
    # Arrange
    now = datetime(2026, 4, 16, 10, 30, 0)
    fetchall_return = [
        (1, 101, "Aldi", 2, 1, 5, 6, {"key": "value"}, now),
        (2, 102, "Lidl", 1, 0, 3, 3, {"key": "value2"}, now),
    ]
    repo, cursor = make_repo(fetchall_return=fetchall_return)

    # Act
    result = repo.get_all(limit=50, offset=0)

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert result[0]["id"] == 1
    assert result[0]["scan_id"] == 101
    assert result[0]["vendor_name"] == "Aldi"
    assert result[0]["category_corrections_count"] == 2
    assert result[0]["product_name_corrections_count"] == 1
    assert result[0]["ocr_product_count"] == 5
    assert result[0]["confirmed_product_count"] == 6
    assert result[0]["details"] == {"key": "value"}
    assert result[0]["created_at"] == now.isoformat()

    assert result[1]["id"] == 2
    assert result[1]["scan_id"] == 102
    assert result[1]["vendor_name"] == "Lidl"


@pytest.mark.unit
def test_get_all_empty():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_all(limit=50, offset=0)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_no_conn_returns_empty():
    # Arrange
    repo = ConcretePromptAnalytics.__new__(ConcretePromptAnalytics)
    repo.conn = None

    # Act
    result = repo.get_all(limit=50, offset=0)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_db_error_returns_empty():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all(limit=50, offset=0)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_with_pagination():
    # Arrange
    now = datetime(2026, 4, 16, 10, 30, 0)
    fetchall_return = [
        (3, 103, "Tesco", 0, 0, 2, 2, {}, now),
    ]
    repo, cursor = make_repo(fetchall_return=fetchall_return)

    # Act
    result = repo.get_all(limit=10, offset=20)

    # Assert
    assert len(result) == 1
    assert result[0]["id"] == 3
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("LIMIT %s OFFSET %s" in s for s in sqls)


@pytest.mark.unit
def test_get_all_handles_null_created_at():
    # Arrange
    fetchall_return = [
        (1, 101, "Aldi", 0, 0, 5, 5, {}, None),
    ]
    repo, cursor = make_repo(fetchall_return=fetchall_return)

    # Act
    result = repo.get_all(limit=50, offset=0)

    # Assert
    assert len(result) == 1
    assert result[0]["created_at"] is None


# ============================================================================
# delete_by_scan_id
# ============================================================================

@pytest.mark.unit
def test_delete_by_scan_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_by_scan_id(scan_id=101)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE FROM prompt_analytics WHERE scan_id = %s" in s for s in sqls)


@pytest.mark.unit
def test_delete_by_scan_id_no_conn_returns_false():
    # Arrange
    repo = ConcretePromptAnalytics.__new__(ConcretePromptAnalytics)
    repo.conn = None

    # Act
    result = repo.delete_by_scan_id(scan_id=101)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_by_scan_id_db_error_returns_false_and_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.delete_by_scan_id(scan_id=101)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_by_scan_id_nonexistent_record():
    # Arrange
    repo, cursor = make_repo()
    # DB doesn't raise error for non-existent DELETE, just returns 0 affected rows

    # Act
    result = repo.delete_by_scan_id(scan_id=999)

    # Assert
    assert result is True  # DELETE still "succeeds" even if no rows affected
    repo.conn.commit.assert_called_once()
