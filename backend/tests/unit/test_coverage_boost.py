"""
Additional targeted tests to push src/app.py coverage above the 80% gate.
Covers branches and methods not reached by earlier test modules.
"""
import pytest
from unittest.mock import MagicMock, patch
from tests.unit.conftest import make_app


# ---------------------------------------------------------------------------
# _run_production: already-seen file path (line 274) + on_progress (line 282)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_production_already_added_file():
    """File already in DB (add_receipt returns False/falsy) → printed, not in new_files."""
    app = make_app()
    app.files_repository.list_input_files.return_value = ["old.jpg"]
    app.receipts_scans_repository.add_receipt.return_value = False
    app._run_production()
    # No files to process — _process_single_file never called
    app.preprocessing_service.preprocess_image.assert_not_called()


@pytest.mark.unit
def test_run_production_calls_on_progress():
    """on_progress callback is called after processing each file."""
    app = make_app()
    app.files_repository.list_input_files.return_value = ["img.jpg"]
    app.receipts_scans_repository.add_receipt.return_value = True
    # Make _process_single_file succeed quickly via preprocessing side_effect
    app.preprocessing_service.preprocess_image.side_effect = Exception("skip")

    callback = MagicMock()
    app._run_production(on_progress=callback)
    callback.assert_called_once()


# ---------------------------------------------------------------------------
# get_receipt_by_id: transaction present → bank_link + candidate counts
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_by_id_with_transaction_and_bank_link():
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

    # Simulate bank link present
    app.bank_receipt_links_repository.get_bank_link_info.return_value = {
        "bank_transaction_id": 10,
        "counterparty": "Store",
        "booking_date": "2024-01-01",
        "amount": -10.0,
    }
    # Simulate no cash link
    app.cash_receipt_links_repository.get_cash_link_info.return_value = None
    app.cash_receipt_links_repository.find_cash_tx_candidates.return_value = []

    result = app.get_receipt_by_id(1)
    assert result is not None
    assert result.bank_link is not None


@pytest.mark.unit
def test_get_receipt_by_id_with_transaction_and_cash_link():
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

    # No bank link
    app.bank_receipt_links_repository.get_bank_link_info.return_value = None
    app.bank_receipt_links_repository.find_bank_tx_candidates.return_value = []
    # Cash link present
    app.cash_receipt_links_repository.get_cash_link_info.return_value = {
        "cash_transaction_id": 7,
        "description": None,
        "booking_date": "2024-01-01",
        "amount": -5.0,
    }

    result = app.get_receipt_by_id(1)
    assert result is not None
    assert result.cash_link is not None


@pytest.mark.unit
def test_get_receipt_by_id_counts_candidates():
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

    # No links → count candidates
    app.bank_receipt_links_repository.get_bank_link_info.return_value = None
    app.bank_receipt_links_repository.find_bank_tx_candidates.return_value = [MagicMock(), MagicMock()]
    app.cash_receipt_links_repository.get_cash_link_info.return_value = None
    app.cash_receipt_links_repository.find_cash_tx_candidates.return_value = [MagicMock()]

    result = app.get_receipt_by_id(1)
    assert result.bank_candidate_count == 2
    assert result.cash_candidate_count == 1


# ---------------------------------------------------------------------------
# get_receipt_image_url: minio_object_key present (line 515)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_image_url_returns_url_when_key_exists():
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(
        id=1, filename="f.jpg", status="done", minio_object_key="receipts/1.jpg"
    )
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.minio_service.get_presigned_url.return_value = "http://minio/receipt.jpg"
    result = app.get_receipt_image_url(1)
    assert result == "http://minio/receipt.jpg"
    app.minio_service.get_presigned_url.assert_called_once_with("receipts/1.jpg", expires_sec=3600)


# ---------------------------------------------------------------------------
# reupload_receipt_image (lines 527-544)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_scan_missing():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_preprocessing_fails():
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.side_effect = Exception("fail")
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_returns_false_when_upload_fails(tmp_path):
    from src.data import ReceiptScanDetail
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="test.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.return_value = str(img)
    app.minio_service.upload_image.side_effect = Exception("upload fail")
    assert app.reupload_receipt_image(1) is False


