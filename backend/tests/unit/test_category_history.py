import pytest
from unittest.mock import MagicMock

from src.repositories.category_history import CategoryHistoryRepository
from src.services.category_history import HistoryVerdict, dominant_category


def _repo(fetchall=None, fetchone=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    repo = CategoryHistoryRepository.__new__(CategoryHistoryRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_dominant_category_returns_verdict_above_thresholds():
    # Act
    verdict = dominant_category({1: ("Nabiał", 14), 2: ("Słodycze", 1)}, min_count=2, min_share=0.9)

    # Assert
    assert verdict == HistoryVerdict(1, "Nabiał", 14, pytest.approx(14 / 15))


@pytest.mark.unit
def test_dominant_category_none_when_count_too_low():
    # Act / Assert
    assert dominant_category({1: ("Nabiał", 1)}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_dominant_category_none_when_share_too_low():
    # Act / Assert
    assert dominant_category({1: ("Nabiał", 5), 2: ("Słodycze", 5)}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_dominant_category_none_for_empty_history():
    # Act / Assert
    assert dominant_category({}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_get_category_counts_groups_by_product():
    # Arrange
    repo, cursor = _repo(fetchall=[(10, 1, "Nabiał", 3), (10, 2, "Słodycze", 1), (11, 5, "Pieczywo", 2)])

    # Act
    result = repo.get_category_counts([10, 11])

    # Assert
    assert result == {10: {1: ("Nabiał", 3), 2: ("Słodycze", 1)}, 11: {5: ("Pieczywo", 2)}}
    sql, params = cursor.execute.call_args[0]
    assert "COALESCE(rti.product_id, pan.product)" in sql
    assert params == ([10, 11],)


@pytest.mark.unit
def test_get_category_counts_empty_ids_skips_query():
    # Arrange
    repo, cursor = _repo()

    # Act
    result = repo.get_category_counts([])

    # Assert
    assert result == {}
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_category_counts_db_error_rolls_back():
    # Arrange
    repo, cursor = _repo()
    cursor.execute.side_effect = Exception("boom")

    # Act
    result = repo.get_category_counts([1])

    # Assert
    assert result == {}
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_vendor_has_confirmed_receipts_true():
    # Arrange
    repo, _ = _repo(fetchone=(True,))

    # Act / Assert
    assert repo.vendor_has_confirmed_receipts(3) is True


@pytest.mark.unit
def test_vendor_has_confirmed_receipts_none_vendor_is_false():
    # Arrange
    repo, cursor = _repo()

    # Act / Assert
    assert repo.vendor_has_confirmed_receipts(None) is False
    cursor.execute.assert_not_called()
