from abc import ABC


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