@pytest.mark.unit
def test_reupload_receipt_image_success(tmp_path):
    from src.data import ReceiptScanDetail
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="test.jpg", status="done")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.preprocessing_service.preprocess_image.return_value = str(img)
    result = app.reupload_receipt_image(1)
    assert result is True
    app.receipts_scans_repository.set_minio_key.assert_called_once()


# ---------------------------------------------------------------------------
# get_ground_truth_image_bytes (lines 548-551)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_ground_truth_image_bytes_returns_none_when_missing():
    app = make_app()
    app.ground_truth_repository.get_by_id.return_value = None
    result = app.get_ground_truth_image_bytes(1)
    assert result is None


@pytest.mark.unit
def test_get_ground_truth_image_bytes_downloads():
    app = make_app()
    entry = MagicMock()
    entry.minio_object_key = "gt/1.jpg"
    app.ground_truth_repository.get_by_id.return_value = entry
    app.minio_service.download_image.return_value = b"imgdata"
    result = app.get_ground_truth_image_bytes(1)
    assert result == b"imgdata"
    app.minio_service.download_image.assert_called_once_with("gt/1.jpg")


# ---------------------------------------------------------------------------
# confirm_receipt: vendor/date/total overrides + normalized_vendor (576-631)
# ---------------------------------------------------------------------------

def _make_scan_with_result():
    from src.data import ReceiptScanDetail, TransactionModel, ProductItem
    tx_model = TransactionModel(
        vendor="Raw Vendor",
        title="PARAGON",
        date="2024-06-15",
        total=20.0,
        products=[ProductItem(name="Apple", quantity=1, price=2.0)],
    )
    return ReceiptScanDetail(id=1, filename="f.jpg", status="to_confirm", result=tx_model)


@pytest.mark.unit
def test_confirm_receipt_returns_none_when_no_scan():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(product_categories={})
    result = app.confirm_receipt(1, req)
    assert result is None


@pytest.mark.unit
def test_confirm_receipt_returns_none_when_transaction_create_fails():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = _make_scan_with_result()
    app.transactions_repository.create_transaction.return_value = -1
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(product_categories={"Apple": 1})
    result = app.confirm_receipt(1, req)
    assert result is None


@pytest.mark.unit
def test_confirm_receipt_applies_vendor_override():
    app = make_app()
    scan = _make_scan_with_result()
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 99
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(product_categories={"Apple": 1}, vendor="Override Vendor")
    app.confirm_receipt(1, req)
    # set_result_by_id should have been called because override was applied
    app.receipts_scans_repository.set_result_by_id.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_normalized_vendor_path():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = _make_scan_with_result()
    app.transactions_repository.create_transaction.return_value = 99
    app.vendors_repository.get_vendor_by_name.return_value = None
    app.vendors_repository.insert_vendor.return_value = 5
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(
        product_categories={"Apple": 1},
        normalized_vendor="Normal Vendor",
    )
    app.confirm_receipt(1, req)
    app.vendors_repository.insert_vendor.assert_called_once_with("Normal Vendor")
    app.vendors_repository.insert_alternative_name.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_normalized_vendor_already_exists():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = _make_scan_with_result()
    app.transactions_repository.create_transaction.return_value = 99
    app.vendors_repository.get_vendor_by_name.return_value = 3  # already exists
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(
        product_categories={"Apple": 1},
        normalized_vendor="Normal Vendor",
    )
    app.confirm_receipt(1, req)
    app.vendors_repository.insert_vendor.assert_not_called()
    app.vendors_repository.insert_alternative_name.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_normalized_product_path():
    """normalized_products triggers look-up/insert path for product_id."""
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = _make_scan_with_result()
    app.transactions_repository.create_transaction.return_value = 99
    app.products_repository.get_product_by_name.return_value = None
    app.products_repository.insert_product.return_value = 11
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(
        product_categories={"Apple": 1},
        normalized_products={"Apple": "Apple Normalized"},
    )
    app.confirm_receipt(1, req)
    app.products_repository.insert_product.assert_called_once_with("Apple Normalized")
    app.products_repository.insert_alternative_name.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_date_parse_failure():
    """Invalid date string → today's date used without crash."""
    from src.data import ReceiptScanDetail, TransactionModel, ProductItem
    app = make_app()
    tx_model = TransactionModel(
        vendor="Shop", title="PARAGON", date="NOT-A-DATE", total=5.0,
        products=[ProductItem(name="Item", quantity=1, price=5.0)],
    )
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="to_confirm", result=tx_model)
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 99
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    req = ConfirmReceiptRequest(product_categories={"Item": 1})
    # Should not raise
    app.confirm_receipt(1, req)
    app.transactions_repository.create_transaction.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_product_with_no_category_skipped():
    """Product not in product_categories dict → continue (line 631)."""
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = _make_scan_with_result()
    app.transactions_repository.create_transaction.return_value = 99
    app.transactions_repository.get_by_scan_id.return_value = None
    from src.data import ConfirmReceiptRequest
    # Apple has no category mapped
    req = ConfirmReceiptRequest(product_categories={})
    app.confirm_receipt(1, req)
    app.transactions_repository.create_transaction_item.assert_not_called()


