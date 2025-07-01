import os
import psycopg2
from psycopg2 import extras

class ReceiptsScansRepository:
    def __init__(self):
        self.conn = None
        self.connect_db()
        self.table = '"receipts_scans"'
    
    def dispose(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
        else:
            print("No database connection to close.")
            
    def connect_db(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRESQL_HOST"),
                port=os.getenv("POSTGRESQL_PORT"),
                dbname=os.getenv("POSTGRESQL_DB"),
                user=os.getenv("POSTGRESQL_USER"),
                password=os.getenv("POSTGRESQL_PASSWORD")
            )
            print("Database connection established.")
        except Exception as e:
            print("Failed to connect to database:", e)

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
