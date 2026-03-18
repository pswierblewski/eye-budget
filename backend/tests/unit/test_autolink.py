import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


def make_bank_match(bank_transaction_id=10, scan_id=1):
    m = MagicMock()
    m.bank_transaction_id = bank_transaction_id
    m.scan_id = scan_id
    return m


def make_receipt_match(receipt_transaction_id=20, scan_id=1):
    m = MagicMock()
    m.receipt_transaction_id = receipt_transaction_id
    m.scan_id = scan_id
    return m


@pytest.mark.unit
def test_auto_link_receipt_bank_has_priority():
    # Arrange
    app = make_app()
    bank_match = make_bank_match()
    app.bank_receipt_links_repository.find_auto_match_bank_tx.return_value = bank_match
    app.bank_receipt_links_repository.create_link.return_value = True

    # Act
    app._auto_link_receipt(scan_id=1, receipt_transaction_id=20)

    # Assert
    app.cash_receipt_links_repository.find_auto_match_cash_tx.assert_not_called()


@pytest.mark.unit
def test_auto_link_receipt_falls_back_to_cash():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.find_auto_match_bank_tx.return_value = None
    cash_match = {"cash_transaction_id": 55}
    app.cash_receipt_links_repository.find_auto_match_cash_tx.return_value = cash_match

    # Act
    app._auto_link_receipt(scan_id=1, receipt_transaction_id=20)

    # Assert
    app.cash_receipt_links_repository.create_link.assert_called_once_with(
        cash_transaction_id=55, receipt_transaction_id=20
    )


@pytest.mark.unit
def test_auto_link_receipt_merges_tags_on_bank_link():
    # Arrange
    app = make_app()
    bank_match = make_bank_match(bank_transaction_id=10, scan_id=1)
    app.bank_receipt_links_repository.find_auto_match_bank_tx.return_value = bank_match
    app.bank_receipt_links_repository.create_link.return_value = True
    app.receipts_scans_repository.get_tags_for_scan.return_value = ["a"]
    app.bank_transactions_repository.get_tags_for_tx.return_value = ["b"]

    # Act
    app._auto_link_receipt(scan_id=1, receipt_transaction_id=20)

    # Assert
    expected_merged = ["a", "b"]
    app.receipts_scans_repository.update_tags.assert_called_once_with(1, expected_merged)
    app.bank_transactions_repository.update_tags.assert_called_once_with(10, expected_merged)


@pytest.mark.unit
def test_auto_link_receipt_exception_is_swallowed():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.find_auto_match_bank_tx.side_effect = Exception("db error")

    # Act / Assert — should not raise
    app._auto_link_receipt(scan_id=1, receipt_transaction_id=20)


@pytest.mark.unit
def test_auto_link_bank_transactions_single_match_creates_link():
    # Arrange
    app = make_app()
    receipt_match = make_receipt_match(receipt_transaction_id=20, scan_id=1)
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = [MagicMock()]
    app.bank_receipt_links_repository.find_auto_match_receipt.return_value = receipt_match
    app.bank_receipt_links_repository.create_link.return_value = True
    app.receipts_scans_repository.get_tags_for_scan.return_value = []
    app.bank_transactions_repository.get_tags_for_tx.return_value = []

    # Act
    linked, skipped = app._auto_link_bank_transactions([42])

    # Assert
    app.bank_receipt_links_repository.create_link.assert_called_once()
    assert linked == 1
    assert skipped == 0


@pytest.mark.unit
def test_auto_link_bank_transactions_multi_candidate_is_skipped():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = [MagicMock(), MagicMock()]

    # Act
    linked, skipped = app._auto_link_bank_transactions([42])

    # Assert
    app.bank_receipt_links_repository.create_link.assert_not_called()
    assert linked == 0
    assert skipped == 1


@pytest.mark.unit
def test_auto_link_bank_transactions_no_match_no_link():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = [MagicMock()]
    app.bank_receipt_links_repository.find_auto_match_receipt.return_value = None

    # Act
    linked, skipped = app._auto_link_bank_transactions([42])

    # Assert
    app.bank_receipt_links_repository.create_link.assert_not_called()
    assert linked == 0


@pytest.mark.unit
def test_auto_link_cash_transaction_creates_link():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.find_auto_match_receipt.return_value = {"receipt_transaction_id": 42}
    app.cash_receipt_links_repository.create_link.return_value = True

    # Act
    result = app._auto_link_cash_transaction(tx_id=99)

    # Assert
    app.cash_receipt_links_repository.create_link.assert_called_once_with(
        cash_transaction_id=99, receipt_transaction_id=42
    )
    assert result is True
