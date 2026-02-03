from abc import ABC
from typing import List, Optional

from ..data import ProductMapping


class ProductsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

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

    def dispose(self):
        """
        Dispose of the repository resources.
        """
        print("ProductsRepository disposed.")

