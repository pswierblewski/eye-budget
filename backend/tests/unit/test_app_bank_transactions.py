"""Unit tests for App bank CSV import, categorization, links, and candidates."""
import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_import_bank_csv_empty_returns_zeros():
    # Arrange
    app = make_app()
    app.bank_csv_parser.parse_bytes.return_value = []

    # Act
    result, ids = app.import_bank_csv(b"data")

    # Assert
    assert result.imported == 0
    assert result.duplicates == 0
    assert result.errors == 0
    assert ids == []


@pytest.mark.unit
def test_import_bank_csv_with_rows():
    # Arrange
    app = make_app()
    app.bank_csv_parser.parse_bytes.return_value = [MagicMock()]
    app.bank_transactions_repository.insert_transactions.return_value = (2, 0)
    app.bank_transactions_repository.get_new_ids_for_categorization.return_value = [1, 2]
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = []
    app.bank_receipt_links_repository.find_auto_match_receipt.return_value = None

    # Act
    result, ids = app.import_bank_csv(b"data")

    # Assert
    assert result.imported == 2
    assert result.duplicates == 0
    assert result.errors == 0
    assert result.auto_linked == 0
    assert result.needs_manual_link == 0
    assert ids == [1, 2]


@pytest.mark.unit
def test_categorize_bank_transactions_skips_missing_tx():
    # Arrange
    app = make_app()
    app.bank_transactions_repository.get_by_id.return_value = None

    # Act
    app.categorize_bank_transactions([1])

    # Assert
    app.bank_categorization_service.assign_candidates.assert_not_called()


@pytest.mark.unit
def test_categorize_bank_transactions_updates_candidates():
    # Arrange
    app = make_app()
    tx = MagicMock()
    app.bank_transactions_repository.get_by_id.return_value = tx
    app.bank_categorization_service.assign_candidates.return_value = {"candidates": []}

    # Act
    app.categorize_bank_transactions([1])

    # Assert
    app.bank_transactions_repository.update_candidates.assert_called_once_with(1, {"candidates": []})


@pytest.mark.unit
def test_categorize_bank_transactions_swallows_exception():
    # Arrange
    app = make_app()
    tx = MagicMock()
    app.bank_transactions_repository.get_by_id.return_value = tx
    app.bank_categorization_service.assign_candidates.side_effect = Exception("LLM down")

    # Act / Assert — should not raise
    app.categorize_bank_transactions([1])


@pytest.mark.unit
def test_get_bank_transaction_by_id_with_receipt_link():
    # Arrange
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

    # Act
    result = app.get_bank_transaction_by_id(1)

    # Assert
    assert result is not None
    assert result.receipt_link is not None


@pytest.mark.unit
def test_update_bank_transaction_category_skips_linked():
    # Arrange
    from src.data import BankTransactionDetail, UpdateBankTransactionCategoryRequest
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="R", booking_date="2024-01-01",
        amount=10.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = {
        "scan_id": 1, "receipt_transaction_id": 1, "scan_filename": "f.jpg",
        "vendor_name": "V", "date": "2024-01-01", "total": 10.0,
    }
    req = UpdateBankTransactionCategoryRequest(category_id=3)

    # Act
    app.update_bank_transaction_category(1, req)

    # Assert
    app.bank_transactions_repository.update_category.assert_not_called()


@pytest.mark.unit
def test_update_bank_transaction_category_updates_when_not_linked():
    # Arrange
    from src.data import BankTransactionDetail, UpdateBankTransactionCategoryRequest
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="R", booking_date="2024-01-01",
        amount=10.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = None
    req = UpdateBankTransactionCategoryRequest(category_id=3)

    # Act
    app.update_bank_transaction_category(1, req)

    # Assert
    app.bank_transactions_repository.update_category.assert_called_once_with(1, 3)


@pytest.mark.unit
def test_get_receipt_candidates_for_bank_tx_returns_items():
    # Arrange
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

    # Act
    result = app.get_receipt_candidates_for_bank_tx(1)

    # Assert
    assert len(result) == 1
    assert result[0].receipt_transaction_id == 1


@pytest.mark.unit
def test_get_bank_tx_candidates_for_receipt_returns_items():
    # Arrange
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

    # Act
    result = app.get_bank_tx_candidates_for_receipt(1)

    # Assert
    assert len(result) == 1
    assert result[0].bank_transaction_id == 5


@pytest.mark.unit
def test_link_bank_to_receipt_returns_none_on_conflict():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.create_link.return_value = False
    from src.data import LinkReceiptRequest
    req = LinkReceiptRequest(receipt_transaction_id=5)

    # Act
    result = app.link_bank_to_receipt(1, req)

    # Assert
    assert result is None


@pytest.mark.unit
def test_link_bank_to_receipt_returns_detail_on_success():
    # Arrange
    from src.data import BankTransactionDetail, LinkReceiptRequest
    app = make_app()
    app.bank_receipt_links_repository.create_link.return_value = True
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

    # Act
    result = app.link_bank_to_receipt(1, req)

    # Assert
    assert result is not None
