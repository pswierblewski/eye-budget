from abc import ABC

from ..data import CategoryItem


class CategoriesRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_all_groups(self) -> list[str]:
        """Return distinct category group names ordered alphabetically."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT name FROM category_groups ORDER BY name ASC")
                return [r[0] for r in cursor.fetchall()]
        except Exception as e:
            print("Failed to fetch category groups:", e)
            return []

    def create_category(self, name: str, group_name: str, parent_id: int | None) -> CategoryItem | None:
        """Insert a new leaf category using the existing DB helper function."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                # Resolve parent name for the SQL function
                parent_name: str | None = None
                if parent_id is not None:
                    cursor.execute("SELECT name FROM categories WHERE id = %s", (parent_id,))
                    row = cursor.fetchone()
                    parent_name = row[0] if row else None

                cursor.execute(
                    "SELECT insert_category(%s, %s, %s, 'expense'::category_type)",
                    (parent_name, name, group_name),
                )
                self.conn.commit()

                # Fetch the newly created (or already-existing) category
                cursor.execute(
                    """
                    SELECT c.id, c.name, cp.name AS parent_name, cg.name AS group_name
                    FROM categories c
                    LEFT JOIN categories cp ON cp.id = c.parent_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    WHERE c.name = %s AND cg.name = %s
                      AND (%s IS NULL OR cp.id = %s)
                    ORDER BY c.id DESC LIMIT 1
                    """,
                    (name, group_name, parent_id, parent_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return CategoryItem(id=row[0], name=row[1], parent_name=row[2], group_name=row[3])
        except Exception as e:
            print("Failed to create category:", e)
            self.conn.rollback()
            return None

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
        pass