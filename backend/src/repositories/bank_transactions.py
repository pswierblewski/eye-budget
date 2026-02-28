"""
Repository for bank_transactions table.
"""
from __future__ import annotations

import datetime
import json
from decimal import Decimal
from typing import Optional

from ..data import BankTransactionListItem, BankTransactionDetail
from ..services.bank_csv_parser import BankTransactionRow


class BankTransactionsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def insert_transactions(self, rows: list[BankTransactionRow]) -> tuple[int, int]:
        """Bulk-insert parsed CSV rows.  Returns (inserted, duplicates)."""
        if not self.conn or not rows:
            return 0, 0
        inserted = 0
        duplicates = 0
        try:
            with self.conn.cursor() as cur:
                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO bank_transactions
                            (reference_number, booking_date, value_date, counterparty,
                             counterparty_address, source_account, target_account,
                             description, amount, currency, operation_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (reference_number) DO NOTHING
                        RETURNING id
                        """,
                        (
                            row.reference_number,
                            row.booking_date,
                            row.value_date,
                            row.counterparty,
                            row.counterparty_address,
                            row.source_account,
                            row.target_account,
                            row.description,
                            float(row.amount),
                            row.currency,
                            row.operation_type,
                        ),
                    )
                    result = cur.fetchone()
                    if result:
                        inserted += 1
                    else:
                        duplicates += 1
            self.conn.commit()
        except Exception as e:
            print(f"BankTransactionsRepository.insert_transactions error: {e}")
            self.conn.rollback()
        return inserted, duplicates

    def update_candidates(self, transaction_id: int, candidates: list) -> None:
        """Persist LLM category candidates JSON."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE bank_transactions SET category_candidates = %s WHERE id = %s",
                    (json.dumps(candidates), transaction_id),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BankTransactionsRepository.update_candidates error: {e}")
            self.conn.rollback()

    def confirm(self, transaction_id: int, category_id: int) -> None:
        """Mark transaction as done and save chosen category."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE bank_transactions SET status = 'done', category_id = %s WHERE id = %s",
                    (category_id, transaction_id),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BankTransactionsRepository.confirm error: {e}")
            self.conn.rollback()

    def reopen(self, transaction_id: int) -> None:
        """Reset transaction back to to_confirm, clearing confirmed category."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE bank_transactions SET status = 'to_confirm', category_id = NULL WHERE id = %s",
                    (transaction_id,),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BankTransactionsRepository.reopen error: {e}")
            self.conn.rollback()

    def link_vendor(self, transaction_id: int, vendor_id: int) -> None:
        """Associate a normalized vendor with this transaction."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE bank_transactions SET vendor_id = %s WHERE id = %s",
                    (vendor_id, transaction_id),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BankTransactionsRepository.link_vendor error: {e}")
            self.conn.rollback()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_list(self, status: Optional[str] = None) -> list[BankTransactionListItem]:
        """Return all transactions (optionally filtered by status), newest first."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                if status:
                    cur.execute(
                        """
                        SELECT bt.id, bt.reference_number, bt.booking_date,
                               bt.counterparty, bt.description, bt.amount, bt.currency,
                               bt.operation_type, bt.status, bt.category_id, c.name
                        FROM bank_transactions bt
                        LEFT JOIN categories c ON c.id = bt.category_id
                        WHERE bt.status = %s
                        ORDER BY bt.booking_date DESC, bt.id DESC
                        """,
                        (status,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT bt.id, bt.reference_number, bt.booking_date,
                               bt.counterparty, bt.description, bt.amount, bt.currency,
                               bt.operation_type, bt.status, bt.category_id, c.name
                        FROM bank_transactions bt
                        LEFT JOIN categories c ON c.id = bt.category_id
                        ORDER BY bt.booking_date DESC, bt.id DESC
                        """
                    )
                rows = cur.fetchall()
            return [
                BankTransactionListItem(
                    id=r[0],
                    reference_number=r[1],
                    booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                    counterparty=r[3],
                    description=r[4],
                    amount=float(r[5]),
                    currency=r[6],
                    operation_type=r[7],
                    status=r[8],
                    category_id=r[9],
                    category_name=r[10],
                )
                for r in rows
            ]
        except Exception as e:
            print(f"BankTransactionsRepository.get_list error: {e}")
            return []

    def get_by_id(self, transaction_id: int) -> Optional[BankTransactionDetail]:
        """Return full detail for a single transaction."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bt.id, bt.reference_number, bt.booking_date, bt.value_date,
                           bt.counterparty, bt.counterparty_address, bt.source_account,
                           bt.target_account, bt.description, bt.amount, bt.currency,
                           bt.operation_type, bt.status, bt.category_id, c.name,
                           bt.category_candidates, bt.vendor_id
                    FROM bank_transactions bt
                    LEFT JOIN categories c ON c.id = bt.category_id
                    WHERE bt.id = %s
                    """,
                    (transaction_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return BankTransactionDetail(
                id=r[0],
                reference_number=r[1],
                booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                value_date=r[3].isoformat() if isinstance(r[3], datetime.date) else (str(r[3]) if r[3] else None),
                counterparty=r[4],
                counterparty_address=r[5],
                source_account=r[6],
                target_account=r[7],
                description=r[8],
                amount=float(r[9]),
                currency=r[10],
                operation_type=r[11],
                status=r[12],
                category_id=r[13],
                category_name=r[14],
                category_candidates=r[15],
                vendor_id=r[16],
            )
        except Exception as e:
            print(f"BankTransactionsRepository.get_by_id error: {e}")
            return None

    def get_new_ids_for_categorization(self) -> list[int]:
        """Return IDs of transactions that have been inserted but not yet categorized."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM bank_transactions WHERE category_candidates IS NULL ORDER BY id"
                )
                return [r[0] for r in cur.fetchall()]
        except Exception as e:
            print(f"BankTransactionsRepository.get_new_ids_for_categorization error: {e}")
            return []

    # ------------------------------------------------------------------
    # Context queries for LLM
    # ------------------------------------------------------------------

    def get_confirmed_by_counterparty(
        self, counterparty_pattern: str, limit: int = 5
    ) -> list[dict]:
        """
        Return up to `limit` confirmed bank transactions whose counterparty
        matches (case-insensitive, ILIKE) the given pattern.

        Used to provide historical context to the LLM.
        """
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bt.counterparty, bt.description, bt.operation_type,
                           bt.amount, c.name AS category_name
                    FROM bank_transactions bt
                    JOIN categories c ON c.id = bt.category_id
                    WHERE bt.status = 'done'
                      AND bt.counterparty ILIKE %s
                    ORDER BY bt.booking_date DESC
                    LIMIT %s
                    """,
                    (f"%{counterparty_pattern}%", limit),
                )
                rows = cur.fetchall()
            return [
                {
                    "counterparty": r[0],
                    "description": r[1],
                    "operation_type": r[2],
                    "amount": float(r[3]),
                    "category": r[4],
                }
                for r in rows
            ]
        except Exception as e:
            print(f"BankTransactionsRepository.get_confirmed_by_counterparty error: {e}")
            return []

    def dispose(self) -> None:
        pass
