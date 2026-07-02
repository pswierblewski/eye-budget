"""
Parser for Revolut CSV exports.

Expected columns (comma-separated, English):
  Type, Product, Started Date, Completed Date, Description,
  Amount, Fee, Currency, State, Balance
"""

import csv
import io
import hashlib
import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from .bank_csv_parser import BankTransactionRow


class RevolutCsvParser:
    ENCODINGS = ("utf-8-sig", "utf-8")

    def parse_bytes(self, data: bytes, account_id: int) -> list[BankTransactionRow]:
        text = self._decode(data)
        return self._parse_text(text, account_id)

    def _decode(self, data: bytes) -> str:
        for enc in self.ENCODINGS:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")

    def _parse_text(self, text: str, account_id: int) -> list[BankTransactionRow]:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[BankTransactionRow] = []
        for raw in reader:
            row = self._parse_row(raw, account_id)
            if row is not None:
                rows.append(row)
        return rows

    def _parse_row(self, raw: dict, account_id: int) -> Optional[BankTransactionRow]:
        state = (raw.get("State") or "").strip()
        if state == "REVERTED":
            return None

        started = (raw.get("Started Date") or "").strip()
        completed = (raw.get("Completed Date") or "").strip()
        description = (raw.get("Description") or "").strip()
        amount_str = (raw.get("Amount") or "").strip()
        currency = (raw.get("Currency") or "PLN").strip()
        op_type = (raw.get("Type") or "").strip()

        try:
            amount = Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None

        booking_date = self._parse_date(started)
        if booking_date is None:
            return None

        reference_number = self._make_reference(account_id, started, description, amount_str)

        return BankTransactionRow(
            reference_number=reference_number,
            booking_date=booking_date,
            value_date=self._parse_date(completed),
            counterparty=None,
            counterparty_address=None,
            source_account=None,
            target_account=None,
            description=description or None,
            amount=amount,
            currency=currency,
            operation_type=op_type or None,
        )

    @staticmethod
    def _make_reference(account_id: int, started: str, description: str, amount: str) -> str:
        # NOTE: Two distinct transactions with identical date+description+amount produce the
        # same hash and the second is silently dropped as a duplicate on re-import.
        # This is an inherent limitation of Revolut's CSV format (no stable per-row ID).
        raw = f"{account_id}|{started}|{description}|{amount}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"revolut_{digest}"

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime.date]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