# ---------------------------------------------------------------------------
# localize_receipt (lines 838-861)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_localize_receipt_raises_404_when_scan_missing():
    from fastapi import HTTPException
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        app.localize_receipt(1)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_localize_receipt_raises_404_when_no_minio_key():
    from fastapi import HTTPException
    from src.data import ReceiptScanDetail, TransactionModel
    app = make_app()
    tx = TransactionModel(vendor="V", title="P", date="2024-01-01", total=1.0, products=[])
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx, minio_object_key=None)
    app.receipts_scans_repository.get_by_id.return_value = scan
    with pytest.raises(HTTPException) as exc_info:
        app.localize_receipt(1)
    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_localize_receipt_success(tmp_path):
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

    result = app.localize_receipt(1)
    app.minio_service.download_image.assert_called_once_with("receipts/1.jpg")


# ---------------------------------------------------------------------------
# import_bank_csv (lines 946-964)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_import_bank_csv_empty_returns_zeros():
    app = make_app()
    app.bank_csv_parser.parse_bytes.return_value = []
    result, ids = app.import_bank_csv(b"data")
    assert result.imported == 0
    assert ids == []


@pytest.mark.unit
def test_import_bank_csv_with_rows():
    app = make_app()
    app.bank_csv_parser.parse_bytes.return_value = [MagicMock()]
    app.bank_transactions_repository.insert_transactions.return_value = (2, 0)
    app.bank_transactions_repository.get_new_ids_for_categorization.return_value = [1, 2]
    app.bank_receipt_links_repository.find_auto_match_receipt.return_value = None
    result, ids = app.import_bank_csv(b"data")
    assert result.imported == 2
    assert ids == [1, 2]


# ---------------------------------------------------------------------------
# categorize_bank_transactions (lines 972-980)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_categorize_bank_transactions_skips_missing_tx():
    app = make_app()
    app.bank_transactions_repository.get_by_id.return_value = None
    app.categorize_bank_transactions([1])
    app.bank_categorization_service.assign_candidates.assert_not_called()


@pytest.mark.unit
def test_categorize_bank_transactions_updates_candidates():
    app = make_app()
    tx = MagicMock()
    app.bank_transactions_repository.get_by_id.return_value = tx
    app.bank_categorization_service.assign_candidates.return_value = {"candidates": []}
    app.categorize_bank_transactions([1])
    app.bank_transactions_repository.update_candidates.assert_called_once_with(1, {"candidates": []})


@pytest.mark.unit
def test_categorize_bank_transactions_swallows_exception():
    app = make_app()
    tx = MagicMock()
    app.bank_transactions_repository.get_by_id.return_value = tx
    app.bank_categorization_service.assign_candidates.side_effect = Exception("LLM down")
    # Should not raise
    app.categorize_bank_transactions([1])


