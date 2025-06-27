from abc import ABC
from repositories.receipts_repository import ReceiptsRepository
from repositories.files_repository import FilesRepository
from services.preprocessing import PreprocessingService
from services.ocr import OCRService

class App(ABC):
    def __init__(self):
        self.receipts_repository = ReceiptsRepository()
        self.files_repository = FilesRepository()
        self.preprocessing_service = PreprocessingService()
        self.ocr_service = OCRService()
    
    def run(self):
        #self.receipts_repository.download_receipts()
        #files = self.files_repository.list_input_files()
        file = '20250623_081058 (Custom).jpg'
        self.ocr_service.process_image(file)
        
        
        