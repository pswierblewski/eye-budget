import os
import tempfile
from io import BytesIO

from minio import Minio
from minio.error import S3Error


class MinioStorageService:
    """Service for storing and retrieving images from MinIO."""
    
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT")
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        self.bucket = os.getenv("MINIO_BUCKET", "eye-budget")
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure the bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")
            raise
    
    def upload_image(self, file_data: bytes, object_name: str, content_type: str = "image/png") -> str:
        """
        Upload image to MinIO.
        
        Args:
            file_data: Binary image data
            object_name: Object key/name in MinIO (e.g., "ground-truth/1_receipt.png")
            content_type: MIME type of the image
            
        Returns:
            The object name/key that was uploaded
        """
        try:
            data = BytesIO(file_data)
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length=len(file_data),
                content_type=content_type
            )
            print(f"Uploaded to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            print(f"Error uploading to MinIO: {e}")
            raise
    
    def download_image(self, object_name: str) -> bytes:
        """
        Download image from MinIO.
        
        Args:
            object_name: Object key/name in MinIO
            
        Returns:
            Binary image data
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            print(f"Error downloading from MinIO: {e}")
            raise
    
    def get_temp_file(self, object_name: str) -> str:
        """
        Download image to a temporary file and return the path.
        Useful for OCR processing which requires a file path.
        
        Args:
            object_name: Object key/name in MinIO
            
        Returns:
            Path to temporary file containing the image
        """
        data = self.download_image(object_name)
        
        # Get file extension from object name
        _, ext = os.path.splitext(object_name)
        if not ext:
            ext = ".png"
        
        # Create temp file with proper extension
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        
        return temp_path
    
    def delete_image(self, object_name: str) -> bool:
        """
        Delete image from MinIO.
        
        Args:
            object_name: Object key/name in MinIO
            
        Returns:
            True if successful
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            print(f"Deleted from MinIO: {object_name}")
            return True
        except S3Error as e:
            print(f"Error deleting from MinIO: {e}")
            return False
    
    def dispose(self):
        """Cleanup resources."""
        print("MinioStorageService disposed.")