# ---------------------------------------------------------------------------
# get_bank_transaction_by_id with receipt_link (line 998)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_bank_transaction_by_id_with_receipt_link():
    from src.data import BankTransactionDetail
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="REF001", booking_date="2024-01-01",
        amount=100.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {
        "receipt_transaction_id": 5,
        "scan_id": 2,
        "scan_filename": "receipt.jpg",
        "vendor_name": "Shop",
        "date": "2024-01-01",
        "total": 100.0,
    }
    result = app.get_bank_transaction_by_id(1)
    assert result is not None
    assert result.receipt_link is not None


# ---------------------------------------------------------------------------
# update_bank_transaction_category (lines 1005-1008)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_bank_transaction_category_skips_linked():
    from src.data import BankTransactionDetail, UpdateBankTransactionCategoryRequest
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="R", booking_date="2024-01-01",
        amount=10.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 1, "receipt_transaction_id": 1, "scan_filename": "f.jpg", "vendor_name": "V", "date": "2024-01-01", "total": 10.0}
    req = UpdateBankTransactionCategoryRequest(category_id=3)
    app.update_bank_transaction_category(1, req)
    app.bank_transactions_repository.update_category.assert_not_called()


@pytest.mark.unit
def test_update_bank_transaction_category_updates_when_not_linked():
    from src.data import BankTransactionDetail, UpdateBankTransactionCategoryRequest
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="R", booking_date="2024-01-01",
        amount=10.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = None
    req = UpdateBankTransactionCategoryRequest(category_id=3)
    app.update_bank_transaction_category(1, req)
    app.bank_transactions_repository.update_category.assert_called_once_with(1, 3)


# ---------------------------------------------------------------------------
# get_receipt_candidates_for_bank_tx (lines 1018-1030)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_candidates_for_bank_tx_returns_items():
    app = make_app()
    candidate = MagicMock()
    candidate.receipt_transaction_id = 1
    candidate.scan_id = 2
    candidate.scan_filename = "f.jpg"
    candidate.vendor_name = "Shop"
    candidate.date = "2024-01-01"
    candidate.total = 10.0
    candidate.match_score = 3
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = [candidate]
    result = app.get_receipt_candidates_for_bank_tx(1)
    assert len(result) == 1
    assert result[0].receipt_transaction_id == 1


# ---------------------------------------------------------------------------
# get_bank_tx_candidates_for_receipt with results (lines 1039-1049)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_bank_tx_candidates_for_receipt_returns_items():
    app = make_app()
    tx_mock = MagicMock()
    tx_mock.id = 10
    app.transactions_repository.get_by_scan_id.return_value = tx_mock
    candidate = MagicMock()
    candidate.bank_transaction_id = 5
    candidate.counterparty = "Store"
    candidate.booking_date = "2024-01-01"
    candidate.amount = -10.0
    candidate.match_score = 2
    app.bank_receipt_links_repository.find_bank_tx_candidates.return_value = [candidate]
    result = app.get_bank_tx_candidates_for_receipt(1)
    assert len(result) == 1
    assert result[0].bank_transaction_id == 5


# ---------------------------------------------------------------------------
# link_bank_to_receipt (lines 1138-1154)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_link_bank_to_receipt_returns_none_on_conflict():
    app = make_app()
    app.bank_receipt_links_repository.create_link.return_value = False
    from src.data import LinkReceiptRequest
    req = LinkReceiptRequest(receipt_transaction_id=5)
    result = app.link_bank_to_receipt(1, req)
    assert result is None


