import pytest
from unittest.mock import MagicMock, call
from src.data import (
    ConfirmReceiptRequest,
    ProductItem,
    TransactionModel,
    ReceiptScanDetail,
)
from tests.unit.conftest import make_app


def make_confirm_request(**kwargs):
    defaults = dict(
        product_categories={"Chleb": 1},
        vendor=None,
        date=None,
        total=None,
        products=None,
        normalized_vendor=None,
        normalized_products=None,
    )
    defaults.update(kwargs)
    return ConfirmReceiptRequest(**defaults)


def make_scan_detail(vendor="Biedronka", date="2024-01-15", total=55.0, minio_object_key=None):
    tx = TransactionModel(
        vendor=vendor,
        title="PARAGON FISKALNY",
        products=[ProductItem(name="Chleb", quantity=1.0, price=5.0, unit_price=5.0)],
        total=total,
        date=date,
    )
    return ReceiptScanDetail(
        id=1,
        filename="receipt.jpg",
        status="TO_CONFIRM",
        result=tx,
        minio_object_key=minio_object_key,
    )


def _setup_no_transaction(app):
    """Prevent get_receipt_by_id from triggering bank/cash link Pydantic validation."""
    app.transactions_repository.get_by_scan_id.return_value = None


@pytest.mark.unit
def test_confirm_receipt_applies_vendor_override():
    app = make_app()
    scan = make_scan_detail()
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 42
    _setup_no_transaction(app)

    request = make_confirm_request(vendor="Override Store")
    app.confirm_receipt(1, request)

    call_args = app.receipts_scans_repository.set_result_by_id.call_args
    assert call_args is not None
    dumped = call_args[0][1]  # second positional arg
    assert dumped["vendor"] == "Override Store"


@pytest.mark.unit
def test_confirm_receipt_creates_transaction_with_correct_args():
    import datetime as dt
    app = make_app()
    scan = make_scan_detail(vendor="Lidl", date="2024-03-10", total=99.5)
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 5
    _setup_no_transaction(app)

    request = make_confirm_request()
    app.confirm_receipt(1, request)

    app.transactions_repository.create_transaction.assert_called_once()
    _, kwargs = app.transactions_repository.create_transaction.call_args
    assert kwargs["scan_id"] == 1
    assert kwargs["total"] == 99.5
    assert kwargs["transaction_date"] == dt.date(2024, 3, 10)


@pytest.mark.unit
def test_confirm_receipt_normalized_vendor_path():
    app = make_app()
    scan = make_scan_detail(vendor="BIEDRONKA 1234")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 7
    app.vendors_repository.get_vendor_by_name.return_value = None
    app.vendors_repository.insert_vendor.return_value = 99
    _setup_no_transaction(app)

    request = make_confirm_request(normalized_vendor="Biedronka")
    app.confirm_receipt(1, request)

    app.vendors_repository.insert_vendor.assert_called_once_with("Biedronka")
    app.vendors_repository.insert_alternative_name.assert_called_once_with("BIEDRONKA 1234", 99)


@pytest.mark.unit
def test_confirm_receipt_standard_vendor_lookup_path():
    app = make_app()
    scan = make_scan_detail()
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 8
    _setup_no_transaction(app)

    request = make_confirm_request()
    app.confirm_receipt(1, request)

    app.transactions_repository.lookup_vendor_id.assert_called_once_with("Biedronka")


@pytest.mark.unit
def test_confirm_receipt_analytics_exception_is_swallowed():
    app = make_app()
    scan = make_scan_detail()
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 9
    app.prompt_analytics_repository.upsert.side_effect = Exception("boom")
    _setup_no_transaction(app)

    request = make_confirm_request()
    result = app.confirm_receipt(1, request)

    # confirm_receipt should still return without raising (analytics non-fatal)
    app.receipts_scans_repository.get_by_id.assert_called()


@pytest.mark.unit
def test_confirm_receipt_returns_none_when_scan_missing():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None

    request = make_confirm_request()
    result = app.confirm_receipt(1, request)

    assert result is None


@pytest.mark.unit
def test_confirm_receipt_calls_auto_link():
    app = make_app()
    scan = make_scan_detail()
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.create_transaction.return_value = 42
    _setup_no_transaction(app)

    request = make_confirm_request()
    app.confirm_receipt(1, request)

    app.bank_receipt_links_repository.find_auto_match_bank_tx.assert_called()


@pytest.mark.unit
def test_reopen_receipt_deletes_transaction_and_resets_status():
    app = make_app()
    scan = make_scan_detail()
    app.receipts_scans_repository.get_by_id.return_value = scan
    _setup_no_transaction(app)

    app.reopen_receipt(1)

    app.transactions_repository.delete_by_scan_id.assert_called_once_with(1)
    app.receipts_scans_repository.set_status_to_confirm_by_id.assert_called_once_with(1)


@pytest.mark.unit
def test_delete_receipt_removes_minio_image():
    app = make_app()
    scan = make_scan_detail(minio_object_key="images/receipt.jpg")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.receipts_scans_repository.delete_scan_by_id.return_value = True

    result = app.delete_receipt(1)

    app.minio_service.delete_image.assert_called_once_with("images/receipt.jpg")
    app.receipts_scans_repository.delete_scan_by_id.assert_called_once_with(1)


@pytest.mark.unit
def test_delete_receipt_returns_false_when_scan_missing():
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None

    result = app.delete_receipt(1)

    assert result is False


@pytest.mark.unit
def test_retry_receipt_returns_false_when_scan_missing():
    app = make_app()
    app.receipts_scans_repository.reset_for_retry.return_value = None

    result = app.retry_receipt(1)

    assert result is False
