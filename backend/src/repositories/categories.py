from abc import ABC

from ..data import CategoryItem


class CategoriesRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_categories(self) -> list:
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                            select c.id, c."name" as "category_name", cp."name" as "category_parent_name", cg."name" as "category_group_name"
                            from categories c
                            left join categories cp on cp.id = c.parent_id
                            left join category_groups cg on cg.id = c.category_group_id
                            where c.c_type = 'expense'
                            """)
                categories = cursor.fetchall()
                self.conn.commit()
                return categories
        except Exception as e:
            print("Failed to fetch categories:", e)
            self.conn.rollback()
            return False

    def get_all_expense_categories(self) -> list[CategoryItem]:
        """Return all expense categories with parent and group context."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.name, cp.name AS parent_name, cg.name AS group_name
                    FROM categories c
                    LEFT JOIN categories cp ON cp.id = c.parent_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    WHERE c.c_type = 'expense'
                    ORDER BY cg.name, cp.name NULLS FIRST, c.name
                    """
                )
                rows = cursor.fetchall()
                return [
                    CategoryItem(id=r[0], name=r[1], parent_name=r[2], group_name=r[3])
                    for r in rows
                ]
        except Exception as e:
            print("Failed to fetch expense categories:", e)
            return []

    def dispose(self):
        print("CategoriesRepository disposed.")
