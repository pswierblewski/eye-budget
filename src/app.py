from abc import ABC
from repositories.receipts_repository import ReceiptsRepository
from repositories.files_repository import FilesRepository
from services.preprocessing import PreprocessingService

class App(ABC):
    def __init__(self):
        self.receipts_repository = ReceiptsRepository()
        self.files_repository = FilesRepository()
        self.preprocessing_service = PreprocessingService()
    
    def run(self):
        self.receipts_repository.download_receipts()
        files = self.files_repository.list_input_files()
        for file in files:
            processed_file = self.preprocessing_service.preprocess(file)
        
        
        