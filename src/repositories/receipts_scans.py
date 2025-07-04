from abc import ABC
from psycopg2 import extras

from data import ReceiptsScanStatus

class ReceiptsScansRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn
        self.table = '"receipts-scans"'

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
        
    def set_status(self, receipt_filename, status):
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s WHERE filename = %s",
                    (status, receipt_filename)
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
