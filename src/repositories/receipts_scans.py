from abc import ABC
from dataclasses import dataclass

from psycopg2 import extras

from ..data import ReceiptsScanStatus, TransactionModel


@dataclass
class ProcessedScan:
    id: int
    filename: str
    transaction_model: TransactionModel


class ReceiptsScansRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn
        self.table = 'receipts_scans'

    def add_receipt(self, receipt_filename) -> bool:
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO " + self.table + " (filename) VALUES (%s) ON CONFLICT (filename) DO NOTHING RETURNING filename",
                    (receipt_filename,)
                )
                result = cursor.fetchone()
                self.conn.commit()
                if result:
                    print(f"Receipt {receipt_filename} added successfully.")
                    return True
                else:
                    print(f"Receipt {receipt_filename} already exists.")
                    return False
        except Exception as e:
            print("Failed to add receipt:", e)
            self.conn.rollback()
            return False
        
    def set_status(self, receipt_filename, status, error_message=None):
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s, message = %s WHERE filename = %s",
                    (status, error_message, receipt_filename)
                )
                self.conn.commit()
                print(f"Status for {receipt_filename} updated to {status}.")
                return True
        except Exception as e:
            print("Failed to update status:", e)
            self.conn.rollback()
            return False
    
    def set_category_candidates(self, receipt_filename, category_candidates):
        if not self.conn:
            print("No database connection available.")
            return False
        try:    
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET category_candidates = %s, status = %s WHERE filename = %s",
                    (extras.Json(category_candidates), ReceiptsScanStatus.TO_CONFIRM, receipt_filename)
                )
                self.conn.commit()
                print(f"Category candidates for {receipt_filename} updated successfully.")
                return True
        except Exception as e:
            print("Failed to update category candidates:", e)
            self.conn.rollback()
            return False
    
    def set_result(self, receipt_filename, result):
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET result = %s WHERE filename = %s",
                    (extras.Json(result), receipt_filename)
                )
                self.conn.commit()
                print(f"Result for {receipt_filename} updated successfully.")
                return True
        except Exception as e:
            print("Failed to update result:", e)
            self.conn.rollback()
            return False

    def get_scan_id_by_filename(self, filename: str) -> int | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM " + self.table + " WHERE filename = %s",
                    (filename,),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print("Failed to get scan id:", e)
            return None

    def get_processed_scans(self) -> list[ProcessedScan]:
        """Returns all scans with status 'processed' that have a non-null result."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, filename, result FROM " + self.table +
                    " WHERE status = %s AND result IS NOT NULL",
                    (ReceiptsScanStatus.PROCESSED,),
                )
                rows = cursor.fetchall()
                scans = []
                for row in rows:
                    try:
                        scans.append(ProcessedScan(
                            id=row[0],
                            filename=row[1],
                            transaction_model=TransactionModel(**row[2]),
                        ))
                    except Exception as e:
                        print(f"Skipping scan id={row[0]}: failed to parse result — {e}")
                return scans
        except Exception as e:
            print("Failed to fetch processed scans:", e)
            return []

    def dispose(self):
        print("ReceiptsScansRepository disposed.")