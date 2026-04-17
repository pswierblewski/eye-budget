"""Unit tests for App cash transactions, links, and tag propagation."""
import datetime as dt
import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_create_cash_transaction_returns_none_when_insert_fails():
    # Arrange
    from src.data import CashTransactionCreate
    app = make_app()
    app.cash_transactions_repository.insert_transaction.return_value = None
    data = CashTransactionCreate(booking_date="2024-01-01", amount=-10.0)

    # Act
    result = app.create_cash_transaction(data)

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_cash_transaction_success():
    # Arrange
    from src.data import CashTransactionCreate
    app = make_app()
    app.cash_transactions_repository.insert_transaction.return_value = 7
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    app.cash_receipt_links_repository.find_auto_match_receipt.return_value = None
    data = CashTransactionCreate(booking_date="2024-01-01", amount=-10.0)

    # Act
    app.create_cash_transaction(data)

    # Assert
    app.cash_transactions_repository.insert_transaction.assert_called_once()


@pytest.mark.unit
def test_create_cash_transaction_from_receipt_returns_none_when_no_tx():
    # Arrange
    app = make_app()
    app.transactions_repository.get_by_scan_id.return_value = None

    # Act
    result = app.create_cash_transaction_from_receipt(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_cash_transaction_from_receipt_success():
    # Arrange
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

    # Act
    app.create_cash_transaction_from_receipt(1)

    # Assert
    app.cash_transactions_repository.insert_transaction.assert_called_once()
    app.cash_receipt_links_repository.create_link.assert_called_once()
    app.cash_transactions_repository.update_tags.assert_called_once()


@pytest.mark.unit
def test_get_cash_transaction_by_id_with_link():
    # Arrange
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

    # Act
    result = app.get_cash_transaction_by_id(1)

    # Assert
    assert result is not None
    assert result.receipt_link is not None


@pytest.mark.unit
def test_update_cash_transaction_passes_parsed_booking_date_and_amount():
    # Arrange
    from src.data import CashTransactionUpdate
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    data = CashTransactionUpdate(booking_date="2024-02-01", amount=-20.0)

    # Act
    app.update_cash_transaction(1, data)

    # Assert
    app.cash_transactions_repository.update.assert_called_once_with(
        1,
        booking_date=dt.date(2024, 2, 1),
        description=None,
        amount=-20.0,
        category_id=None,
        vendor_id=None,
    )


@pytest.mark.unit
def test_update_cash_transaction_omits_booking_date_when_not_set():
    # Arrange
    from src.data import CashTransactionUpdate
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    data = CashTransactionUpdate(amount=-5.0)

    # Act
    app.update_cash_transaction(1, data)

    # Assert
    app.cash_transactions_repository.update.assert_called_once_with(
        1,
        booking_date=None,
        description=None,
        amount=-5.0,
        category_id=None,
        vendor_id=None,
    )


@pytest.mark.unit
def test_update_cash_transaction_category_skips_when_linked():
    # Arrange
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {
        "receipt_transaction_id": 1, "scan_id": 1, "scan_filename": "f.jpg",
        "vendor_name": "V", "date": "2024-01-01", "total": 5.0,
    }
    from src.data import UpdateCashTransactionCategoryRequest
    req = UpdateCashTransactionCategoryRequest(category_id=2)

    # Act
    app.update_cash_transaction_category(1, req)

    # Assert
    app.cash_transactions_repository.update_category.assert_not_called()


@pytest.mark.unit
def test_update_cash_transaction_category_updates_when_not_linked():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    from src.data import UpdateCashTransactionCategoryRequest
    req = UpdateCashTransactionCategoryRequest(category_id=2)

    # Act
    app.update_cash_transaction_category(1, req)

    # Assert
    app.cash_transactions_repository.update_category.assert_called_once_with(1, 2)


@pytest.mark.unit
def test_get_cash_tx_candidates_for_receipt_returns_items():
    # Arrange
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

    # Act
    result = app.get_cash_tx_candidates_for_receipt(1)

    # Assert
    assert len(result) == 1
    assert result[0].cash_transaction_id == 3


@pytest.mark.unit
def test_link_cash_to_receipt_success():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.create_link.return_value = True
    app.cash_transactions_repository.get_by_id.return_value = MagicMock()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None
    from src.data import LinkCashReceiptRequest
    req = LinkCashReceiptRequest(receipt_transaction_id=5)

    # Act
    result = app.link_cash_to_receipt(1, req)

    # Assert
    assert result is not None


@pytest.mark.unit
def test_update_receipt_tags_merges_cash_tags():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.get_bank_tx_id_for_scan.return_value = None
    app.cash_receipt_links_repository.get_cash_tx_id_for_scan.return_value = 20
    app.cash_transactions_repository.get_tags_for_tx.return_value = ["c"]

    # Act
    app.update_receipt_tags(1, ["a"])

    # Assert
    app.cash_transactions_repository.update_tags.assert_called()


@pytest.mark.unit
def test_update_cash_transaction_tags_with_link():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 3}
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["receipt_tag"]

    # Act
    app.update_cash_transaction_tags(5, ["x"])

    # Assert
    app.cash_transactions_repository.update_tags.assert_called()
    app.receipts_scans_repository.update_tags.assert_called()


@pytest.mark.unit
def test_update_bank_transaction_tags_with_link():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {"scan_id": 2}
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["receipt_tag"]

    # Act
    app.update_bank_transaction_tags(5, ["x"])

    # Assert
    app.bank_transactions_repository.update_tags.assert_called()
    app.receipts_scans_repository.update_tags.assert_called()
