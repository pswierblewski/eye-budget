import os
import uuid

from ..data import (
    TransactionModel,
    GroundTruthResponse,
)
from ..repositories.ground_truth import GroundTruthRepository
from .minio_storage import MinioStorageService
from .preprocessing import PreprocessingService
from .ocr import OCRService


class GroundTruthService:
    """Service for managing ground truth data for evaluation."""
    
    def __init__(
        self,
        ground_truth_repository: GroundTruthRepository,
        minio_service: MinioStorageService,
        preprocessing_service: PreprocessingService,
        ocr_service: OCRService
    ):
        self.ground_truth_repository = ground_truth_repository
        self.minio_service = minio_service
        self.preprocessing_service = preprocessing_service
        self.ocr_service = ocr_service

    def create(self, filename: str, file_data: bytes) -> GroundTruthResponse:
        """
        Create a new ground truth entry by processing an uploaded image.
        
        Args:
            filename: Original filename of the uploaded image
            file_data: Binary image data
            
        Returns:
            GroundTruthResponse with the created entry
        """
        # Generate a unique object key for MinIO
        temp_id = str(uuid.uuid4())[:8]
        object_key = f"ground-truth/{temp_id}_{filename}"
        
        # Upload image to MinIO
        self.minio_service.upload_image(file_data, object_key)
        
        # Download to temp file for OCR processing
        temp_path = self.minio_service.get_temp_file(object_key)
        
        try:
            # Run OCR preprocessing and processing
            preprocessed_path = self.preprocessing_service.preprocess_image(temp_path)
            ocr_result = self.ocr_service.process_image(preprocessed_path)
            transaction = TransactionModel(**ocr_result)
            
            # Store in database
            entry_id = self.ground_truth_repository.create(
                filename=filename,
                minio_object_key=object_key,
                ground_truth=transaction
            )
            
            if entry_id == -1:
                raise Exception("Failed to create ground truth entry in database")
            
            return GroundTruthResponse(
                id=entry_id,
                filename=filename,
                ground_truth=transaction
            )
        finally:
            # Cleanup temp files
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def update(self, entry_id: int, ground_truth: TransactionModel) -> GroundTruthResponse | None:
        """
        Update the ground truth data for an existing entry.
        
        Args:
            entry_id: The ID of the entry to update
            ground_truth: The corrected transaction data
            
        Returns:
            GroundTruthResponse if successful, None otherwise
        """
        # First check if entry exists
        entry = self.ground_truth_repository.get_by_id(entry_id)
        if entry is None:
            print(f"Ground truth entry {entry_id} not found.")
            return None
        
        # Update the ground truth data
        success = self.ground_truth_repository.update(entry_id, ground_truth)
        if not success:
            return None
        
        return GroundTruthResponse(
            id=entry_id,
            filename=entry.filename,
            ground_truth=ground_truth
        )

    def get(self, entry_id: int) -> GroundTruthResponse | None:
        """
        Get a ground truth entry by ID.
        
        Args:
            entry_id: The ID of the entry to retrieve
            
        Returns:
            GroundTruthResponse if found, None otherwise
        """
        entry = self.ground_truth_repository.get_by_id(entry_id)
        if entry is None:
            return None
        
        return GroundTruthResponse(
            id=entry.id,
            filename=entry.filename,
            ground_truth=entry.ground_truth
        )

    def list(self) -> list[GroundTruthResponse]:
        """
        List all ground truth entries.
        
        Returns:
            List of GroundTruthResponse for all entries
        """
        entries = self.ground_truth_repository.get_all()
        return [
            GroundTruthResponse(
                id=entry.id,
                filename=entry.filename,
                ground_truth=entry.ground_truth
            )
            for entry in entries
        ]

    def dispose(self):
        """Cleanup resources."""
        print("GroundTruthService disposed.")
