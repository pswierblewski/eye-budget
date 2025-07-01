from abc import ABC
import os


class FilesRepository(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")
        
    def dispose(self):
        """
        Dispose of the repository resources.
        This method is a placeholder for any cleanup operations needed.
        """
        print("FilesRepository disposed.")
        
    def list_input_files(self):
        return [f for f in os.listdir(self.input_dir) if os.path.isfile(os.path.join(self.input_dir, f))]