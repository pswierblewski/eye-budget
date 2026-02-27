from abc import ABC
from psycopg2 import extras
from typing import Optional

from ..data import GroundTruthEntry, TransactionModel


class GroundTruthRepository(ABC):
    """Repository for managing ground truth data for evaluation."""
    
    def __init__(self, db_context):
        self.conn = db_context.conn

    def create(self, filename: str, minio_object_key: str, ground_truth: TransactionModel) -> int:
        """
        Create a new ground truth entry.
        
        Args:
            filename: Original filename of the receipt image
            minio_object_key: MinIO object key where the image is stored
            ground_truth: The transaction data (from OCR or corrected)
            
        Returns:
            The ID of the created entry, or -1 on failure
        """
        if not self.conn:
            print("No database connection available.")
            return -1
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO evaluation_ground_truth 
                    (filename, minio_object_key, ground_truth)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        filename,
                        minio_object_key,
                        extras.Json(ground_truth.model_dump())
                    )
                )
                entry_id = cursor.fetchone()[0]
                self.conn.commit()
                print(f"Ground truth entry {entry_id} created for {filename}.")
                return entry_id
        except Exception as e:
            print(f"Failed to create ground truth entry: {e}")
            self.conn.rollback()
            return -1

    def update(self, entry_id: int, ground_truth: TransactionModel) -> bool:
        """
        Update the ground truth data for an existing entry.
        
        Args:
            entry_id: The ID of the entry to update
            ground_truth: The corrected transaction data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE evaluation_ground_truth
                    SET ground_truth = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        extras.Json(ground_truth.model_dump()),
                        entry_id
                    )
                )
                if cursor.rowcount == 0:
                    print(f"Ground truth entry {entry_id} not found.")
                    return False
                self.conn.commit()
                print(f"Ground truth entry {entry_id} updated.")
                return True
        except Exception as e:
            print(f"Failed to update ground truth entry: {e}")
            self.conn.rollback()
            return False

    def get_by_filename(self, filename: str) -> Optional[GroundTruthEntry]:
        """
        Get a ground truth entry by filename.
        
        Args:
            filename: The original filename to search for
            
        Returns:
            GroundTruthEntry if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    WHERE filename = %s
                    LIMIT 1
                    """,
                    (filename,)
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_entry(row)
        except Exception as e:
            print(f"Failed to get ground truth entry by filename: {e}")
            return None

    def get_by_id(self, entry_id: int) -> Optional[GroundTruthEntry]:
        """
        Get a ground truth entry by ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
            
        Returns:
            GroundTruthEntry if found, None otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    WHERE id = %s
                    """,
                    (entry_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_entry(row)
        except Exception as e:
            print(f"Failed to get ground truth entry: {e}")
            return None

    def get_all(self) -> list[GroundTruthEntry]:
        """
        Get all ground truth entries.
        
        Returns:
            List of all GroundTruthEntry records
        """
        if not self.conn:
            print("No database connection available.")
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    ORDER BY id
                    """
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(row) for row in rows]
        except Exception as e:
            print(f"Failed to get ground truth entries: {e}")
            return []

    def _row_to_entry(self, row) -> GroundTruthEntry:
        """Convert a database row to a GroundTruthEntry."""
        return GroundTruthEntry(
            id=row[0],
            filename=row[1],
            minio_object_key=row[2],
            ground_truth=TransactionModel(**row[3]),
            created_at=row[4],
            updated_at=row[5]
        )

    def delete(self, entry_id: int) -> bool:
        """
        Delete a ground truth entry.
        
        Args:
            entry_id: The ID of the entry to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM evaluation_ground_truth
                    WHERE id = %s
                    RETURNING minio_object_key
                    """,
                    (entry_id,)
                )
                if cursor.rowcount == 0:
                    print(f"Ground truth entry {entry_id} not found.")
                    return False
                self.conn.commit()
                print(f"Ground truth entry {entry_id} deleted.")
                return True
        except Exception as e:
            print(f"Failed to delete ground truth entry: {e}")
            self.conn.rollback()
            return False

    def dispose(self):
        """Cleanup resources."""
        print("GroundTruthRepository disposed.")
