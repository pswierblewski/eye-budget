from abc import ABC
from typing import Optional

from ..data import VendorMapping


class VendorsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_vendor_by_name(self, vendor_name: str) -> Optional[int]:
        """
        Get vendor ID by its normalized name.
        
        Args:
            vendor_name: The normalized vendor name
            
        Returns:
            Vendor ID if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM vendors WHERE name = %s",
                    (vendor_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get vendor by name: {e}")
            return None

    def get_vendor_by_alternative_name(self, alternative_name: str) -> Optional[int]:
        """
        Get vendor ID by its alternative (receipt) name.
        
        Args:
            alternative_name: The vendor name as it appears on the receipt
            
        Returns:
            Vendor ID if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT vendor FROM vendors_alternative_names WHERE name = %s",
                    (alternative_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Failed to get vendor by alternative name: {e}")
            return None

    def insert_vendor(self, vendor_name: str) -> Optional[int]:
        """
        Insert a new vendor and return its ID.
        
        Args:
            vendor_name: The normalized vendor name
            
        Returns:
            The ID of the newly inserted vendor, or None if failed
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO vendors (name) VALUES (%s) RETURNING id",
                    (vendor_name,)
                )
                result = cursor.fetchone()
                self.conn.commit()
                if result:
                    print(f"Vendor '{vendor_name}' added successfully with ID {result[0]}.")
                    return result[0]
                return None
        except Exception as e:
            print(f"Failed to insert vendor: {e}")
            self.conn.rollback()
            return None

    def insert_alternative_name(self, alternative_name: str, vendor_id: int) -> bool:
        """
        Insert an alternative (receipt) name for a vendor.
        
        Args:
            alternative_name: The vendor name as it appears on the receipt
            vendor_id: The ID of the vendor this alternative name belongs to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO vendors_alternative_names (name, vendor) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING RETURNING id",
                    (alternative_name, vendor_id)
                )
                result = cursor.fetchone()
                self.conn.commit()
                if result:
                    print(f"Alternative name '{alternative_name}' added for vendor ID {vendor_id}.")
                    return True
                else:
                    print(f"Alternative name '{alternative_name}' already exists.")
                    return False
        except Exception as e:
            print(f"Failed to insert alternative name: {e}")
            self.conn.rollback()
            return False

    def process_vendor_mapping(self, mapping: VendorMapping) -> Optional[int]:
        """
        Process a vendor mapping and insert it into the database.
        This method checks if vendor exists, creates it if needed, and links the alternative name.
        
        Args:
            mapping: VendorMapping object
            
        Returns:
            Vendor ID if successful, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        
        try:
            # Check if alternative name already exists
            existing_vendor_id = self.get_vendor_by_alternative_name(mapping.vendor_alternative_name)
            
            if existing_vendor_id:
                print(f"Alternative name '{mapping.vendor_alternative_name}' already mapped to vendor ID {existing_vendor_id}.")
                return existing_vendor_id
            
            # Check if the normalized vendor name exists
            vendor_id = self.get_vendor_by_name(mapping.vendor_name)
            
            # If vendor doesn't exist, create it
            if not vendor_id:
                vendor_id = self.insert_vendor(mapping.vendor_name)
                if not vendor_id:
                    print(f"Failed to create vendor '{mapping.vendor_name}'.")
                    return None
            
            # Link the alternative name to the vendor
            self.insert_alternative_name(mapping.vendor_alternative_name, vendor_id)
            
            return vendor_id
            
        except Exception as e:
            print(f"Error processing vendor mapping '{mapping.vendor_alternative_name}': {e}")
            return None

    def dispose(self):
        """
        Dispose of the repository resources.
        """
        print("VendorsRepository disposed.")

