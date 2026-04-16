import pytest
from datetime import date
from unittest.mock import MagicMock
from src.repositories.cash_receipt_links import CashReceiptLinksRepository


_UNSET = object()


def make_repo(fetchone_return=_UNSET, fetchall_return=None, fetchmany_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.fetchmany.return_value = fetchmany_return or []
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = conn
    return repo, cursor


# ------------------------------------------------------------------
# find_receipt_candidates
# ------------------------------------------------------------------

@pytest.mark.unit
def test_find_receipt_candidates_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (101, 201, "scan.jpg", "Lidl", date(2025, 4, 15), 49.99, 3),
            (102, 202, "scan2.jpg", "Grocery Store", date(2025, 4, 16), 49.99, 2),
        ]
    )

    # Act
    result = repo.find_receipt_candidates(cash_transaction_id=1)

    # Assert
    assert len(result) == 2
    assert result[0]["receipt_transaction_id"] == 101
    assert result[0]["scan_id"] == 201
    assert result[0]["vendor_name"] == "Lidl"
    assert result[0]["total"] == 49.99
    assert result[0]["match_score"] == 3
    assert result[1]["receipt_transaction_id"] == 102


@pytest.mark.unit
def test_find_receipt_candidates_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.find_receipt_candidates(cash_transaction_id=1)

    # Assert
    assert result == []


@pytest.mark.unit
def test_find_receipt_candidates_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB connection error")

    # Act
    result = repo.find_receipt_candidates(cash_transaction_id=1)

    # Assert
    assert result == []


# ------------------------------------------------------------------
# find_cash_tx_candidates
# ------------------------------------------------------------------

@pytest.mark.unit
def test_find_cash_tx_candidates_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[
            (301, "Card payment", date(2025, 4, 15), -49.99, 3),
            (302, "Card payment", date(2025, 4, 16), -49.99, 2),
        ]
    )

    # Act
    result = repo.find_cash_tx_candidates(receipt_transaction_id=1)

    # Assert
    assert len(result) == 2
    assert result[0]["cash_transaction_id"] == 301
    assert result[0]["description"] == "Card payment"
    assert result[0]["amount"] == -49.99
    assert result[0]["match_score"] == 3
    assert result[1]["cash_transaction_id"] == 302


@pytest.mark.unit
def test_find_cash_tx_candidates_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.find_cash_tx_candidates(receipt_transaction_id=1)

    # Assert
    assert result == []


@pytest.mark.unit
def test_find_cash_tx_candidates_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.find_cash_tx_candidates(receipt_transaction_id=1)

    # Assert
    assert result == []


# ------------------------------------------------------------------
# find_auto_match_receipt
# ------------------------------------------------------------------

@pytest.mark.unit
def test_find_auto_match_receipt_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchmany_return=[
            (101, 201, "scan.jpg", "Lidl", date(2025, 4, 15), 49.99, 3),
        ]
    )

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=1)

    # Assert
    assert result is not None
    assert result["receipt_transaction_id"] == 101
    assert result["scan_filename"] == "scan.jpg"
    assert result["vendor_name"] == "Lidl"
    assert result["total"] == 49.99
    assert result["match_score"] == 3


@pytest.mark.unit
def test_find_auto_match_receipt_no_candidates():
    # Arrange
    repo, cursor = make_repo(fetchmany_return=[])

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_receipt_ambiguous():
    # Arrange
    repo, cursor = make_repo(
        fetchmany_return=[
            (101, 201, "scan1.jpg", "Lidl", date(2025, 4, 15), 49.99, 3),
            (102, 202, "scan2.jpg", "Lidl", date(2025, 4, 14), 49.99, 3),
        ]
    )

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_receipt_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_receipt_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=1)

    # Assert
    assert result is None


# ------------------------------------------------------------------
# find_auto_match_cash_tx
# ------------------------------------------------------------------

@pytest.mark.unit
def test_find_auto_match_cash_tx_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchmany_return=[
            (301, "Card payment", date(2025, 4, 15), -49.99, 3),
        ]
    )

    # Act
    result = repo.find_auto_match_cash_tx(receipt_transaction_id=1)

    # Assert
    assert result is not None
    assert result["cash_transaction_id"] == 301
    assert result["description"] == "Card payment"
    assert result["amount"] == -49.99
    assert result["match_score"] == 3