@pytest.mark.unit
def test_link_bank_to_receipt_returns_detail_on_success():
    from src.data import BankTransactionDetail, LinkReceiptRequest
    app = make_app()
    app.bank_receipt_links_repository.create_link.return_value = True
    # Simulate tag merge path (link_info present)
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {
        "scan_id": 2,
        "receipt_transaction_id": 5,
        "scan_filename": "f.jpg",
        "vendor_name": "Shop",
        "date": "2024-01-01",
        "total": 10.0,
    }
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["food"]
    app.bank_transactions_repository.get_tags_for_tx.return_value = ["expense"]
    detail = BankTransactionDetail(
        id=1, reference_number="R", booking_date="2024-01-01",
        amount=10.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    req = LinkReceiptRequest(receipt_transaction_id=5)
    result = app.link_bank_to_receipt(1, req)
    assert result is not None


# ---------------------------------------------------------------------------
# create_cash_transaction (lines 1169-1183)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_cash_transaction_returns_none_when_insert_fails():
    from src.data import CashTransactionCreate
    app = make_app()
    app.cash_transactions_repository.insert_transaction.return_value = None
    data = CashTransactionCreate(booking_date="2024-01-01", amount=-10.0)
    result = app.create_cash_transaction(data)
    assert result is None


@pytest.mark.unit
def test_create_cash_transaction_success():
    from src.data import CashTransactionCreate
    app = make_app()
    app.cash_transactions_repository.insert_transaction.return_value = 7
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    app.cash_receipt_links_repository.find_auto_match_receipt.return_value = None
    data = CashTransactionCreate(booking_date="2024-01-01", amount=-10.0)
    app.create_cash_transaction(data)
    app.cash_transactions_repository.insert_transaction.assert_called_once()


# ---------------------------------------------------------------------------
# create_cash_transaction_from_receipt (lines 1189-1216)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_cash_transaction_from_receipt_returns_none_when_no_tx():
    app = make_app()
    app.transactions_repository.get_by_scan_id.return_value = None
    result = app.create_cash_transaction_from_receipt(1)
    assert result is None


@pytest.mark.unit
def test_create_cash_transaction_from_receipt_success():
    app = make_app()
    tx = MagicMock()
    tx.items = []
    tx.total = 25.0
    tx.date = "2024-01-01"
    tx.vendor_id = None
    app.transactions_repository.get_by_scan_id.return_value = tx
    scan_mock = MagicMock()
    scan_mock.tags = ["food"]
    app.receipts_scans_repository.get_by_id.return_value = scan_mock
    app.cash_transactions_repository.insert_transaction.return_value = 8
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    app.create_cash_transaction_from_receipt(1)
    app.cash_transactions_repository.insert_transaction.assert_called_once()
    app.cash_receipt_links_repository.create_link.assert_called_once()
    app.cash_transactions_repository.update_tags.assert_called_once()


# ---------------------------------------------------------------------------
# get_cash_transaction_by_id with link (lines 1232-1235)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_cash_transaction_by_id_with_link():
    from src.data import CashTransactionDetail
    app = make_app()
    detail = CashTransactionDetail(
        id=1, booking_date="2024-01-01", amount=-10.0, currency="PLN", source="manual"
    )
    app.cash_transactions_repository.get_by_id.return_value = detail
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {
        "receipt_transaction_id": 3,
        "scan_id": 1,
        "scan_filename": "r.jpg",
        "vendor_name": "Shop",
        "date": "2024-01-01",
        "total": 10.0,
    }
    result = app.get_cash_transaction_by_id(1)
    assert result is not None
    assert result.receipt_link is not None


# ---------------------------------------------------------------------------
# update_cash_transaction (lines 1240-1250)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_cash_transaction_delegates():
    from src.data import CashTransactionUpdate
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    data = CashTransactionUpdate(booking_date="2024-02-01", amount=-20.0)
    app.update_cash_transaction(1, data)
    app.cash_transactions_repository.update.assert_called_once()


@pytest.mark.unit
def test_update_cash_transaction_no_booking_date():
    from src.data import CashTransactionUpdate
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    data = CashTransactionUpdate(amount=-5.0)
    app.update_cash_transaction(1, data)
    app.cash_transactions_repository.update.assert_called_once()


# ---------------------------------------------------------------------------
# update_cash_transaction_category (lines 1262-1265)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_cash_transaction_category_skips_when_linked():
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 1}
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {"receipt_transaction_id": 1, "scan_id": 1, "scan_filename": "f.jpg", "vendor_name": "V", "date": "2024-01-01", "total": 5.0}
    from src.data import UpdateCashTransactionCategoryRequest
    req = UpdateCashTransactionCategoryRequest(category_id=2)
    app.update_cash_transaction_category(1, req)
    app.cash_transactions_repository.update_category.assert_not_called()


