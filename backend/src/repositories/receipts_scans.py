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
        pass

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
        search: str | None = None,
        vendor: str | None = None,
        product: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        total_min: float | None = None,
        total_max: float | None = None,
        tag: str | None = None,
    ) -> tuple[list[ReceiptScanListItem], int]:
        _SORT_COLS: dict[str, str] = {
            "id": "rs.id",
            "filename": "rs.filename",
            "vendor": "COALESCE(v.name, rs.result->>'vendor')",
            "date": "rs.result->>'date'",
            "total": "(rs.result->>'total')::numeric",
            "status": "rs.status",
        }
        order_expr = _SORT_COLS.get(sort_by, "id")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        if not self.conn:
            return [], 0
        try:
            with self.conn.cursor() as cursor:
                conditions: list[str] = []
                params: list = []

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                if search:
                    conditions.append("(filename ILIKE %s OR result->>'vendor' ILIKE %s)")
                    params.extend([f"%{search}%", f"%{search}%"])

                if vendor:
                    conditions.append(
                        "(result->>'vendor' ILIKE %s"
                        " OR EXISTS ("
                        "   SELECT 1 FROM receipt_transactions rt"
                        "   LEFT JOIN vendors v ON v.id = rt.vendor_id"
                        "   WHERE rt.scan_id = rs.id"
                        "     AND (rt.raw_vendor_name ILIKE %s OR v.name ILIKE %s)"
                        " ))"
                    )
                    params.extend([f"%{vendor}%", f"%{vendor}%", f"%{vendor}%"])

                if product:
                    conditions.append(
                        "(EXISTS ("
                        "   SELECT 1 FROM jsonb_array_elements(rs.result->'products') AS p"
                        "   WHERE p->>'name' ILIKE %s"
                        " ) OR EXISTS ("
                        "   SELECT 1 FROM receipt_transactions rt"
                        "   JOIN receipt_transaction_items rti ON rti.transaction_id = rt.id"
                        "   LEFT JOIN products pr ON pr.id = rti.product_id"
                        "   WHERE rt.scan_id = rs.id"
                        "     AND (rti.raw_product_name ILIKE %s OR pr.name ILIKE %s)"
                        " ))"
                    )
                    params.extend([f"%{product}%", f"%{product}%", f"%{product}%"])

                if date_from:
                    conditions.append(
                        "(result->>'date' >= %s"
                        " OR EXISTS (SELECT 1 FROM receipt_transactions rt WHERE rt.scan_id = rs.id AND rt.date >= %s::date))"
                    )
                    params.extend([date_from, date_from])

                if date_to:
                    conditions.append(
                        "(result->>'date' <= %s"
                        " OR EXISTS (SELECT 1 FROM receipt_transactions rt WHERE rt.scan_id = rs.id AND rt.date <= %s::date))"
                    )
                    params.extend([date_to, date_to])

                if total_min is not None:
                    conditions.append(
                        "((result->>'total')::numeric >= %s"
                        " OR EXISTS (SELECT 1 FROM receipt_transactions rt WHERE rt.scan_id = rs.id AND rt.total >= %s))"
                    )
                    params.extend([total_min, total_min])

                if total_max is not None:
                    conditions.append(
                        "((result->>'total')::numeric <= %s"
                        " OR EXISTS (SELECT 1 FROM receipt_transactions rt WHERE rt.scan_id = rs.id AND rt.total <= %s))"
                    )
                    params.extend([total_max, total_max])

                if tag:
                    conditions.append("%s = ANY(rs.tags)")
                    params.append(tag)

                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

                cursor.execute(
                    f"""
                    SELECT rs.id, rs.filename, rs.status,
                           COALESCE(v.name, rs.result->>'vendor'),
                           rs.result->>'date',
                           rs.result->>'total',
                           rs.tags,
                           COUNT(*) OVER () AS total_count
                    FROM {self.table} rs
                    LEFT JOIN receipt_transactions rt ON rt.scan_id = rs.id
                    LEFT JOIN vendors v ON v.id = rt.vendor_id
                    {where}
                    ORDER BY {order_expr} {direction} NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cursor.fetchall()
                total = int(rows[0][7]) if rows else 0
                return [
                    ReceiptScanListItem(
                        id=row[0],
                        filename=row[1],
                        status=row[2],
                        vendor=row[3],
                        date=row[4],
                        total=float(row[5]) if row[5] is not None else None,
                        tags=list(row[6]) if row[6] else [],
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
                    SELECT id, filename, status, result, categories_candidates, minio_object_key, tags
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
                    tags=list(row[6]) if row[6] else [],
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

    def update_tags(self, scan_id: int, tags: list[str]) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET tags = %s WHERE id = %s",
                    (tags, scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to update tags:", e)
            self.conn.rollback()
            return False

    def get_tags_for_scan(self, scan_id: int) -> list[str]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT tags FROM " + self.table + " WHERE id = %s",
                    (scan_id,),
                )
                row = cursor.fetchone()
                return list(row[0]) if row and row[0] else []
        except Exception as e:
            print("Failed to get tags for scan:", e)
            return []