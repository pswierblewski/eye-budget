from abc import ABC


class CategoryHistoryRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_category_counts(self, product_ids: list[int]) -> dict[int, dict[int, tuple[str, int]]]:
        """Confirmed category counts per normalized product.

        Legacy items may have product_id NULL; they are attributed through
        products_alternative_names by raw name.
        """
        if not self.conn or not product_ids:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(rti.product_id, pan.product) AS pid,
                           rti.category_id,
                           c.name,
                           COUNT(*)
                    FROM receipt_transaction_items rti
                    LEFT JOIN products_alternative_names pan ON pan.name = rti.raw_product_name
                    JOIN categories c ON c.id = rti.category_id
                    WHERE COALESCE(rti.product_id, pan.product) = ANY(%s)
                    GROUP BY 1, 2, 3
                    """,
                    (list(product_ids),),
                )
                result: dict[int, dict[int, tuple[str, int]]] = {}
                for product_id, category_id, category_name, count in cursor.fetchall():
                    result.setdefault(product_id, {})[category_id] = (category_name, int(count))
                return result
        except Exception as e:
            print("Failed to fetch category history:", e)
            self.conn.rollback()
            return {}

    def vendor_has_confirmed_receipts(self, vendor_id: int | None) -> bool:
        if not self.conn or vendor_id is None:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM receipt_transactions WHERE vendor_id = %s)",
                    (vendor_id,),
                )
                row = cursor.fetchone()
                return bool(row and row[0])
        except Exception as e:
            print("Failed to check vendor history:", e)
            self.conn.rollback()
            return False
