"""
Repository for cash_transactions table.
"""
from __future__ import annotations

import datetime
from typing import Optional

from ..data import CashTransactionListItem, CashTransactionDetail


class CashTransactionsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def insert_transaction(
        self,
        booking_date: datetime.date,
        amount: float,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        source: str = "manual",
        receipt_scan_id: Optional[int] = None,
    ) -> Optional[int]:
        """Insert a new cash transaction.  Returns the new ID."""
        if not self.conn:
            return None
        status = "done" if category_id is not None else "to_confirm"
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cash_transactions
                        (booking_date, description, amount, category_id, vendor_id,
                         source, receipt_scan_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        booking_date,
                        description,
                        amount,
                        category_id,
                        vendor_id,
                        source,
                        receipt_scan_id,
                        status,
                    ),
                )
                row = cur.fetchone()
            self.conn.commit()
            return row[0] if row else None
        except Exception as e:
            print(f"CashTransactionsRepository.insert_transaction error: {e}")
            self.conn.rollback()
            return None

    def update(
        self,
        tx_id: int,
        booking_date: Optional[datetime.date] = None,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        category_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
    ) -> bool:
        """Partial update of a cash transaction."""
        if not self.conn:
            return False
        fields: list[str] = []
        params: list = []
        if booking_date is not None:
            fields.append("booking_date = %s")
            params.append(booking_date)
        if description is not None:
            fields.append("description = %s")
            params.append(description)
        if amount is not None:
            fields.append("amount = %s")
            params.append(amount)
        if category_id is not None:
            fields.append("category_id = %s")
            params.append(category_id)
        if vendor_id is not None:
            fields.append("vendor_id = %s")
            params.append(vendor_id)
        if not fields:
            return True
        params.append(tx_id)
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"UPDATE cash_transactions SET {', '.join(fields)} WHERE id = %s",
                    params,
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"CashTransactionsRepository.update error: {e}")
            self.conn.rollback()
            return False

    def confirm(self, tx_id: int, category_id: int) -> None:
        """Mark transaction as done and save chosen category."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE cash_transactions SET status = 'done', category_id = %s WHERE id = %s",
                    (category_id, tx_id),
                )
            self.conn.commit()
        except Exception as e:
            print(f"CashTransactionsRepository.confirm error: {e}")
            self.conn.rollback()

    def reopen(self, tx_id: int) -> None:
        """Reset transaction back to to_confirm, clearing confirmed category."""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE cash_transactions SET status = 'to_confirm', category_id = NULL WHERE id = %s",
                    (tx_id,),
                )
            self.conn.commit()
        except Exception as e:
            print(f"CashTransactionsRepository.reopen error: {e}")
            self.conn.rollback()

    def delete(self, tx_id: int) -> bool:
        """Delete a cash transaction."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM cash_transactions WHERE id = %s", (tx_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"CashTransactionsRepository.delete error: {e}")
            self.conn.rollback()
            return False

    def update_tags(self, tx_id: int, tags: list[str]) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE cash_transactions SET tags = %s WHERE id = %s",
                    (tags, tx_id),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"CashTransactionsRepository.update_tags error: {e}")
            self.conn.rollback()
            return False

    def get_tags_for_tx(self, tx_id: int) -> list[str]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT tags FROM cash_transactions WHERE id = %s",
                    (tx_id,),
                )
                row = cur.fetchone()
                return list(row[0]) if row and row[0] else []
        except Exception as e:
            print(f"CashTransactionsRepository.get_tags_for_tx error: {e}")
            return []

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "booking_date",
        sort_dir: str = "desc",
        tag: Optional[str] = None,
    ) -> tuple[list[CashTransactionListItem], int]:
        _SORT_COLS: dict[str, str] = {
            "id": "ct.id",
            "booking_date": "ct.booking_date",
            "description": "ct.description",
            "amount": "ct.amount",
            "category_name": "c.name",
            "status": "ct.status",
        }
        order_expr = _SORT_COLS.get(sort_by, "ct.booking_date")
        secondary = "ct.id DESC" if order_expr != "ct.id" else ""
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        order_clause = f"{order_expr} {direction} NULLS LAST" + (f", {secondary}" if secondary else "")
        if not self.conn:
            return [], 0
        try:
            with self.conn.cursor() as cur:
                conditions: list[str] = []
                params: list = []
                if status:
                    conditions.append("ct.status = %s")
                    params.append(status)
                if tag:
                    conditions.append("%s = ANY(ct.tags)")
                    params.append(tag)
                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
                cur.execute(
                    f"""
                    SELECT ct.id, ct.booking_date, ct.description, ct.amount, ct.currency,
                           ct.status, ct.source, ct.category_id, c.name AS category_name,
                           cg.name AS category_group_name,
                           ct.vendor_id, v.name AS vendor_name,
                           ct.tags,
                           COUNT(*) OVER () AS total_count
                    FROM cash_transactions ct
                    LEFT JOIN categories c   ON c.id = ct.category_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    LEFT JOIN vendors v       ON v.id = ct.vendor_id
                    {where}
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cur.fetchall()
            total = int(rows[0][13]) if rows else 0
            return [
                CashTransactionListItem(
                    id=r[0],
                    booking_date=r[1].isoformat() if isinstance(r[1], datetime.date) else str(r[1]),
                    description=r[2],
                    amount=float(r[3]),
                    currency=r[4],
                    status=r[5],
                    source=r[6],
                    category_id=r[7],
                    category_name=r[8],
                    category_group_name=r[9],
                    vendor_id=r[10],
                    vendor_name=r[11],
                    tags=list(r[12]) if r[12] else [],
                )
                for r in rows
            ], total
        except Exception as e:
            print(f"CashTransactionsRepository.get_list error: {e}")
            return [], 0

    def get_status_counts(self) -> dict[str, int]:
        if not self.conn:
            return {}
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT status, COUNT(*) FROM cash_transactions GROUP BY status")
                rows = cur.fetchall()
                return {row[0]: int(row[1]) for row in rows}
        except Exception as e:
            print(f"CashTransactionsRepository.get_status_counts error: {e}")
            return {}

    def get_by_id(self, tx_id: int) -> Optional[CashTransactionDetail]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ct.id, ct.booking_date, ct.description, ct.amount, ct.currency,
                           ct.status, ct.source, ct.category_id, c.name AS category_name,
                           cg.name AS category_group_name,
                           ct.vendor_id, v.name AS vendor_name,
                           ct.tags, ct.receipt_scan_id
                    FROM cash_transactions ct
                    LEFT JOIN categories c    ON c.id = ct.category_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    LEFT JOIN vendors v        ON v.id = ct.vendor_id
                    WHERE ct.id = %s
                    """,
                    (tx_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return CashTransactionDetail(
                id=r[0],
                booking_date=r[1].isoformat() if isinstance(r[1], datetime.date) else str(r[1]),
                description=r[2],
                amount=float(r[3]),
                currency=r[4],
                status=r[5],
                source=r[6],
                category_id=r[7],
                category_name=r[8],
                category_group_name=r[9],
                vendor_id=r[10],
                vendor_name=r[11],
                tags=list(r[12]) if r[12] else [],
                receipt_scan_id=r[13],
            )
        except Exception as e:
            print(f"CashTransactionsRepository.get_by_id error: {e}")
            return None

    def dispose(self) -> None:
        pass