@pytest.mark.unit
def test_find_auto_match_cash_tx_no_candidates():
    # Arrange
    repo, cursor = make_repo(fetchmany_return=[])

    # Act
    result = repo.find_auto_match_cash_tx(receipt_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_cash_tx_ambiguous():
    # Arrange
    repo, cursor = make_repo(
        fetchmany_return=[
            (301, "Card payment", date(2025, 4, 15), -49.99, 3),
            (302, "Card payment", date(2025, 4, 14), -49.99, 3),
        ]
    )

    # Act
    result = repo.find_auto_match_cash_tx(receipt_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_cash_tx_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.find_auto_match_cash_tx(receipt_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_cash_tx_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.find_auto_match_cash_tx(receipt_transaction_id=1)

    # Assert
    assert result is None


# ------------------------------------------------------------------
# create_link
# ------------------------------------------------------------------

@pytest.mark.unit
def test_create_link_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.create_link(cash_transaction_id=1, receipt_transaction_id=101)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_link_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.create_link(cash_transaction_id=1, receipt_transaction_id=101)

    # Assert
    assert result is False


@pytest.mark.unit
def test_create_link_db_error_with_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("Constraint violation")

    # Act
    result = repo.create_link(cash_transaction_id=1, receipt_transaction_id=101)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ------------------------------------------------------------------
# delete_link_by_cash_tx
# ------------------------------------------------------------------

@pytest.mark.unit
def test_delete_link_by_cash_tx_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_link_by_cash_tx(cash_transaction_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_delete_link_by_cash_tx_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.delete_link_by_cash_tx(cash_transaction_id=1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_link_by_cash_tx_db_error_with_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.delete_link_by_cash_tx(cash_transaction_id=1)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# ------------------------------------------------------------------
# get_receipt_link_info
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_link_info_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchone_return=(101, 201, "scan.jpg", "Lidl", date(2025, 4, 15), 49.99)
    )

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=1)

    # Assert
    assert result is not None
    assert result["receipt_transaction_id"] == 101
    assert result["scan_id"] == 201
    assert result["scan_filename"] == "scan.jpg"
    assert result["vendor_name"] == "Lidl"
    assert result["date"] == "2025-04-15"
    assert result["total"] == 49.99


@pytest.mark.unit
def test_get_receipt_link_info_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_receipt_link_info_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_receipt_link_info_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=1)

    # Assert
    assert result is None


# ------------------------------------------------------------------
# get_cash_link_info
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_cash_link_info_happy_path():
    # Arrange
    repo, cursor = make_repo(
        fetchone_return=(301, "Card payment", date(2025, 4, 15), -49.99)
    )

    # Act
    result = repo.get_cash_link_info(receipt_transaction_id=1)

    # Assert
    assert result is not None
    assert result["cash_transaction_id"] == 301
    assert result["description"] == "Card payment"
    assert result["booking_date"] == "2025-04-15"
    assert result["amount"] == -49.99


@pytest.mark.unit
def test_get_cash_link_info_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_cash_link_info(receipt_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_cash_link_info_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.get_cash_link_info(receipt_transaction_id=1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_cash_link_info_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_cash_link_info(receipt_transaction_id=1)

    # Assert
    assert result is None


# ------------------------------------------------------------------
# get_cash_tx_id_for_scan
# ------------------------------------------------------------------

@pytest.mark.unit
def test_get_cash_tx_id_for_scan_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(301,))

    # Act
    result = repo.get_cash_tx_id_for_scan(scan_id=201)

    # Assert
    assert result == 301


@pytest.mark.unit
def test_get_cash_tx_id_for_scan_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_cash_tx_id_for_scan(scan_id=201)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_cash_tx_id_for_scan_no_conn():
    # Arrange
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = None

    # Act
    result = repo.get_cash_tx_id_for_scan(scan_id=201)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_cash_tx_id_for_scan_db_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_cash_tx_id_for_scan(scan_id=201)

    # Assert
    assert result is None
