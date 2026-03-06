from abc import ABC

from ..data import CategoryItem


class CategoriesRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def create_category(self, name: str, parent_id: int | None) -> CategoryItem | None:
        """Insert a new leaf category."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                parent_name: str | None = None
                if parent_id is not None:
                    cursor.execute("SELECT name FROM categories WHERE id = %s", (parent_id,))
                    row = cursor.fetchone()
                    parent_name = row[0] if row else None

                # Check for existing category with same name and parent
                cursor.execute(
                    """
                    SELECT id, name, cp.name AS parent_name
                    FROM categories c
                    LEFT JOIN categories cp ON cp.id = c.parent_id
                    WHERE c.name = %s
                      AND (%s IS NULL OR c.parent_id = %s)
                    ORDER BY c.id DESC LIMIT 1
                    """,
                    (name, parent_id, parent_id),
                )
                existing = cursor.fetchone()
                if existing:
                    return CategoryItem(id=existing[0], name=existing[1], parent_name=existing[2])

                cursor.execute(
                    "INSERT INTO categories (parent_id, name, c_type) VALUES (%s, %s, 'expense') RETURNING id",
                    (parent_id, name),
                )
                new_id = cursor.fetchone()[0]
                self.conn.commit()
                return CategoryItem(id=new_id, name=name, parent_name=parent_name)
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
                            select c.id, c."name" as "category_name", cp."name" as "category_parent_name"
                            from categories c
                            left join categories cp on cp.id = c.parent_id
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
        """Return all expense categories with parent context."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.name, cp.name AS parent_name
                    FROM categories c
                    LEFT JOIN categories cp ON cp.id = c.parent_id
                    WHERE c.c_type = 'expense'
                    ORDER BY cp.name NULLS FIRST, c.name
                    """
                )
                rows = cursor.fetchall()
                return [
                    CategoryItem(id=r[0], name=r[1], parent_name=r[2])
                    for r in rows
                ]
        except Exception as e:
            print("Failed to fetch expense categories:", e)
            return []

    def dispose(self):
        pass
