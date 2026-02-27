from abc import ABC
import os
import shutil


class FilesRepository(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")
        self.attachment_dir = os.getenv("MY_MONEY_ATTACHMENTS_DIR", "attachment/")
        
    def dispose(self):
        """
        Dispose of the repository resources.
        This method is a placeholder for any cleanup operations needed.
        """
        print("FilesRepository disposed.")
        
    def list_input_files(self):
        return [f for f in os.listdir(self.input_dir) if os.path.isfile(os.path.join(self.input_dir, f))]

    def move_to_attachment_dir(self, source_file_path: str, target_file: str):
        os.makedirs(self.attachment_dir, exist_ok=True)
        shutil.move(source_file_path, os.path.join(self.attachment_dir, target_file))