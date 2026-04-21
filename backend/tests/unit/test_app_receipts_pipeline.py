"""Unit tests for App receipt scan pipeline (production run, detail, images, ground truth, localization)."""
import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_run_production_already_added_file():
    """File already in DB (add_receipt returns False/falsy) → printed, not in new_files."""
    # Arrange
    app = make_app()
    app.files_repository.list_input_files.return_value = ["old.jpg"]
    app.receipts_scans_repository.add_receipt.return_value = False

    # Act
    app._run_production()

    # Assert — no files to process, _process_single_file never called
    app.preprocessing_service.preprocess_image.assert_not_called()


@pytest.mark.unit
def test_run_production_calls_on_progress():
    """on_progress callback is called after processing each file."""
    # Arrange
    app = make_app()
    app.files_repository.list_input_files.return_value = ["img.jpg"]
    app.receipts_scans_repository.add_receipt.return_value = True
    app.preprocessing_service.preprocess_image.side_effect = Exception("skip")
    callback = MagicMock()

    # Act
    app._run_production(on_progress=callback)

    # Assert
    callback.assert_called_once()


@pytest.mark.unit
def test_get_receipt_by_id_with_transaction_and_bank_link():
    # Arrange
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx_model = TransactionModel(
        vendor="Shop", title="PARAGON", date="2024-01-01", total=10.0, products=[]
    )
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx_model)
    app.receipts_scans_repository.get_by_id.return_value = scan
    tx_mock = MagicMock()
    tx_mock.id = 42
    app.transactions_repository.get_by_scan_id.return_value = tx_mock
    app.bank_receipt_links_repository.get_bank_link_info.return_value = {
        "bank_transaction_id": 10,
        "counterparty": "Store",
        "booking_date": "2024-01-01",
        "amount": -10.0,
    }
    app.cash_receipt_links_repository.get_cash_link_info.return_value = None
    app.cash_receipt_links_repository.find_cash_tx_candidates.return_value = []

    # Act
    result = app.get_receipt_by_id(1)

    # Assert
    assert result is not None
    assert result.bank_link is not None


@pytest.mark.unit
def test_get_receipt_by_id_with_transaction_and_cash_link():
    # Arrange
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx_model = TransactionModel(
        vendor="Shop", title="PARAGON", date="2024-01-01", total=5.0, products=[]
    )
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx_model)
    app.receipts_scans_repository.get_by_id.return_value = scan
    tx_mock = MagicMock()
    tx_mock.id = 42
    app.transactions_repository.get_by_scan_id.return_value = tx_mock
    app.bank_receipt_links_repository.get_bank_link_info.return_value = None
    app.bank_receipt_links_repository.find_bank_tx_candidates.return_value = []
    app.cash_receipt_links_repository.get_cash_link_info.return_value = {
        "cash_transaction_id": 7,
        "description": None,
        "booking_date": "2024-01-01",
        "amount": -5.0,
    }

    # Act
    result = app.get_receipt_by_id(1)

    # Assert
    assert result is not None
    assert result.cash_link is not None


@pytest.mark.unit
def test_get_receipt_by_id_counts_candidates():
    # Arrange
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx_model = TransactionModel(
        vendor="Shop", title="PARAGON", date="2024-01-01", total=5.0, products=[]
    )
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx_model)
    app.receipts_scans_repository.get_by_id.return_value = scan
    tx_mock = MagicMock()
    tx_mock.id = 42
    app.transactions_repository.get_by_scan_id.return_value = tx_mock
    app.bank_receipt_links_repository.get_bank_link_info.return_value = None
    app.bank_receipt_links_repository.find_bank_tx_candidates.return_value = [MagicMock(), MagicMock()]
    app.cash_receipt_links_repository.get_cash_link_info.return_value = None
    app.cash_receipt_links_repository.find_cash_tx_candidates.return_value = [MagicMock()]

    # Act
    result = app.get_receipt_by_id(1)

    # Assert
    assert result.bank_candidate_count == 2
    assert result.cash_candidate_count == 1


@pytest.mark.unit
def test_get_receipt_image_url_returns_url_when_key_exists():
    # Arrange
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(
        id=1, filename="f.jpg", status="done", minio_object_key="receipts/1.jpg"
    )
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.minio_service.get_presigned_url.return_value = "http://minio/receipt.jpg"

    # Act
    result = app.get_receipt_image_url(1)

    # Assert
    assert result == "http://minio/receipt.jpg"
    app.minio_service.get_presigned_url.assert_called_once_with("receipts/1.jpg", expires_sec=3600)


@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_scan_missing():
    # Arrange
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None

    # Act / Assert
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_preprocessing_fails():
    # Arrange
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.side_effect = Exception("fail")

    # Act / Assert
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_upload_fails(tmp_path):
    # Arrange
    from src.data import ReceiptScanDetail
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="test.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.return_value = str(img)
    app.minio_service.upload_image.side_effect = Exception("upload fail")

    # Act / Assert
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_success(tmp_path):
    # Arrange
    from src.data import ReceiptScanDetail
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="test.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.return_value = str(img)

    # Act
    result = app.reupload_receipt_image(1)

    # Assert
    assert result is True
    app.receipts_scans_repository.set_minio_key.assert_called_once()


@pytest.mark.unit
def test_get_ground_truth_image_bytes_returns_none_when_missing():
    # Arrange
    app = make_app()
    app.ground_truth_repository.get_by_id.return_value = None

    # Act
    result = app.get_ground_truth_image_bytes(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_ground_truth_image_bytes_downloads():
    # Arrange
    app = make_app()
    entry = MagicMock()
    entry.minio_object_key = "gt/1.jpg"
    app.ground_truth_repository.get_by_id.return_value = entry
    app.minio_service.download_image.return_value = b"imgdata"

    # Act
    result = app.get_ground_truth_image_bytes(1)

    # Assert
    assert result == b"imgdata"
    app.minio_service.download_image.assert_called_once_with("gt/1.jpg")


@pytest.mark.unit
def test_localize_receipt_raises_404_when_scan_missing():
    # Arrange
    from fastapi import HTTPException
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        app.localize_receipt(1)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_localize_receipt_raises_404_when_no_minio_key():
    # Arrange
    from fastapi import HTTPException
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx = TransactionModel(vendor="V", title="P", date="2024-01-01", total=1.0, products=[])
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx, minio_object_key=None)
    app.receipts_scans_repository.get_by_id.return_value = scan

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        app.localize_receipt(1)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_localize_receipt_success():
    # Arrange
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx = TransactionModel(vendor="V", title="P", date="2024-01-01", total=1.0, products=[])
    scan = ReceiptScanDetail(
        id=1, filename="f.jpg", status="done", result=tx, minio_object_key="receipts/1.jpg"
    )
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.minio_service.download_image.return_value = b"\xff\xd8\xff"
    expected_result = MagicMock()
    app.text_localization_service.detect.return_value = MagicMock()
    app.text_matching_service.match.return_value = expected_result
    app.receipts_scans_repository.set_text_regions.return_value = None

    # Act
    result = app.localize_receipt(1)

    # Assert
    assert result is expected_result
    app.minio_service.download_image.assert_called_once_with("receipts/1.jpg")
