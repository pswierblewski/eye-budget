"""Unit tests for BankReceiptLinksRepository."""
import pytest
from datetime import date
from unittest.mock import MagicMock

from src.repositories.bank_receipt_links import (
    BankReceiptLinksRepository,
    ReceiptCandidate,
    BankTxCandidate,
    LinkInfo,
)

_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None, fetchmany_return=None):
    """Create a BankReceiptLinksRepository with mocked connection."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.fetchmany.return_value = fetchmany_return or []
    repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
    repo.conn = conn
    return repo, cursor


class TestFindReceiptCandidates:
    """Tests for find_receipt_candidates method."""

    @pytest.mark.unit
    def test_find_receipt_candidates_happy_path(self):
        # Arrange
        bank_tx_id = 1
        row = (10, 20, "scan.jpg", "Vendor A", date(2026, 4, 10), 99.99, 3)
        repo, cursor = make_repo(fetchall_return=[row])

        # Act
        result = repo.find_receipt_candidates(bank_tx_id)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], ReceiptCandidate)
        assert result[0].receipt_transaction_id == 10
        assert result[0].scan_id == 20
        assert result[0].scan_filename == "scan.jpg"
        assert result[0].vendor_name == "Vendor A"
        assert result[0].total == 99.99
        assert result[0].match_score == 3
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_find_receipt_candidates_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.find_receipt_candidates(1)

        # Assert
        assert result == []

    @pytest.mark.unit
    def test_find_receipt_candidates_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.find_receipt_candidates(1)

        # Assert
        assert result == []

    @pytest.mark.unit
    def test_find_receipt_candidates_multiple_rows(self):
        # Arrange
        bank_tx_id = 1
        rows = [
            (10, 20, "scan1.jpg", "Vendor A", date(2026, 4, 10), 99.99, 3),
            (11, 21, "scan2.jpg", "Vendor B", date(2026, 4, 11), 50.00, 2),
        ]
        repo, cursor = make_repo(fetchall_return=rows)

        # Act
        result = repo.find_receipt_candidates(bank_tx_id)

        # Assert
        assert len(result) == 2
        assert result[0].receipt_transaction_id == 10
        assert result[1].receipt_transaction_id == 11

    @pytest.mark.unit
    def test_find_receipt_candidates_date_string_conversion(self):
        # Arrange
        bank_tx_id = 1
        row = (10, 20, "scan.jpg", "Vendor A", "2026-04-10", 99.99, 3)
        repo, cursor = make_repo(fetchall_return=[row])

        # Act
        result = repo.find_receipt_candidates(bank_tx_id)

        # Assert
        assert result[0].date == "2026-04-10"


class TestFindBankTxCandidates:
    """Tests for find_bank_tx_candidates method."""

    @pytest.mark.unit
    def test_find_bank_tx_candidates_happy_path(self):
        # Arrange
        receipt_tx_id = 1
        row = (100, "Counterparty X", date(2026, 4, 10), -99.99, 3)
        repo, cursor = make_repo(fetchall_return=[row])

        # Act
        result = repo.find_bank_tx_candidates(receipt_tx_id)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], BankTxCandidate)
        assert result[0].bank_transaction_id == 100
        assert result[0].counterparty == "Counterparty X"
        assert result[0].amount == -99.99
        assert result[0].match_score == 3
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_find_bank_tx_candidates_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.find_bank_tx_candidates(1)

        # Assert
        assert result == []

    @pytest.mark.unit
    def test_find_bank_tx_candidates_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.find_bank_tx_candidates(1)

        # Assert
        assert result == []

    @pytest.mark.unit
    def test_find_bank_tx_candidates_multiple_rows(self):
        # Arrange
        receipt_tx_id = 1
        rows = [
            (100, "Party A", date(2026, 4, 10), -99.99, 3),
            (101, "Party B", date(2026, 4, 11), -50.00, 2),
        ]
        repo, cursor = make_repo(fetchall_return=rows)

        # Act
        result = repo.find_bank_tx_candidates(receipt_tx_id)

        # Assert
        assert len(result) == 2
        assert result[0].bank_transaction_id == 100
        assert result[1].bank_transaction_id == 101


class TestFindAutoMatchReceipt:
    """Tests for find_auto_match_receipt method."""

    @pytest.mark.unit
    def test_find_auto_match_receipt_single_match(self):
        # Arrange
        bank_tx_id = 1
        row = (10, 20, "scan.jpg", "Vendor A", date(2026, 4, 10), 99.99, 3)
        repo, cursor = make_repo(fetchmany_return=[row])

        # Act
        result = repo.find_auto_match_receipt(bank_tx_id)

        # Assert
        assert isinstance(result, ReceiptCandidate)
        assert result.receipt_transaction_id == 10
        assert result.scan_id == 20

    @pytest.mark.unit
    def test_find_auto_match_receipt_no_match(self):
        # Arrange
        bank_tx_id = 1
        repo, cursor = make_repo(fetchmany_return=[])

        # Act
        result = repo.find_auto_match_receipt(bank_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_receipt_ambiguous_multiple_matches(self):
        # Arrange
        bank_tx_id = 1
        rows = [
            (10, 20, "scan1.jpg", "Vendor A", date(2026, 4, 10), 99.99, 3),
            (11, 21, "scan2.jpg", "Vendor B", date(2026, 4, 11), 99.99, 3),
        ]
        repo, cursor = make_repo(fetchmany_return=rows)

        # Act
        result = repo.find_auto_match_receipt(bank_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_receipt_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.find_auto_match_receipt(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_receipt_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.find_auto_match_receipt(1)

        # Assert
        assert result is None


class TestFindAutoMatchBankTx:
    """Tests for find_auto_match_bank_tx method."""

    @pytest.mark.unit
    def test_find_auto_match_bank_tx_single_match(self):
        # Arrange
        receipt_tx_id = 1
        row = (100, "Counterparty X", date(2026, 4, 10), -99.99, 3)
        repo, cursor = make_repo(fetchmany_return=[row])

        # Act
        result = repo.find_auto_match_bank_tx(receipt_tx_id)

        # Assert
        assert isinstance(result, BankTxCandidate)
        assert result.bank_transaction_id == 100
        assert result.counterparty == "Counterparty X"

    @pytest.mark.unit
    def test_find_auto_match_bank_tx_no_match(self):
        # Arrange
        receipt_tx_id = 1
        repo, cursor = make_repo(fetchmany_return=[])

        # Act
        result = repo.find_auto_match_bank_tx(receipt_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_bank_tx_ambiguous_multiple_matches(self):
        # Arrange
        receipt_tx_id = 1
        rows = [
            (100, "Party A", date(2026, 4, 10), -99.99, 3),
            (101, "Party B", date(2026, 4, 11), -99.99, 3),
        ]
        repo, cursor = make_repo(fetchmany_return=rows)

        # Act
        result = repo.find_auto_match_bank_tx(receipt_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_bank_tx_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.find_auto_match_bank_tx(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_find_auto_match_bank_tx_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.find_auto_match_bank_tx(1)

        # Assert
        assert result is None


class TestCreateLink:
    """Tests for create_link method."""

    @pytest.mark.unit
    def test_create_link_happy_path(self):
        # Arrange
        bank_tx_id = 1
        receipt_tx_id = 10
        repo, cursor = make_repo(fetchone_return=(123,))

        # Act
        result = repo.create_link(bank_tx_id, receipt_tx_id)

        # Assert
        assert result is True
        cursor.execute.assert_called_once()
        repo.conn.commit.assert_called_once()

    @pytest.mark.unit
    def test_create_link_conflict_returns_none(self):
        # Arrange
        bank_tx_id = 1
        receipt_tx_id = 10
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.create_link(bank_tx_id, receipt_tx_id)

        # Assert
        assert result is False
        repo.conn.commit.assert_called_once()

    @pytest.mark.unit
    def test_create_link_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.create_link(1, 10)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_create_link_db_error_with_rollback(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.create_link(1, 10)

        # Assert
        assert result is False
        repo.conn.rollback.assert_called_once()


class TestDeleteLinkByBankTx:
    """Tests for delete_link_by_bank_tx method."""

    @pytest.mark.unit
    def test_delete_link_by_bank_tx_happy_path(self):
        # Arrange
        bank_tx_id = 1
        repo, cursor = make_repo()

        # Act
        result = repo.delete_link_by_bank_tx(bank_tx_id)

        # Assert
        assert result is True
        cursor.execute.assert_called_once()
        repo.conn.commit.assert_called_once()

    @pytest.mark.unit
    def test_delete_link_by_bank_tx_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.delete_link_by_bank_tx(1)

        # Assert
        assert result is False

    @pytest.mark.unit
    def test_delete_link_by_bank_tx_db_error_with_rollback(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.delete_link_by_bank_tx(1)

        # Assert
        assert result is False
        repo.conn.rollback.assert_called_once()


class TestGetLinkForBankTx:
    """Tests for get_link_for_bank_tx method."""

    @pytest.mark.unit
    def test_get_link_for_bank_tx_happy_path(self):
        # Arrange
        bank_tx_id = 1
        row = (1, 10)
        repo, cursor = make_repo(fetchone_return=row)

        # Act
        result = repo.get_link_for_bank_tx(bank_tx_id)

        # Assert
        assert isinstance(result, LinkInfo)
        assert result.bank_transaction_id == 1
        assert result.receipt_transaction_id == 10
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_get_link_for_bank_tx_not_found(self):
        # Arrange
        bank_tx_id = 999
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.get_link_for_bank_tx(bank_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_link_for_bank_tx_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.get_link_for_bank_tx(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_link_for_bank_tx_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.get_link_for_bank_tx(1)

        # Assert
        assert result is None


class TestGetLinkForReceiptTx:
    """Tests for get_link_for_receipt_tx method."""

    @pytest.mark.unit
    def test_get_link_for_receipt_tx_happy_path(self):
        # Arrange
        receipt_tx_id = 10
        row = (1, 10)
        repo, cursor = make_repo(fetchone_return=row)

        # Act
        result = repo.get_link_for_receipt_tx(receipt_tx_id)

        # Assert
        assert isinstance(result, LinkInfo)
        assert result.bank_transaction_id == 1
        assert result.receipt_transaction_id == 10
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_get_link_for_receipt_tx_not_found(self):
        # Arrange
        receipt_tx_id = 999
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.get_link_for_receipt_tx(receipt_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_link_for_receipt_tx_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.get_link_for_receipt_tx(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_link_for_receipt_tx_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.get_link_for_receipt_tx(1)

        # Assert
        assert result is None


class TestGetReceiptLinkInfo:
    """Tests for get_receipt_link_info method."""

    @pytest.mark.unit
    def test_get_receipt_link_info_happy_path(self):
        # Arrange
        bank_tx_id = 1
        row = (10, 20, "scan.jpg", "Vendor A", date(2026, 4, 10), 99.99)
        repo, cursor = make_repo(fetchone_return=row)

        # Act
        result = repo.get_receipt_link_info(bank_tx_id)

        # Assert
        assert isinstance(result, dict)
        assert result["receipt_transaction_id"] == 10
        assert result["scan_id"] == 20
        assert result["scan_filename"] == "scan.jpg"
        assert result["vendor_name"] == "Vendor A"
        assert result["total"] == 99.99
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_get_receipt_link_info_not_found(self):
        # Arrange
        bank_tx_id = 999
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.get_receipt_link_info(bank_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_receipt_link_info_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.get_receipt_link_info(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_receipt_link_info_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.get_receipt_link_info(1)

        # Assert
        assert result is None


class TestGetBankLinkInfo:
    """Tests for get_bank_link_info method."""

    @pytest.mark.unit
    def test_get_bank_link_info_happy_path(self):
        # Arrange
        receipt_tx_id = 10
        row = (1, "Counterparty X", date(2026, 4, 10), -99.99)
        repo, cursor = make_repo(fetchone_return=row)

        # Act
        result = repo.get_bank_link_info(receipt_tx_id)

        # Assert
        assert isinstance(result, dict)
        assert result["bank_transaction_id"] == 1
        assert result["counterparty"] == "Counterparty X"
        assert result["amount"] == -99.99
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_get_bank_link_info_not_found(self):
        # Arrange
        receipt_tx_id = 999
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.get_bank_link_info(receipt_tx_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_bank_link_info_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.get_bank_link_info(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_bank_link_info_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.get_bank_link_info(1)

        # Assert
        assert result is None


class TestGetBankTxIdForScan:
    """Tests for get_bank_tx_id_for_scan method."""

    @pytest.mark.unit
    def test_get_bank_tx_id_for_scan_happy_path(self):
        # Arrange
        scan_id = 20
        row = (1,)
        repo, cursor = make_repo(fetchone_return=row)

        # Act
        result = repo.get_bank_tx_id_for_scan(scan_id)

        # Assert
        assert result == 1
        cursor.execute.assert_called_once()

    @pytest.mark.unit
    def test_get_bank_tx_id_for_scan_not_found(self):
        # Arrange
        scan_id = 999
        repo, cursor = make_repo(fetchone_return=None)

        # Act
        result = repo.get_bank_tx_id_for_scan(scan_id)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_bank_tx_id_for_scan_no_connection(self):
        # Arrange
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = None

        # Act
        result = repo.get_bank_tx_id_for_scan(1)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_get_bank_tx_id_for_scan_db_error(self):
        # Arrange
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.execute.side_effect = Exception("DB error")
        repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
        repo.conn = conn

        # Act
        result = repo.get_bank_tx_id_for_scan(1)

        # Assert
        assert result is None
