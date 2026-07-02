import pytest
from decimal import Decimal
from src.services.revolut_csv_parser import RevolutCsvParser

SAMPLE_CSV = b"""Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
Deposit,Current,2026-01-09 14:16:48,2026-01-09 14:16:49,Payment from SOFTWARE,300.00,0.00,PLN,COMPLETED,484.21
Card Payment,Current,2026-01-12 11:01:02,2026-01-12 16:22:41,IDrive,-432.75,0.00,PLN,COMPLETED,51.46
Card Payment,Current,2026-04-13 15:24:46,,Midjourney,-44.96,0.00,PLN,REVERTED,
Card Payment,Current,2026-06-27 18:07:18,,Google Play,-9.99,0.00,PLN,PENDING,
"""


@pytest.mark.unit
def test_parse_skips_reverted_rows():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    descriptions = [r.description for r in rows]
    assert "Midjourney" not in descriptions


@pytest.mark.unit
def test_parse_includes_pending_rows():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    descriptions = [r.description for r in rows]
    assert "Google Play" in descriptions


@pytest.mark.unit
def test_parse_returns_correct_row_count():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert len(rows) == 3  # REVERTED is filtered out


@pytest.mark.unit
def test_parse_maps_amount_correctly():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    assert deposit.amount == Decimal("300.00")
    card = next(r for r in rows if r.description == "IDrive")
    assert card.amount == Decimal("-432.75")


@pytest.mark.unit
def test_parse_maps_dates_correctly():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    import datetime
    assert deposit.booking_date == datetime.date(2026, 1, 9)
    assert deposit.value_date == datetime.date(2026, 1, 9)


@pytest.mark.unit
def test_parse_value_date_none_when_completed_date_missing():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    pending = next(r for r in rows if r.description == "Google Play")
    assert pending.value_date is None


@pytest.mark.unit
def test_parse_maps_currency():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert all(r.currency == "PLN" for r in rows)


@pytest.mark.unit
def test_reference_number_starts_with_revolut():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert all(r.reference_number.startswith("revolut_") for r in rows)


@pytest.mark.unit
def test_reference_number_is_deterministic():
    parser = RevolutCsvParser()
    rows1 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    rows2 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    refs1 = [r.reference_number for r in rows1]
    refs2 = [r.reference_number for r in rows2]
    assert refs1 == refs2


@pytest.mark.unit
def test_reference_number_differs_by_account_id():
    parser = RevolutCsvParser()
    rows1 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    rows2 = parser.parse_bytes(SAMPLE_CSV, account_id=2)
    assert rows1[0].reference_number != rows2[0].reference_number


@pytest.mark.unit
def test_operation_type_maps_from_type_column():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    assert deposit.operation_type == "Deposit"
