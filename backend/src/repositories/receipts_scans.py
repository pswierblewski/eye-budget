from abc import ABC
from dataclasses import dataclass

from psycopg2 import extras

from ..data import (
    ReceiptsScanStatus,
    TransactionModel,
    ReceiptScanListItem,
    ReceiptScanDetail,
)


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
        # Ensure error_message is a plain string — exception objects cannot be
        # serialised by psycopg2 and will raise "can't adapt type '...'".
        if error_message is not None and not isinstance(error_message, str):
            error_message = str(error_message)
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
                    "UPDATE " + self.table + " SET categories_candidates = %s, status = %s WHERE filename = %s",
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

    # ------------------------------------------------------------------
    # New methods for the review/confirm API
    # ------------------------------------------------------------------

    def set_minio_key(self, filename: str, key: str) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET minio_object_key = %s WHERE filename = %s",
                    (key, filename),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to set minio key:", e)
            self.conn.rollback()
            return False

    def set_status_done(self, scan_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s WHERE id = %s",
                    (ReceiptsScanStatus.DONE, scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to set status to done:", e)
            self.conn.rollback()
            return False

    def set_status_to_confirm_by_id(self, scan_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s WHERE id = %s",
                    (ReceiptsScanStatus.TO_CONFIRM, scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to reset status to to_confirm:", e)
            self.conn.rollback()
            return False

    def set_result_by_id(self, scan_id: int, result: dict) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET result = %s WHERE id = %s",
                    (extras.Json(result), scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to update result by id:", e)
            self.conn.rollback()
            return False

    def get_all(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "id",
        sort_dir: str = "desc",
    ) -> tuple[list[ReceiptScanListItem], int]:
        _SORT_COLS: dict[str, str] = {
            "id": "id",
            "filename": "filename",
            "vendor": "result->>'vendor'",
            "date": "result->>'date'",
            "total": "(result->>'total')::numeric",
            "status": "status",
        }
        order_expr = _SORT_COLS.get(sort_by, "id")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        if not self.conn:
            return [], 0
        try:
            with self.conn.cursor() as cursor:
                where = "WHERE status = %s" if status else ""
                params: list = [status] if status else []
                cursor.execute(
                    f"""
                    SELECT id, filename, status,
                           result->>'vendor',
                           result->>'date',
                           result->>'total',
                           COUNT(*) OVER () AS total_count
                    FROM {self.table}
                    {where}
                    ORDER BY {order_expr} {direction} NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cursor.fetchall()
                total = int(rows[0][6]) if rows else 0
                return [
                    ReceiptScanListItem(
                        id=row[0],
                        filename=row[1],
                        status=row[2],
                        vendor=row[3],
                        date=row[4],
                        total=float(row[5]) if row[5] is not None else None,
                    )
                    for row in rows
                ], total
        except Exception as e:
            print("Failed to fetch all scans:", e)
            return [], 0

    def get_status_counts(self) -> dict[str, int]:
        """Return count per status for all receipt scans."""
        if not self.conn:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status, COUNT(*) FROM " + self.table + " GROUP BY status"
                )
                rows = cursor.fetchall()
                return {row[0]: int(row[1]) for row in rows}
        except Exception as e:
            print("Failed to fetch status counts:", e)
            return {}

    def get_by_id(self, scan_id: int) -> ReceiptScanDetail | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, status, result, categories_candidates, minio_object_key
                    FROM """ + self.table + """
                    WHERE id = %s
                    """,
                    (scan_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                result_model: TransactionModel | None = None
                if row[3]:
                    try:
                        result_model = TransactionModel(**row[3])
                    except Exception:
                        pass
                return ReceiptScanDetail(
                    id=row[0],
                    filename=row[1],
                    status=row[2],
                    result=result_model,
                    categories_candidates=row[4],
                    minio_object_key=row[5],
                    transaction=None,  # populated by endpoint handler
                )
        except Exception as e:
            print("Failed to fetch scan by id:", e)
            return None

    def delete_scan_by_id(self, scan_id: int) -> bool:
        """Delete a scan row by ID. FK cleanup (transactions, links) must be done by caller."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM " + self.table + " WHERE id = %s",
                    (scan_id,),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to delete scan:", e)
            self.conn.rollback()
            return False

    def reset_for_retry(self, scan_id: int) -> str | None:
        """
        Reset a scan so it can be re-processed by the pipeline.

        Clears result, categories_candidates and message, and sets status to
        PROCESSING.  Returns the filename on success, None if the scan was
        not found or an error occurred.
        """
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE """ + self.table + """
                    SET status = %s,
                        result = NULL,
                        categories_candidates = NULL,
                        message = NULL
                    WHERE id = %s
                    RETURNING filename
                    """,
                    (ReceiptsScanStatus.PROCESSING, scan_id),
                )
                row = cursor.fetchone()
                self.conn.commit()
                return row[0] if row else None
        except Exception as e:
            print("Failed to reset scan for retry:", e)
            self.conn.rollback()
            return None