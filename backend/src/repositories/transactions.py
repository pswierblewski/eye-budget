from abc import ABC
from datetime import date

from ..data import ReceiptTransaction, ReceiptTransactionItem


class TransactionsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def lookup_vendor_id(self, raw_vendor_name: str) -> int | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT vendor FROM vendors_alternative_names WHERE name = %s",
                    (raw_vendor_name,),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print("Failed to look up vendor id:", e)
            return None

    def lookup_product_id(self, raw_product_name: str) -> int | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT product FROM products_alternative_names WHERE name = %s",
                    (raw_product_name,),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print("Failed to look up product id:", e)
            return None

    def create_transaction(
        self,
        scan_id: int,
        vendor_id: int | None,
        raw_vendor_name: str,
        transaction_date: date,
        total: float,
    ) -> int:
        if not self.conn:
            return -1
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO receipt_transactions
                        (scan_id, vendor_id, raw_vendor_name, date, total)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (scan_id, vendor_id, raw_vendor_name, transaction_date, total),
                )
                transaction_id = cursor.fetchone()[0]
                self.conn.commit()
                return transaction_id
        except Exception as e:
            print("Failed to create transaction:", e)
            self.conn.rollback()
            return -1

    def create_transaction_item(
        self,
        transaction_id: int,
        product_id: int | None,
        raw_product_name: str,
        category_id: int,
        quantity: float,
        unit_price: float | None,
        price: float,
    ) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO receipt_transaction_items
                        (transaction_id, product_id, raw_product_name,
                         category_id, quantity, unit_price, price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (transaction_id, product_id, raw_product_name,
                     category_id, quantity, unit_price, price),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to create transaction item:", e)
            self.conn.rollback()
            return False

    def get_by_scan_id(self, scan_id: int) -> ReceiptTransaction | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rt.id, rt.vendor_id, rt.raw_vendor_name, rt.date, rt.total,
                           v.name AS normalized_vendor_name
                    FROM receipt_transactions rt
                    LEFT JOIN vendors v ON rt.vendor_id = v.id
                    WHERE rt.scan_id = %s
                    LIMIT 1
                    """,
                    (scan_id,),
                )
                tx_row = cursor.fetchone()
                if tx_row is None:
                    return None
                transaction_id = tx_row[0]
                cursor.execute(
                    """
                    SELECT rti.id, rti.product_id, rti.raw_product_name, rti.category_id,
                           rti.quantity, rti.unit_price, rti.price,
                           p.name AS normalized_product_name
                    FROM receipt_transaction_items rti
                    LEFT JOIN products p ON rti.product_id = p.id
                    WHERE rti.transaction_id = %s
                    ORDER BY rti.id
                    """,
                    (transaction_id,),
                )
                items = [
                    ReceiptTransactionItem(
                        id=r[0],
                        product_id=r[1],
                        raw_product_name=r[2],
                        category_id=r[3],
                        quantity=float(r[4]),
                        unit_price=float(r[5]) if r[5] is not None else None,
                        price=float(r[6]),
                        normalized_product_name=r[7],
                    )
                    for r in cursor.fetchall()
                ]
                return ReceiptTransaction(
                    id=transaction_id,
                    vendor_id=tx_row[1],
                    raw_vendor_name=tx_row[2],
                    normalized_vendor_name=tx_row[5],
                    date=str(tx_row[3]),
                    total=float(tx_row[4]),
                    items=items,
                )
        except Exception as e:
            print("Failed to fetch transaction by scan id:", e)
            return None

    def delete_by_scan_id(self, scan_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM receipt_transaction_items
                    WHERE transaction_id IN (
                        SELECT id FROM receipt_transactions WHERE scan_id = %s
                    )
                    """,
                    (scan_id,),
                )
                cursor.execute(
                    "DELETE FROM receipt_transactions WHERE scan_id = %s",
                    (scan_id,),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to delete transaction for scan:", e)
            self.conn.rollback()
            return False

    def dispose(self):
        print("TransactionsRepository disposed.")
