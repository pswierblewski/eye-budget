from abc import ABC
from psycopg2 import extras


class PromptAnalyticsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def upsert(
        self,
        scan_id: int,
        vendor_name: str | None,
        category_corrections_count: int,
        product_name_corrections_count: int,
        ocr_product_count: int,
        confirmed_product_count: int,
        details: dict,
    ) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO prompt_analytics
                        (scan_id, vendor_name, category_corrections_count,
                         product_name_corrections_count, ocr_product_count,
                         confirmed_product_count, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scan_id) DO UPDATE SET
                        vendor_name = EXCLUDED.vendor_name,
                        category_corrections_count = EXCLUDED.category_corrections_count,
                        product_name_corrections_count = EXCLUDED.product_name_corrections_count,
                        ocr_product_count = EXCLUDED.ocr_product_count,
                        confirmed_product_count = EXCLUDED.confirmed_product_count,
                        details = EXCLUDED.details,
                        created_at = NOW()
                    """,
                    (
                        scan_id,
                        vendor_name,
                        category_corrections_count,
                        product_name_corrections_count,
                        ocr_product_count,
                        confirmed_product_count,
                        extras.Json(details),
                    ),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to upsert prompt analytics:", e)
            self.conn.rollback()
            return False

    def get_summary(self) -> dict:
        """Return aggregated analytics: totals, correction rates, top confusions."""
        if not self.conn:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total_receipts,
                        SUM(category_corrections_count) AS total_category_corrections,
                        SUM(product_name_corrections_count) AS total_product_name_corrections,
                        SUM(CASE WHEN confirmed_product_count > ocr_product_count THEN 1 ELSE 0 END)
                            AS receipts_with_added_products,
                        SUM(CASE WHEN confirmed_product_count < ocr_product_count THEN 1 ELSE 0 END)
                            AS receipts_with_removed_products,
                        SUM(CASE WHEN confirmed_product_count != ocr_product_count THEN 1 ELSE 0 END)
                            AS receipts_with_product_count_mismatch,
                        AVG(category_corrections_count)::FLOAT AS avg_category_corrections,
                        AVG(product_name_corrections_count)::FLOAT AS avg_product_name_corrections,
                        AVG(ocr_product_count)::FLOAT AS avg_ocr_product_count
                    FROM prompt_analytics
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    return {}
                summary = {
                    "total_receipts": row[0] or 0,
                    "total_category_corrections": row[1] or 0,
                    "total_product_name_corrections": row[2] or 0,
                    "receipts_with_added_products": row[3] or 0,
                    "receipts_with_removed_products": row[4] or 0,
                    "receipts_with_product_count_mismatch": row[5] or 0,
                    "avg_category_corrections": round(row[6] or 0.0, 2),
                    "avg_product_name_corrections": round(row[7] or 0.0, 2),
                    "avg_ocr_product_count": round(row[8] or 0.0, 2),
                }

                # Top category confusion pairs
                cursor.execute(
                    """
                    SELECT
                        corr->>'ai_category_name' AS ai_cat,
                        corr->>'user_category_name' AS user_cat,
                        COUNT(*) AS cnt
                    FROM prompt_analytics,
                         jsonb_array_elements(details->'category_corrections') AS corr
                    GROUP BY ai_cat, user_cat
                    ORDER BY cnt DESC
                    LIMIT 20
                    """
                )
                summary["top_category_confusions"] = [
                    {
                        "ai_category_name": r[0],
                        "user_category_name": r[1],
                        "count": r[2],
                    }
                    for r in cursor.fetchall()
                ]

                # Top product name corrections
                cursor.execute(
                    """
                    SELECT
                        corr->>'ai_normalized_name' AS ai_name,
                        corr->>'user_normalized_name' AS user_name,
                        COUNT(*) AS cnt
                    FROM prompt_analytics,
                         jsonb_array_elements(details->'product_name_corrections') AS corr
                    GROUP BY ai_name, user_name
                    ORDER BY cnt DESC
                    LIMIT 20
                    """
                )
                summary["top_product_name_corrections"] = [
                    {
                        "ai_normalized_name": r[0],
                        "user_normalized_name": r[1],
                        "count": r[2],
                    }
                    for r in cursor.fetchall()
                ]

                return summary
        except Exception as e:
            print("Failed to get prompt analytics summary:", e)
            return {}

    def get_all(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return paginated list of analytics rows."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id, scan_id, vendor_name,
                        category_corrections_count, product_name_corrections_count,
                        ocr_product_count, confirmed_product_count,
                        details, created_at
                    FROM prompt_analytics
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                return [
                    {
                        "id": r[0],
                        "scan_id": r[1],
                        "vendor_name": r[2],
                        "category_corrections_count": r[3],
                        "product_name_corrections_count": r[4],
                        "ocr_product_count": r[5],
                        "confirmed_product_count": r[6],
                        "details": r[7],
                        "created_at": r[8].isoformat() if r[8] else None,
                    }
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            print("Failed to get prompt analytics list:", e)
            return []

    def dispose(self):
        pass