@pytest.mark.unit
def test_update_cash_transaction_category_updates_when_not_linked():
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    from src.data import UpdateCashTransactionCategoryRequest
    req = UpdateCashTransactionCategoryRequest(category_id=2)
    app.update_cash_transaction_category(1, req)
    app.cash_transactions_repository.update_category.assert_called_once_with(1, 2)


# ---------------------------------------------------------------------------
# get_cash_tx_candidates_for_receipt with results (lines 1290-1300)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_cash_tx_candidates_for_receipt_returns_items():
    app = make_app()
    tx_mock = MagicMock()
    tx_mock.id = 10
    app.transactions_repository.get_by_scan_id.return_value = tx_mock
    app.cash_receipt_links_repository.find_cash_tx_candidates.return_value = [
        {
            "cash_transaction_id": 3,
            "description": "Coffee",
            "booking_date": "2024-01-01",
            "amount": -5.0,
            "match_score": 2,
        }
    ]
    result = app.get_cash_tx_candidates_for_receipt(1)
    assert len(result) == 1
    assert result[0].cash_transaction_id == 3


# ---------------------------------------------------------------------------
# link_cash_to_receipt success path (line 1311)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_link_cash_to_receipt_success():
    app = make_app()
    app.cash_receipt_links_repository.create_link.return_value = True
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    from src.data import LinkCashReceiptRequest
    req = LinkCashReceiptRequest(receipt_transaction_id=5)
    result = app.link_cash_to_receipt(1, req)
    assert result is not None


# ---------------------------------------------------------------------------
# update_receipt_tags: cash link present (lines 1327-1331)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_receipt_tags_merges_cash_tags():
    app = make_app()
    app.bank_receipt_links_repository.get_bank_tx_id_for_scan.return_value = None
    app.cash_receipt_links_repository.get_cash_tx_id_for_scan.return_value = 20
    app.cash_transactions_repository.get_tags_for_tx.return_value = ["c"]
    app.update_receipt_tags(1, ["a"])
    app.cash_transactions_repository.update_tags.assert_called()


# ---------------------------------------------------------------------------
# update_cash_transaction_tags with link (lines 1337-1342)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_cash_transaction_tags_with_link():
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 3}
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["receipt_tag"]
    app.update_cash_transaction_tags(5, ["x"])
    app.cash_transactions_repository.update_tags.assert_called()
    app.receipts_scans_repository.update_tags.assert_called()


# ---------------------------------------------------------------------------
# update_bank_transaction_tags with link (lines 1348-1353)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_bank_transaction_tags_with_link():
    app = make_app()
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 2}
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["receipt_tag"]
    app.update_bank_transaction_tags(5, ["x"])
    app.bank_transactions_repository.update_tags.assert_called()
    app.receipts_scans_repository.update_tags.assert_called()


# ---------------------------------------------------------------------------
# get_transactions_analytics (line 1396)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_transactions_analytics_delegates():
    app = make_app()
    app.get_transactions_analytics()
    app.unified_transactions_repository.get_analytics.assert_called_once()


# ---------------------------------------------------------------------------
# get_all_tags (lines 1402-1422)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_tags_returns_empty_when_no_conn():
    app = make_app()
    app.receipts_scans_repository.conn = None
    result = app.get_all_tags()
    assert result == []


@pytest.mark.unit
def test_get_all_tags_returns_tags():
    app = make_app()
    cursor_mock = MagicMock()
    cursor_mock.__enter__ = MagicMock(return_value=cursor_mock)
    cursor_mock.__exit__ = MagicMock(return_value=False)
    cursor_mock.fetchall.return_value = [("food",), ("transport",)]
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    app.receipts_scans_repository.conn = conn_mock
    result = app.get_all_tags()
    assert result == ["food", "transport"]


@pytest.mark.unit
def test_get_all_tags_returns_empty_on_exception():
    app = make_app()
    conn_mock = MagicMock()
    conn_mock.cursor.side_effect = Exception("db error")
    app.receipts_scans_repository.conn = conn_mock
    result = app.get_all_tags()
    assert result == []


