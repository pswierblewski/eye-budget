from abc import ABC
import os

from src.db_contexts.my_money import MyMoneyDbContext
from src.services.preprocessing import PreprocessingService
from .repositories.files import FilesRepository
from .services.ocr import OCRService
from .repositories.receipts_scans import ReceiptsScansRepository
from .data import ReceiptsScanStatus, TransactionModel
from .db_contexts.eye_budget import EyeBudgetDbContext
from .repositories.my_money import MyMoneyRepository


class App(ABC):
    def __init__(self):
        self.eye_budget_db_context = EyeBudgetDbContext()
        self.my_money_db_context = MyMoneyDbContext()
        self.files_repository = FilesRepository()
        self.receipts_scans_repository = ReceiptsScansRepository(self.eye_budget_db_context)
        self.ocr_service = OCRService()
        self.my_money_repository = MyMoneyRepository(self.my_money_db_context)
        self.preprocessing_service = PreprocessingService()
    
    def run(self):
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
                self.files_repository.move_to_attachment_dir(preprocessed_image_path, f'{transaction_id}.{os.getenv("PREPROCESSED_IMAGE_EXTENSION")}')
                return
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.FAILED, e)
                return
        
    def dispose(self):
        self.files_repository.dispose()
        self.receipts_scans_repository.dispose()
        self.ocr_service.dispose()
        self.my_money_repository.dispose()
        self.my_money_db_context.dispose()
        self.eye_budget_db_context.dispose()
        print("All resources disposed.")
        
        