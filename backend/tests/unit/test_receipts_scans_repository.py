import pytest
from unittest.mock import MagicMock
from src.data import (
    ReceiptsScanStatus,
    TransactionModel,
    ReceiptScanListItem,
    ReceiptScanDetail,
    TextRegionsResult,
    ProductTextRegion,
)
from src.repositories.receipts_scans import ReceiptsScansRepository, ProcessedScan


# Concrete implementation for testing (ReceiptsScansRepository is ABC)
class ConcreteReceiptsScansRepository(ReceiptsScansRepository):
    """Concrete implementation of ReceiptsScansRepository for testing."""
    pass


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Build a ReceiptsScansRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []

    # instantiate via __new__ and inject conn
    repo = ConcreteReceiptsScansRepository.__new__(ConcreteReceiptsScansRepository)
    repo.conn = conn
    repo.table = 'receipts_scans'
    return repo, cursor


# ========================================================================
# add_receipt tests
# ========================================================================

@pytest.mark.unit
def test_add_receipt_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("test.jpg",))

    # Act
    result = repo.add_receipt("test.jpg")

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_add_receipt_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.add_receipt("test.jpg")

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_add_receipt_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.add_receipt("test.jpg")

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_add_receipt_already_exists():
    # Arrange — ON CONFLICT returns NULL
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.add_receipt("test.jpg")

    # Assert
    assert result is False
    repo.conn.commit.assert_called_once()


# ========================================================================
# set_status tests
# ========================================================================

@pytest.mark.unit
def test_set_status_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_status("test.jpg", ReceiptsScanStatus.PROCESSING)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_status_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_status("test.jpg", ReceiptsScanStatus.PROCESSING)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_status_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_status("test.jpg", ReceiptsScanStatus.FAILED, "Some error")

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_set_status_with_error_message():
    # Arrange
    repo, cursor = make_repo()
    error_msg = "OCR failed"

    # Act
    result = repo.set_status("test.jpg", ReceiptsScanStatus.FAILED, error_msg)

    # Assert
    assert result is True
    call_args = cursor.execute.call_args
    assert call_args[0][1][1] == error_msg


@pytest.mark.unit
def test_set_status_converts_exception_to_string():
    # Arrange
    repo, cursor = make_repo()
    exc = ValueError("Some error")

    # Act
    result = repo.set_status("test.jpg", ReceiptsScanStatus.FAILED, exc)

    # Assert
    assert result is True
    call_args = cursor.execute.call_args
    assert isinstance(call_args[0][1][1], str)
    assert "Some error" in call_args[0][1][1]


# ========================================================================
# set_category_candidates tests
# ========================================================================

@pytest.mark.unit
def test_set_category_candidates_happy_path():
    # Arrange
    repo, cursor = make_repo()
    candidates = {"product_name": "test", "candidates": []}

    # Act
    result = repo.set_category_candidates("test.jpg", candidates)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_category_candidates_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None
    candidates = {"product_name": "test"}

    # Act
    result = repo.set_category_candidates("test.jpg", candidates)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_category_candidates_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    candidates = {}

    # Act
    result = repo.set_category_candidates("test.jpg", candidates)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# set_result tests
# ========================================================================

@pytest.mark.unit
def test_set_result_happy_path():
    # Arrange
    repo, cursor = make_repo()
    result_data = {"vendor": "Lidl", "total": 100.50}

    # Act
    result = repo.set_result("test.jpg", result_data)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_result_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_result("test.jpg", {})

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_result_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_result("test.jpg", {"vendor": "Aldi"})

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# get_scan_id_by_filename tests
# ========================================================================

@pytest.mark.unit
def test_get_scan_id_by_filename_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.get_scan_id_by_filename("test.jpg")

    # Assert
    assert result == 42
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_scan_id_by_filename_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_scan_id_by_filename("nonexistent.jpg")

    # Assert
    assert result is None
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_scan_id_by_filename_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.get_scan_id_by_filename("test.jpg")

    # Assert
    assert result is None
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_scan_id_by_filename_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_scan_id_by_filename("test.jpg")

    # Assert
    assert result is None


# ========================================================================
# get_processed_scans tests
# ========================================================================

