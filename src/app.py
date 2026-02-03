from abc import ABC
import os

from src.db_contexts.my_money import MyMoneyDbContext
from src.services.preprocessing import PreprocessingService
from src.services.minio_storage import MinioStorageService
from src.services.evaluation import EvaluationService
from src.services.ground_truth import GroundTruthService
from .repositories.files import FilesRepository
from .services.ocr import OCRService
from .repositories.receipts_scans import ReceiptsScansRepository
from .repositories.evaluations import EvaluationsRepository
from .repositories.ground_truth import GroundTruthRepository
from .data import (
    ReceiptsScanStatus,
    TransactionModel,
    EvaluationRunSummary,
    GroundTruthResponse,
)
from .db_contexts.eye_budget import EyeBudgetDbContext
from .repositories.my_money import MyMoneyRepository


class App(ABC):
    def __init__(self):
        # Database contexts
        self.eye_budget_db_context = EyeBudgetDbContext()
        self.my_money_db_context = MyMoneyDbContext()
        
        # Repositories
        self.files_repository = FilesRepository()
        self.receipts_scans_repository = ReceiptsScansRepository(self.eye_budget_db_context)
        self.evaluations_repository = EvaluationsRepository(self.eye_budget_db_context)
        self.ground_truth_repository = GroundTruthRepository(self.eye_budget_db_context)
        self.my_money_repository = MyMoneyRepository(self.my_money_db_context)
        
        # Core services
        self.ocr_service = OCRService()
        self.preprocessing_service = PreprocessingService()
        self.minio_service = MinioStorageService()
        
        # High-level services
        self.evaluation_service = EvaluationService(
            evaluations_repository=self.evaluations_repository,
            ground_truth_repository=self.ground_truth_repository,
            minio_service=self.minio_service,
            preprocessing_service=self.preprocessing_service,
            ocr_service=self.ocr_service
        )
        self.ground_truth_service = GroundTruthService(
            ground_truth_repository=self.ground_truth_repository,
            minio_service=self.minio_service,
            preprocessing_service=self.preprocessing_service,
            ocr_service=self.ocr_service
        )

    def run(self, evaluate: bool = False) -> EvaluationRunSummary | None:
        """
        Run the receipt processing pipeline.
        
        Args:
            evaluate: If True, run evaluation against ground truth data.
                     Returns EvaluationRunSummary.
        
        Returns:
            EvaluationRunSummary if evaluate=True, None otherwise.
        """
        if evaluate:
            return self.evaluation_service.run_evaluation()
        else:
            self._run_production()
            return None

    def _run_production(self):
        """Run the standard production processing pipeline."""
        files = self.files_repository.list_input_files()
        if not files:
            print("No files to process.")
            return
        for file in files:
            added = self.receipts_scans_repository.add_receipt(file)
            if not added:
                print(f"File {file} already added.")
                continue
            try:
                print(f"Processing file: {file}")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSING)
                preprocessed_image_path = self.preprocessing_service.preprocess_image(file)
                ocr_result = self.ocr_service.process_image(preprocessed_image_path)
                self.receipts_scans_repository.set_result(file, ocr_result)
                print(f"File {file} processed successfully.")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSED)
                transaction_model = TransactionModel(**ocr_result)
                transaction_id = self.my_money_repository.insert_transaction(transaction_model)
                self.my_money_repository.transaction_has_attachment(transaction_id)
                self.files_repository.move_to_attachment_dir(
                    preprocessed_image_path,
                    f'{transaction_id}.{os.getenv("PREPROCESSED_IMAGE_EXTENSION")}'
                )
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.FAILED, e)

    # Ground Truth Methods (delegated to service)
    
    def create_ground_truth(self, filename: str, file_data: bytes) -> GroundTruthResponse:
        """Create a new ground truth entry by processing an uploaded image."""
        return self.ground_truth_service.create(filename, file_data)

    def update_ground_truth(self, entry_id: int, ground_truth: TransactionModel) -> GroundTruthResponse | None:
        """Update the ground truth data for an existing entry."""
        return self.ground_truth_service.update(entry_id, ground_truth)

    def get_ground_truth(self, entry_id: int) -> GroundTruthResponse | None:
        """Get a ground truth entry by ID."""
        return self.ground_truth_service.get(entry_id)

    def list_ground_truth(self) -> list[GroundTruthResponse]:
        """List all ground truth entries."""
        return self.ground_truth_service.list()

    def dispose(self):
        self.files_repository.dispose()
        self.receipts_scans_repository.dispose()
        self.evaluations_repository.dispose()
        self.ground_truth_repository.dispose()
        self.ocr_service.dispose()
        self.my_money_repository.dispose()
        self.minio_service.dispose()
        self.evaluation_service.dispose()
        self.ground_truth_service.dispose()
        self.my_money_db_context.dispose()
        self.eye_budget_db_context.dispose()
        print("All resources disposed.")
