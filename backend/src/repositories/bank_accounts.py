"""Repository for bank_accounts table."""
from __future__ import annotations

from typing import Optional

from ..data import BankAccount, BankAccountStats


class BankAccountsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def list_with_stats(self) -> list[BankAccountStats]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        ba.id, ba.name, ba.bank_type, ba.color,
                        COALESCE(SUM(CASE WHEN bt.amount > 0 THEN bt.amount ELSE 0 END), 0.0) AS total_income,
                        COALESCE(SUM(CASE WHEN bt.amount < 0 THEN bt.amount ELSE 0 END), 0.0) AS total_expense,
                        COUNT(bt.id) AS transaction_count
                    FROM bank_accounts ba
                    LEFT JOIN bank_transactions bt ON bt.account_id = ba.id
                    GROUP BY ba.id, ba.name, ba.bank_type, ba.color
                    ORDER BY ba.id
                    """
                )
                rows = cur.fetchall()
            return [
                BankAccountStats(
                    id=r[0], name=r[1], bank_type=r[2], color=r[3],
                    total_income=float(r[4]),
                    total_expense=float(r[5]),
                    transaction_count=int(r[6]),
                )
                for r in rows
            ]
        except Exception as e:
            print(f"BankAccountsRepository.list_with_stats error: {e}")
            raise

    def get_by_id(self, account_id: int) -> Optional[BankAccount]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, bank_type, color FROM bank_accounts WHERE id = %s",
                    (account_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.get_by_id error: {e}")
            raise

    def create(self, name: str, bank_type: str, color: str) -> BankAccount:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bank_accounts (name, bank_type, color)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, bank_type, color
                    """,
                    (name, bank_type, color),
                )
                r = cur.fetchone()
            self.conn.commit()
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.create error: {e}")
            self.conn.rollback()
            raise

    def update(self, account_id: int, name: str, color: str) -> Optional[BankAccount]:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bank_accounts SET name = %s, color = %s WHERE id = %s
                    RETURNING id, name, bank_type, color
                    """,
                    (name, color, account_id),
                )
                r = cur.fetchone()
            self.conn.commit()
            if not r:
                return None
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.update error: {e}")
            self.conn.rollback()
            raise

    def has_transactions(self, account_id: int) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM bank_transactions WHERE account_id = %s",
                    (account_id,),
                )
                count = cur.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"BankAccountsRepository.has_transactions error: {e}")
            raise

    def delete(self, account_id: int) -> bool:
        """Delete account. Returns False if it has transactions (caller should 409)."""
        try:
            if self.has_transactions(account_id):
                return False
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM bank_accounts WHERE id = %s", (account_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"BankAccountsRepository.delete error: {e}")
            self.conn.rollback()
            raise

    def dispose(self) -> None:
        pass