@pytest.mark.unit
def test_get_processed_scans_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", {"vendor": "Lidl", "date": "2025-01-01", "title": "PARAGON", "total": 50.0, "products": []}),
            (2, "scan2.jpg", {"vendor": "Aldi", "date": "2025-01-02", "title": "PARAGON", "total": 75.0, "products": []}),
        ]
    )

    # Act
    result = repo.get_processed_scans()

    # Assert
    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].filename == "scan1.jpg"
    assert result[1].id == 2
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_processed_scans_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.get_processed_scans()

    # Assert
    assert result == []
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_processed_scans_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_processed_scans()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_processed_scans_skips_invalid_models():
    # Arrange — one valid, one with invalid result
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", {"vendor": "Lidl", "date": "2025-01-01", "title": "PARAGON", "total": 50.0, "products": []}),
            (2, "scan2.jpg", {"invalid": "data"}),  # Missing required fields
        ]
    )

    # Act
    result = repo.get_processed_scans()

    # Assert
    assert len(result) == 1
    assert result[0].id == 1


# ========================================================================
# set_minio_key tests
# ========================================================================

@pytest.mark.unit
def test_set_minio_key_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_minio_key("test.jpg", "minio/key/test.jpg")

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_minio_key_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_minio_key("test.jpg", "minio/key/test.jpg")

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_minio_key_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_minio_key("test.jpg", "minio/key/test.jpg")

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# set_status_done tests
# ========================================================================

@pytest.mark.unit
def test_set_status_done_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_status_done(42)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_status_done_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_status_done(42)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_status_done_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_status_done(42)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# set_status_to_confirm_by_id tests
# ========================================================================

@pytest.mark.unit
def test_set_status_to_confirm_by_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_status_to_confirm_by_id(42)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_status_to_confirm_by_id_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_status_to_confirm_by_id(42)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_status_to_confirm_by_id_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_status_to_confirm_by_id(42)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# set_result_by_id tests
# ========================================================================

@pytest.mark.unit
def test_set_result_by_id_happy_path():
    # Arrange
    repo, cursor = make_repo()
    result_data = {"vendor": "Lidl", "total": 100.50}

    # Act
    result = repo.set_result_by_id(42, result_data)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_result_by_id_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.set_result_by_id(42, {})

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_result_by_id_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.set_result_by_id(42, {"vendor": "Aldi"})

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# get_all tests
# ========================================================================

@pytest.mark.unit
def test_get_all_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (1, "scan1.jpg", "processed", "Lidl", "2025-01-01", "50.0", ["tag1"], 100, True, 10),
            (2, "scan2.jpg", "to_confirm", "Aldi", "2025-01-02", "75.5", ["tag2"], None, False, 10),
        ]
    )

    # Act
    items, total = repo.get_all(limit=50, offset=0)

    # Assert
    assert len(items) == 2
    assert total == 10
    assert items[0].id == 1
    assert items[0].filename == "scan1.jpg"
    assert items[0].receipt_transaction_id == 100
    assert items[0].has_transaction_link is True
    assert items[1].receipt_transaction_id is None
    assert items[1].has_transaction_link is False
    assert items[1].id == 2
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_all_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    items, total = repo.get_all()

    # Assert
    assert items == []
    assert total == 0
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_all_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    items, total = repo.get_all()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_all_with_status_filter():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_all(status="processed")

    # Assert
    cursor.execute.assert_called_once()
    call_sql = cursor.execute.call_args[0][0]
    assert "status = %s" in call_sql


@pytest.mark.unit
def test_get_all_with_search_filter():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_all(search="Lidl")

    # Assert
    cursor.execute.assert_called_once()
    call_sql = cursor.execute.call_args[0][0]
    assert "ILIKE" in call_sql


@pytest.mark.unit
def test_get_all_with_tag_filter():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_all(tag="important")

    # Assert
    cursor.execute.assert_called_once()
    call_sql = cursor.execute.call_args[0][0]
    assert "tags" in call_sql


@pytest.mark.unit
def test_get_all_empty_result():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    items, total = repo.get_all()

    # Assert
    assert items == []
    assert total == 0


# ========================================================================
# get_status_counts tests
# ========================================================================

@pytest.mark.unit
def test_get_status_counts_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            ("processed", 10),
            ("to_confirm", 5),
            ("failed", 2),
        ]
    )

    # Act
    result = repo.get_status_counts()

    # Assert
    assert result == {"processed": 10, "to_confirm": 5, "failed": 2}
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_status_counts_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.get_status_counts()

    # Assert
    assert result == {}
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_status_counts_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_status_counts()

    # Assert
    assert result == {}


# ========================================================================
# get_by_id tests
# ========================================================================

