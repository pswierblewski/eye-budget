from abc import ABC
import os
import time
from PIL import Image

class PreprocessingService(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")

    def preprocess_image(self, image_path: str) -> str:
        input_image_path = os.path.join(self.input_dir, image_path)
        timestr = time.strftime("%Y%m%d-%H%M%S")
        output_filename = f'{timestr}.{os.getenv("PREPROCESSED_IMAGE_EXTENSION")}'
        output_path = os.path.join(self.output_dir, output_filename)
        with Image.open(input_image_path) as img:
            new_size = (img.width // 2, img.height // 2)
            resized_img = img.resize(new_size)
            resized_img.save(output_path)
        return output_path