"""
Repository for receipt_bank_links join table.

Handles finding match candidates between bank_transactions and receipt_transactions,
and creating/deleting links between them.

Matching logic:
- Amount: ABS(bank.amount) = receipt.total   (exact)
- Date:   bank.booking_date BETWEEN receipt.date - 2 AND receipt.date + 2
- Vendor bonus: both rows share the same vendor_id  (+1 to match_score)

match_score:
  2 = amount + date only
  3 = amount + date + vendor
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass
class ReceiptCandidate:
    """A receipt_transaction candidate for linking to a bank transaction."""
    receipt_transaction_id: int
    scan_id: int
    scan_filename: str
    vendor_name: str
    date: str          # ISO date
    total: float
    match_score: int   # 2 = amount+date, 3 = amount+date+vendor


@dataclass
class BankTxCandidate:
    """A bank_transaction candidate for linking to a receipt transaction."""
    bank_transaction_id: int
    counterparty: str | None
    booking_date: str  # ISO date
    amount: float
    match_score: int


@dataclass
class LinkInfo:
    """Current link info returned inside bank tx / receipt detail."""
    bank_transaction_id: int
    receipt_transaction_id: int


class BankReceiptLinksRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    # ------------------------------------------------------------------
    # Candidate queries
    # ------------------------------------------------------------------

    def find_receipt_candidates(self, bank_transaction_id: int) -> list[ReceiptCandidate]:
        """
        Return receipt_transactions that match the given bank transaction by
        amount (exact) and date (±2 days).  Rows already linked to any bank
        transaction are excluded.  Results are ordered by match_score DESC.
        """
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        rt.id                       AS receipt_transaction_id,
                        rs.id                       AS scan_id,
                        rs.filename                 AS scan_filename,
                        COALESCE(v.name, rt.raw_vendor_name) AS vendor_name,
                        rt.date,
                        rt.total,
                        CASE
                            WHEN bt.vendor_id IS NOT NULL
                             AND rt.vendor_id IS NOT NULL
                             AND bt.vendor_id = rt.vendor_id  THEN 3
                            ELSE 2
                        END                         AS match_score
                    FROM bank_transactions bt
                    JOIN receipt_transactions rt
                      ON ABS(bt.amount) = rt.total
                     AND bt.booking_date BETWEEN rt.date - INTERVAL '2 days'
                                             AND rt.date + INTERVAL '2 days'
                    JOIN receipts_scans rs ON rs.id = rt.scan_id
                    LEFT JOIN vendors v ON v.id = rt.vendor_id
                    LEFT JOIN receipt_bank_links rbl ON rbl.receipt_transaction_id = rt.id
                    WHERE bt.id = %s
                      AND rbl.id IS NULL
                    ORDER BY match_score DESC, rt.date DESC
                    """,
                    (bank_transaction_id,),
                )
                rows = cur.fetchall()
            return [
                ReceiptCandidate(
                    receipt_transaction_id=r[0],
                    scan_id=r[1],
                    scan_filename=r[2],
                    vendor_name=r[3],
                    date=r[4].isoformat() if isinstance(r[4], datetime.date) else str(r[4]),
                    total=float(r[5]),
                    match_score=r[6],
                )
                for r in rows
            ]
        except Exception as e:
            print(f"BankReceiptLinksRepository.find_receipt_candidates error: {e}")
            return []

    def find_bank_tx_candidates(self, receipt_transaction_id: int) -> list[BankTxCandidate]:
        """
        Return bank_transactions that match the given receipt transaction by
        amount (exact) and date (±2 days).  Rows already linked to any receipt
        are excluded.  Results are ordered by match_score DESC.
        """
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        bt.id,
                        bt.counterparty,
                        bt.booking_date,
                        bt.amount,
                        CASE
                            WHEN bt.vendor_id IS NOT NULL
                             AND rt.vendor_id IS NOT NULL
                             AND bt.vendor_id = rt.vendor_id  THEN 3
                            ELSE 2
                        END AS match_score
                    FROM receipt_transactions rt
                    JOIN bank_transactions bt
                      ON ABS(bt.amount) = rt.total
                     AND bt.booking_date BETWEEN rt.date - INTERVAL '2 days'
                                             AND rt.date + INTERVAL '2 days'
                    LEFT JOIN receipt_bank_links rbl ON rbl.bank_transaction_id = bt.id
                    WHERE rt.id = %s
                      AND rbl.id IS NULL
                    ORDER BY match_score DESC, bt.booking_date DESC
                    """,
                    (receipt_transaction_id,),
                )
                rows = cur.fetchall()
            return [
                BankTxCandidate(
                    bank_transaction_id=r[0],
                    counterparty=r[1],
                    booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                    amount=float(r[3]),
                    match_score=r[4],
                )
                for r in rows
            ]
        except Exception as e:
            print(f"BankReceiptLinksRepository.find_bank_tx_candidates error: {e}")
            return []

    # ------------------------------------------------------------------
    # Link CRUD
    # ------------------------------------------------------------------

    def create_link(
        self, bank_transaction_id: int, receipt_transaction_id: int
    ) -> bool:
        """Insert a link.  Returns False if either ID is already linked."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO receipt_bank_links (bank_transaction_id, receipt_transaction_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (bank_transaction_id, receipt_transaction_id),
                )
                result = cur.fetchone()
            self.conn.commit()
            return result is not None
        except Exception as e:
            print(f"BankReceiptLinksRepository.create_link error: {e}")
            self.conn.rollback()
            return False

    def delete_link_by_bank_tx(self, bank_transaction_id: int) -> bool:
        """Remove the link for a given bank transaction."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM receipt_bank_links WHERE bank_transaction_id = %s",
                    (bank_transaction_id,),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"BankReceiptLinksRepository.delete_link_by_bank_tx error: {e}")
            self.conn.rollback()
            return False

    def get_link_for_bank_tx(self, bank_transaction_id: int) -> LinkInfo | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bank_transaction_id, receipt_transaction_id
                    FROM receipt_bank_links
                    WHERE bank_transaction_id = %s
                    """,
                    (bank_transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return LinkInfo(bank_transaction_id=r[0], receipt_transaction_id=r[1])
        except Exception as e:
            print(f"BankReceiptLinksRepository.get_link_for_bank_tx error: {e}")
            return None

    def get_link_for_receipt_tx(self, receipt_transaction_id: int) -> LinkInfo | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bank_transaction_id, receipt_transaction_id
                    FROM receipt_bank_links
                    WHERE receipt_transaction_id = %s
                    """,
                    (receipt_transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return LinkInfo(bank_transaction_id=r[0], receipt_transaction_id=r[1])
        except Exception as e:
            print(f"BankReceiptLinksRepository.get_link_for_receipt_tx error: {e}")
            return None

    def get_receipt_link_info(self, bank_transaction_id: int):
        """Return enriched ReceiptLinkInfo for displaying inside a bank tx detail."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rt.id, rs.id, rs.filename,
                           COALESCE(v.name, rt.raw_vendor_name),
                           rt.date, rt.total
                    FROM receipt_bank_links rbl
                    JOIN receipt_transactions rt ON rt.id = rbl.receipt_transaction_id
                    JOIN receipts_scans rs ON rs.id = rt.scan_id
                    LEFT JOIN vendors v ON v.id = rt.vendor_id
                    WHERE rbl.bank_transaction_id = %s
                    """,
                    (bank_transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return dict(
                receipt_transaction_id=r[0],
                scan_id=r[1],
                scan_filename=r[2],
                vendor_name=r[3],
                date=r[4].isoformat() if isinstance(r[4], datetime.date) else str(r[4]),
                total=float(r[5]),
            )
        except Exception as e:
            print(f"BankReceiptLinksRepository.get_receipt_link_info error: {e}")
            return None

    def get_bank_link_info(self, receipt_transaction_id: int):
        """Return enriched BankLinkInfo for displaying inside a receipt scan detail."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bt.id, bt.counterparty, bt.booking_date, bt.amount
                    FROM receipt_bank_links rbl
                    JOIN bank_transactions bt ON bt.id = rbl.bank_transaction_id
                    WHERE rbl.receipt_transaction_id = %s
                    """,
                    (receipt_transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return dict(
                bank_transaction_id=r[0],
                counterparty=r[1],
                booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                amount=float(r[3]),
            )
        except Exception as e:
            print(f"BankReceiptLinksRepository.get_bank_link_info error: {e}")
            return None

    def get_bank_tx_id_for_scan(self, scan_id: int) -> int | None:
        """Return the linked bank_transaction_id for the given scan, or None."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rbl.bank_transaction_id
                    FROM receipt_bank_links rbl
                    JOIN receipt_transactions rt ON rt.id = rbl.receipt_transaction_id
                    WHERE rt.scan_id = %s
                    LIMIT 1
                    """,
                    (scan_id,),
                )
                r = cur.fetchone()
            return r[0] if r else None
        except Exception as e:
            print(f"BankReceiptLinksRepository.get_bank_tx_id_for_scan error: {e}")
            return None

    def dispose(self) -> None:
        pass