# ---------------------------------------------------------------------------
# seed_and_get_classifications / update_category_classification (1432, 1437)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_seed_and_get_classifications_delegates():
    app = make_app()
    app.seed_and_get_classifications()
    app.budget_analysis_service.seed_and_get_classifications.assert_called_once()


@pytest.mark.unit
def test_update_category_classification_delegates():
    app = make_app()
    app.update_category_classification(3, "essential")
    app.budget_analysis_service.update_category_classification.assert_called_once_with(3, "essential")


# ---------------------------------------------------------------------------
# set_financial_focus (line 1443)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_set_financial_focus_delegates():
    from src.data import SetFinancialFocusRequest
    app = make_app()
    req = SetFinancialFocusRequest(label="savings", description="Save more")
    app.set_financial_focus(req)
    app.budget_analysis_service.set_financial_focus.assert_called_once_with("savings", "Save more")


# ---------------------------------------------------------------------------
# get_emergency_advice (lines 1462-1463)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_emergency_advice_delegates():
    app = make_app()
    app.budget_goals_repository.get_all_goals.return_value = []
    app.get_emergency_advice(500.0)
    app.budget_analysis_service.get_emergency_advice.assert_called_once_with(500.0, [])


# ---------------------------------------------------------------------------
# create_simulation (lines 1489-1495)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_simulation_delegates():
    from src.data import CreateBudgetSimulationRequest
    app = make_app()
    req = CreateBudgetSimulationRequest(
        name="Test Sim",
        expense_name="New Car",
        expense_amount_pln=1000.0,
        expense_type="one_time",
        expense_start_date="2024-06-01",
    )
    app.create_simulation(req)
    app.budget_simulations_repository.create_simulation.assert_called_once()


# ---------------------------------------------------------------------------
# get_simulation (lines 1498-1501)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_simulation_returns_none_when_missing():
    app = make_app()
    app.budget_simulations_repository.get_simulation.return_value = None
    result = app.get_simulation(1)
    assert result is None


@pytest.mark.unit
def test_get_simulation_returns_detail():
    app = make_app()
    row = {
        "id": 1, "name": "S", "expense_name": "E",
        "expense_amount": 100.0, "expense_type": "one_time",
        "expense_start_date": "2024-01-01", "status": "done",
        "result_json": None, "error_message": None,
        "created_at": "2024-01-01T00:00:00",
    }
    app.budget_simulations_repository.get_simulation.return_value = row
    result = app.get_simulation(1)
    assert result is not None
    assert result.name == "S"


# ---------------------------------------------------------------------------
# get_all_simulations (lines 1504-1517)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_simulations_returns_list():
    app = make_app()
    app.budget_simulations_repository.get_all_simulations.return_value = [
        {
            "id": 1, "name": "S1", "expense_name": "E1",
            "expense_amount": 50.0, "expense_type": "recurring",
            "expense_start_date": "2024-01-01", "status": "pending",
            "created_at": "2024-01-01T00:00:00",
        }
    ]
    result = app.get_all_simulations()
    assert len(result) == 1
    assert result[0].name == "S1"


# ---------------------------------------------------------------------------
# create_category (line 922)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_category_delegates():
    app = make_app()
    app.create_category("Groceries", None)
    app.categories_repository.create_category.assert_called_once_with("Groceries", None)


# ---------------------------------------------------------------------------
# get_all_evaluation_runs / get_evaluation_run (928-934)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_evaluation_runs_delegates():
    app = make_app()
    app.get_all_evaluation_runs()
    app.evaluations_repository.get_all_runs.assert_called_once()


@pytest.mark.unit
def test_get_evaluation_run_delegates():
    app = make_app()
    app.get_evaluation_run(5)
    app.evaluations_repository.get_run_with_results.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# get_bank_tx_ids_for_recategorization (line 968)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_bank_tx_ids_for_recategorization_delegates():
    app = make_app()
    app.get_bank_tx_ids_for_recategorization()
    app.bank_transactions_repository.get_ids_for_recategorization.assert_called_once()
