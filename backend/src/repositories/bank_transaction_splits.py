"""Repository for bank_transaction_category_splits table."""
from __future__ import annotations

from ..data import BankTransactionSplit, SplitItem


class BankTransactionSplitsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def upsert_splits(self, tx_id: int, splits: list[SplitItem]) -> list[BankTransactionSplit]:
        """Replace all splits for a transaction and clear category_id (invariant)."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM bank_transaction_category_splits WHERE bank_transaction_id = %s",
                    (tx_id,),
                )
                cur.execute(
                    "UPDATE bank_transactions SET category_id = NULL WHERE id = %s",
                    (tx_id,),
                )
                for split in splits:
                    cur.execute(
                        """
                        INSERT INTO bank_transaction_category_splits
                            (bank_transaction_id, category_id, amount)
                        VALUES (%s, %s, %s)
                        """,
                        (tx_id, split.category_id, split.amount),
                    )
            self.conn.commit()
            return self.get_splits(tx_id)
        except Exception:
            self.conn.rollback()
            raise

    def delete_splits(self, tx_id: int) -> bool:
        """Remove all splits for a transaction."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM bank_transaction_category_splits WHERE bank_transaction_id = %s",
                    (tx_id,),
                )
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    def get_splits(self, tx_id: int) -> list[BankTransactionSplit]:
        """Fetch all splits for a transaction with category names resolved."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.category_id, c.name AS category_name, s.amount
                    FROM bank_transaction_category_splits s
                    JOIN categories c ON c.id = s.category_id
                    WHERE s.bank_transaction_id = %s
                    ORDER BY s.id
                    """,
                    (tx_id,),
                )
                rows = cur.fetchall()
            return [
                BankTransactionSplit(
                    id=row[0],
                    category_id=row[1],
                    category_name=row[2],
                    amount=float(row[3]),
                )
                for row in rows
            ]
        except Exception as e:
            print(f"BankTransactionSplitsRepository.get_splits error: {e}")
            return []

    def dispose(self) -> None:
        pass
