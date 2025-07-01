from abc import ABC
from repositories.receipts import ReceiptsRepository
from repositories.files import FilesRepository
from services.ocr import OCRService
from repositories.receipts_scans import ReceiptsScansRepository
from data import ReceiptsScanStatus, TransactionModel

class App(ABC):
    def __init__(self):
        self.receipts_repository = ReceiptsRepository()
        self.files_repository = FilesRepository()
        self.receipts_scans_repository = ReceiptsScansRepository()
        self.ocr_service = OCRService()
    
    def run(self):
        self.receipts_repository.download_receipts()
        files = self.files_repository.list_input_files()
        if not files:
            print("No files to process.")
            return
        for file in files:
            added = self.receipts_scans_repository.add_receipt(file)
            if added:
                try:
                    print(f"Processing file: {file}")
                    self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSING)
                    ocr_result = self.ocr_service.process_image(file)
                    self.receipts_scans_repository.set_result(file, ocr_result)
                    print(f"File {file} processed successfully.")
                    self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSED)
                    transaction_model = TransactionModel(**ocr_result)
                    return
                except Exception as e:
                    print(f"Error processing file {file}: {e}")
                    self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.FAILED)
                    return
        
    def dispose(self):
        self.receipts_repository.dispose()
        self.files_repository.dispose()
        self.receipts_scans_repository.dispose()
        self.ocr_service.dispose()
        print("All resources disposed.")
        
        