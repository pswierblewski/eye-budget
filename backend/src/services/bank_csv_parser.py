"""
Parser for Pekao SA bank CSV exports.

Expected columns (semicolon-separated, Polish locale):
  Data księgowania; Data waluty; Nadawca / Odbiorca; Adres nadawcy / odbiorcy;
  Rachunek źródłowy; Rachunek docelowy; Tytułem; Kwota operacji; Waluta;
  Numer referencyjny; Typ operacji
"""

import csv
import io
import datetime
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class BankTransactionRow:
    reference_number: str
    booking_date: datetime.date
    value_date: Optional[datetime.date]
    counterparty: Optional[str]
    counterparty_address: Optional[str]
    source_account: Optional[str]
    target_account: Optional[str]
    description: Optional[str]
    amount: Decimal
    currency: str
    operation_type: Optional[str]


class PekaoCsvParser:
    ENCODINGS = ("utf-8-sig", "utf-8", "cp1250", "iso-8859-2")

    # Map Polish column headers → internal keys
    COLUMN_MAP = {
        "Data księgowania":         "booking_date",
        "Data waluty":              "value_date",
        "Nadawca / Odbiorca":       "counterparty",
        "Adres nadawcy / odbiorcy": "counterparty_address",
        "Rachunek źródłowy":        "source_account",
        "Rachunek docelowy":        "target_account",
        "Tytułem":                  "description",
        "Kwota operacji":           "amount",
        "Waluta":                   "currency",
        "Numer referencyjny":       "reference_number",
        "Typ operacji":             "operation_type",
    }

    def parse_bytes(self, data: bytes) -> list[BankTransactionRow]:
        """Parse raw bytes of a Pekao CSV export."""
        text = self._decode(data)
        return self._parse_text(text)

    def _decode(self, data: bytes) -> str:
        for enc in self.ENCODINGS:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")

    def _parse_text(self, text: str) -> list[BankTransactionRow]:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        rows: list[BankTransactionRow] = []
        for raw in reader:
            row = self._parse_row(raw)
            if row is not None:
                rows.append(row)
        return rows

    def _parse_row(self, raw: dict) -> Optional[BankTransactionRow]:
        # Map Polish headers → internal names (strip BOM / whitespace from keys)
        mapped: dict = {}
        for key, value in raw.items():
            clean_key = key.strip().lstrip("\ufeff")
            internal = self.COLUMN_MAP.get(clean_key)
            if internal:
                mapped[internal] = (value or "").strip()

        # Reference number is the deduplication key — skip rows without it
        ref = self._strip_apostrophe(mapped.get("reference_number", ""))
        if not ref:
            return None

        # Parse amount — Polish format: "1 014,31" or "-29,99"
        amount_str = mapped.get("amount", "")
        try:
            amount = self._parse_amount(amount_str)
        except (InvalidOperation, ValueError):
            return None

        return BankTransactionRow(
            reference_number=ref,
            booking_date=self._parse_date(mapped.get("booking_date", "")),
            value_date=self._parse_date_optional(mapped.get("value_date", "")),
            counterparty=mapped.get("counterparty") or None,
            counterparty_address=mapped.get("counterparty_address") or None,
            source_account=self._strip_apostrophe(mapped.get("source_account", "")) or None,
            target_account=self._strip_apostrophe(mapped.get("target_account", "")) or None,
            description=mapped.get("description") or None,
            amount=amount,
            currency=mapped.get("currency", "PLN"),
            operation_type=mapped.get("operation_type") or None,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_apostrophe(value: str) -> str:
        """Pekao prefixes some fields with a leading apostrophe to prevent Excel auto-format."""
        return value.lstrip("'").strip()

    @staticmethod
    def _parse_amount(value: str) -> Decimal:
        """Convert Polish-locale number string to Decimal.

        Examples: "-29,99" → Decimal("-29.99"), "-1 014,31" → Decimal("-1014.31")
        """
        clean = value.replace("\xa0", "").replace(" ", "").replace(",", ".")
        return Decimal(clean)

    @staticmethod
    def _parse_date(value: str) -> datetime.date:
        """Parse DD.MM.YYYY date string. Returns today if blank/invalid."""
        try:
            return datetime.datetime.strptime(value.strip(), "%d.%m.%Y").date()
        except (ValueError, AttributeError):
            return datetime.date.today()

    @staticmethod
    def _parse_date_optional(value: str) -> Optional[datetime.date]:
        """Parse DD.MM.YYYY date string. Returns None if blank/invalid."""
        try:
            return datetime.datetime.strptime(value.strip(), "%d.%m.%Y").date()
        except (ValueError, AttributeError):
            return None
