from abc import ABC
from typing import List, Optional

from ..data import ProductMapping, NormalizedProductItem


class ProductsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_all_products(self) -> List[NormalizedProductItem]:
        """Return all normalized products ordered alphabetically."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM products ORDER BY name ASC")
                rows = cursor.fetchall()
                return [NormalizedProductItem(id=r[0], name=r[1]) for r in rows]
        except Exception as e:
            print(f"Failed to list products: {e}")
            return []

    def get_product_by_name(self, product_name: str) -> Optional[int]:
        """
        Get product ID by its normalized name.
        
        Args:
            product_name: The normalized product name
            
        Returns:
            Product ID if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM products WHERE name = %s",
                    (product_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get product by name: {e}")
            return None

    def get_product_by_alternative_name(self, alternative_name: str) -> Optional[int]:
        """
        Get product ID by its alternative (receipt) name.
        
        Args:
            alternative_name: The product name as it appears on the receipt
            
        Returns:
            Product ID if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT product FROM products_alternative_names WHERE name = %s",
                    (alternative_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get product by alternative name: {e}")
            return None

    def get_normalized_name_by_alternative_name(self, alternative_name: str) -> Optional[str]:
        """
        Return the normalized product name that a raw receipt name maps to.

        Args:
            alternative_name: The product name as it appears on the receipt

        Returns:
            Normalized product name if a mapping exists, None otherwise
        """
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.name
                    FROM products_alternative_names pan
                    JOIN products p ON p.id = pan.product
                    WHERE pan.name = %s
                    """,
                    (alternative_name,),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Failed to get normalized product name: {e}")
            return None

    def insert_product(self, product_name: str) -> Optional[int]:
        """
        Insert a new product and return its ID.
        
        Args:
            product_name: The normalized product name
            
        Returns:
            The ID of the newly inserted product, or None if failed
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO products (name) VALUES (%s) RETURNING id",
                    (product_name,)
                )
                result = cursor.fetchone()
                self.conn.commit()
                if result:
                    print(f"Product '{product_name}' added successfully with ID {result[0]}.")
                    return result[0]
                return None
        except Exception as e:
            print(f"Failed to insert product: {e}")
            self.conn.rollback()
            return None

    def insert_alternative_name(self, alternative_name: str, product_id: int) -> bool:
        """
        Insert an alternative (receipt) name for a product.
        
        Args:
            alternative_name: The product name as it appears on the receipt
            product_id: The ID of the product this alternative name belongs to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO products_alternative_names (name, product) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING RETURNING id",
                    (alternative_name, product_id)
                )
                result = cursor.fetchone()
                self.conn.commit()
                if result:
                    print(f"Alternative name '{alternative_name}' added for product ID {product_id}.")
                    return True
                else:
                    print(f"Alternative name '{alternative_name}' already exists.")
                    return False
        except Exception as e:
            print(f"Failed to insert alternative name: {e}")
            self.conn.rollback()
            return False

    def process_product_mappings(self, mappings: List[ProductMapping]) -> bool:
        """
        Process a list of product mappings and insert them into the database.
        This method checks if products exist, creates them if needed, and links alternative names.
        
        Args:
            mappings: List of ProductMapping objects
            
        Returns:
            True if all mappings were processed successfully, False otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return False
        
        success = True
        for mapping in mappings:
            try:
                # Check if alternative name already exists
                existing_product_id = self.get_product_by_alternative_name(mapping.product_alternative_name)
                
                if existing_product_id:
                    print(f"Alternative name '{mapping.product_alternative_name}' already mapped to product ID {existing_product_id}.")
                    continue
                
                # Check if the normalized product name exists
                product_id = self.get_product_by_name(mapping.product_name)
                
                # If product doesn't exist, create it
                if not product_id:
                    product_id = self.insert_product(mapping.product_name)
                    if not product_id:
                        print(f"Failed to create product '{mapping.product_name}'.")
                        success = False
                        continue
                
                # Link the alternative name to the product
                self.insert_alternative_name(mapping.product_alternative_name, product_id)
                
            except Exception as e:
                print(f"Error processing mapping '{mapping.product_alternative_name}': {e}")
                success = False
        
        return success

    def has_trigram_support(self) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')")
                row = cursor.fetchone()
                return bool(row and row[0])
        except Exception as e:
            print(f"Failed to check pg_trgm: {e}")
            self.conn.rollback()
            return False

    def find_similar_alternative_names(
        self, name: str, limit: int = 10, min_similarity: float = 0.3
    ) -> List[tuple[str, int, float]]:
        """Trigram search over raw receipt names. Raises when pg_trgm is unavailable."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT name, product, similarity(name, %s) AS score
                    FROM products_alternative_names
                    WHERE name %% %s AND similarity(name, %s) >= %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (name, name, name, min_similarity, limit),
                )
                return [(r[0], r[1], float(r[2])) for r in cursor.fetchall()]
        except Exception:
            self.conn.rollback()
            raise

    def get_all_alternative_names(self) -> List[tuple[str, int]]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT name, product FROM products_alternative_names")
                return [(r[0], r[1]) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Failed to list alternative names: {e}")
            self.conn.rollback()
            return []

    def get_names_by_ids(self, product_ids: List[int]) -> dict[int, str]:
        if not self.conn or not product_ids:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM products WHERE id = ANY(%s)", (list(product_ids),))
                return {r[0]: r[1] for r in cursor.fetchall()}
        except Exception as e:
            print(f"Failed to get product names: {e}")
            self.conn.rollback()
            return {}

    def upsert_alternative_name(self, alternative_name: str, product_id: int) -> bool:
        """Link a raw name to a product, replacing any previous mapping."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO products_alternative_names (name, product) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET product = EXCLUDED.product",
                    (alternative_name, product_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Failed to upsert alternative name: {e}")
            self.conn.rollback()
            return False

    def dispose(self):
        pass