@pytest.mark.unit
def test_get_by_id_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchone_return=(
            42,
            "test.jpg",
            "processed",
            {"vendor": "Lidl", "date": "2025-01-01", "title": "PARAGON", "total": 50.0, "products": []},
            None,  # categories_candidates
            "minio/key/test.jpg",
            ["tag1", "tag2"],
            None,  # text_regions
        )
    )

    # Act
    result = repo.get_by_id(42)

    # Assert
    assert result is not None
    assert result.id == 42
    assert result.filename == "test.jpg"
    assert result.status == "processed"
    assert result.minio_object_key == "minio/key/test.jpg"
    assert result.tags == ["tag1", "tag2"]
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_by_id_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_id(42)

    # Assert
    assert result is None
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_by_id_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.get_by_id(42)

    # Assert
    assert result is None
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_by_id_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_by_id(42)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_with_text_regions():
    # Arrange
    text_regions_data = {
        "image_width": 800,
        "image_height": 600,
        "product_regions": {"0": {"polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}}
    }
    repo, cursor = make_repo(
        fetchone_return=(
            42,
            "test.jpg",
            "processed",
            None,
            None,
            None,
            [],
            text_regions_data,
        )
    )

    # Act
    result = repo.get_by_id(42)

    # Assert
    assert result is not None
    assert result.text_regions is not None
    assert result.text_regions.image_width == 800


# ========================================================================
# delete_scan_by_id tests
# ========================================================================

@pytest.mark.unit
def test_delete_scan_by_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_scan_by_id(42)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_scan_by_id_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.delete_scan_by_id(42)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_delete_scan_by_id_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.delete_scan_by_id(42)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# reset_for_retry tests
# ========================================================================

@pytest.mark.unit
def test_reset_for_retry_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("test.jpg",))

    # Act
    result = repo.reset_for_retry(42)

    # Assert
    assert result == "test.jpg"
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_reset_for_retry_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.reset_for_retry(42)

    # Assert
    assert result is None
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_reset_for_retry_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.reset_for_retry(42)

    # Assert
    assert result is None
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_reset_for_retry_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.reset_for_retry(42)

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


# ========================================================================
# update_tags tests
# ========================================================================

@pytest.mark.unit
def test_update_tags_happy_path():
    # Arrange
    repo, cursor = make_repo()
    tags = ["tag1", "tag2", "tag3"]

    # Act
    result = repo.update_tags(42, tags)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_tags_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.update_tags(42, ["tag1"])

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_update_tags_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.update_tags(42, ["tag1"])

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_update_tags_empty_list():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.update_tags(42, [])

    # Assert
    assert result is True
    cursor.execute.assert_called_once()


# ========================================================================
# set_text_regions tests
# ========================================================================

@pytest.mark.unit
def test_set_text_regions_happy_path():
    # Arrange
    repo, cursor = make_repo()
    text_regions = TextRegionsResult(
        image_width=800,
        image_height=600,
        product_regions={"0": ProductTextRegion(polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])}
    )

    # Act
    result = repo.set_text_regions(42, text_regions)

    # Assert
    assert result is True
    cursor.execute.assert_called_once()
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_text_regions_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None
    text_regions = TextRegionsResult(
        image_width=800,
        image_height=600,
        product_regions={}
    )

    # Act
    result = repo.set_text_regions(42, text_regions)

    # Assert
    assert result is False
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_set_text_regions_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")
    text_regions = TextRegionsResult(
        image_width=800,
        image_height=600,
        product_regions={}
    )

    # Act
    result = repo.set_text_regions(42, text_regions)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


# ========================================================================
# get_tags_for_scan tests
# ========================================================================

@pytest.mark.unit
def test_get_tags_for_scan_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(["tag1", "tag2", "tag3"],))

    # Act
    result = repo.get_tags_for_scan(42)

    # Assert
    assert result == ["tag1", "tag2", "tag3"]
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_tags_for_scan_no_tags():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(None,))

    # Act
    result = repo.get_tags_for_scan(42)

    # Assert
    assert result == []
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_tags_for_scan_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_tags_for_scan(42)

    # Assert
    assert result == []
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_get_tags_for_scan_no_conn():
    # Arrange
    repo, cursor = make_repo()
    repo.conn = None

    # Act
    result = repo.get_tags_for_scan(42)

    # Assert
    assert result == []
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_tags_for_scan_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_tags_for_scan(42)

    # Assert
    assert result == []


# ========================================================================
# dispose tests
# ========================================================================

@pytest.mark.unit
def test_dispose():
    # Arrange
    repo, _ = make_repo()

    # Act
    repo.dispose()

    # Assert — dispose is a no-op
