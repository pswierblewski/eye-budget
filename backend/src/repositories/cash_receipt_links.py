"""
Repository for receipt_cash_links join table.

Links cash_transactions 1:1 with receipt_transactions.
Matching logic mirrors BankReceiptLinksRepository.
"""
from __future__ import annotations

import datetime
from typing import Optional


class CashReceiptLinksRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    # ------------------------------------------------------------------
    # Candidate queries
    # ------------------------------------------------------------------

    def find_receipt_candidates(self, cash_transaction_id: int) -> list[dict]:
        """
        Return receipt_transactions that match the given cash transaction by
        ABS(amount) = total and date ±2 days. Already-linked receipts excluded.
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
                            WHEN ct.vendor_id IS NOT NULL
                             AND rt.vendor_id IS NOT NULL
                             AND ct.vendor_id = rt.vendor_id  THEN 3
                            ELSE 2
                        END AS match_score
                    FROM cash_transactions ct
                    JOIN receipt_transactions rt
                      ON ABS(ct.amount) = rt.total
                     AND ct.booking_date BETWEEN rt.date - INTERVAL '2 days'
                                             AND rt.date + INTERVAL '2 days'
                    JOIN receipts_scans rs ON rs.id = rt.scan_id
                    LEFT JOIN vendors v ON v.id = rt.vendor_id
                    LEFT JOIN receipt_cash_links rcl ON rcl.receipt_transaction_id = rt.id
                    WHERE ct.id = %s
                      AND rcl.id IS NULL
                    ORDER BY match_score DESC, rt.date DESC
                    """,
                    (cash_transaction_id,),
                )
                rows = cur.fetchall()
            return [
                dict(
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
            print(f"CashReceiptLinksRepository.find_receipt_candidates error: {e}")
            return []

    def find_cash_tx_candidates(self, receipt_transaction_id: int) -> list[dict]:
        """
        Return cash_transactions that match the given receipt_transaction.
        """
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        ct.id,
                        ct.description,
                        ct.booking_date,
                        ct.amount,
                        CASE
                            WHEN ct.vendor_id IS NOT NULL
                             AND rt.vendor_id IS NOT NULL
                             AND ct.vendor_id = rt.vendor_id  THEN 3
                            ELSE 2
                        END AS match_score
                    FROM receipt_transactions rt
                    JOIN cash_transactions ct
                      ON ABS(ct.amount) = rt.total
                     AND ct.booking_date BETWEEN rt.date - INTERVAL '2 days'
                                             AND rt.date + INTERVAL '2 days'
                    LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                    WHERE rt.id = %s
                      AND rcl.id IS NULL
                    ORDER BY match_score DESC, ct.booking_date DESC
                    """,
                    (receipt_transaction_id,),
                )
                rows = cur.fetchall()
            return [
                dict(
                    cash_transaction_id=r[0],
                    description=r[1],
                    booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                    amount=float(r[3]),
                    match_score=r[4],
                )
                for r in rows
            ]
        except Exception as e:
            print(f"CashReceiptLinksRepository.find_cash_tx_candidates error: {e}")
            return []

    # ------------------------------------------------------------------
    # Link CRUD
    # ------------------------------------------------------------------

    def create_link(self, cash_transaction_id: int, receipt_transaction_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO receipt_cash_links (cash_transaction_id, receipt_transaction_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (cash_transaction_id, receipt_transaction_id),
                )
                result = cur.fetchone()
            self.conn.commit()
            return result is not None
        except Exception as e:
            print(f"CashReceiptLinksRepository.create_link error: {e}")
            self.conn.rollback()
            return False

    def delete_link_by_cash_tx(self, cash_transaction_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM receipt_cash_links WHERE cash_transaction_id = %s",
                    (cash_transaction_id,),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"CashReceiptLinksRepository.delete_link_by_cash_tx error: {e}")
            self.conn.rollback()
            return False

    def get_receipt_link_info(self, cash_transaction_id: int) -> Optional[dict]:
        """Return enriched receipt link info for a cash transaction detail."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rt.id, rs.id, rs.filename,
                           COALESCE(v.name, rt.raw_vendor_name),
                           rt.date, rt.total
                    FROM receipt_cash_links rcl
                    JOIN receipt_transactions rt ON rt.id = rcl.receipt_transaction_id
                    JOIN receipts_scans rs ON rs.id = rt.scan_id
                    LEFT JOIN vendors v ON v.id = rt.vendor_id
                    WHERE rcl.cash_transaction_id = %s
                    """,
                    (cash_transaction_id,),
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
            print(f"CashReceiptLinksRepository.get_receipt_link_info error: {e}")
            return None

    def get_cash_link_info(self, receipt_transaction_id: int) -> Optional[dict]:
        """Return enriched cash link info for a receipt scan detail."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ct.id, ct.description, ct.booking_date, ct.amount
                    FROM receipt_cash_links rcl
                    JOIN cash_transactions ct ON ct.id = rcl.cash_transaction_id
                    WHERE rcl.receipt_transaction_id = %s
                    """,
                    (receipt_transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return dict(
                cash_transaction_id=r[0],
                description=r[1],
                booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                amount=float(r[3]),
            )
        except Exception as e:
            print(f"CashReceiptLinksRepository.get_cash_link_info error: {e}")
            return None

    def get_cash_tx_id_for_scan(self, scan_id: int) -> Optional[int]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rcl.cash_transaction_id
                    FROM receipt_cash_links rcl
                    JOIN receipt_transactions rt ON rt.id = rcl.receipt_transaction_id
                    WHERE rt.scan_id = %s
                    LIMIT 1
                    """,
                    (scan_id,),
                )
                r = cur.fetchone()
            return r[0] if r else None
        except Exception as e:
            print(f"CashReceiptLinksRepository.get_cash_tx_id_for_scan error: {e}")
            return None

    def dispose(self) -> None:
        pass
