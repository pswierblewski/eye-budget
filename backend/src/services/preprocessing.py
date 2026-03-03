from abc import ABC
import os
from PIL import Image

# Quality setting for JPEG output – high enough for accurate OCR (text legible),
# low enough that file sizes are 60-80 % smaller than lossless PNG.
_JPEG_QUALITY = int(os.getenv("PREPROCESSED_JPEG_QUALITY", "90"))

class PreprocessingService(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")

    def preprocess_image(self, image_path: str) -> str:
        input_image_path = os.path.join(self.input_dir, image_path)
        stem = os.path.splitext(os.path.basename(image_path))[0]
        # Always store as JPEG regardless of the source format.
        output_filename = f"{stem}.jpg"
        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        with Image.open(input_image_path) as img:
            new_size = (img.width // 2, img.height // 2)
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
            # JPEG does not support alpha channel – flatten to white background.
            if resized_img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", resized_img.size, (255, 255, 255))
                background.paste(
                    resized_img,
                    mask=resized_img.split()[-1] if resized_img.mode in ("RGBA", "LA") else None,
                )
                resized_img = background
            elif resized_img.mode != "RGB":
                resized_img = resized_img.convert("RGB")
            resized_img.save(
                output_path,
                format="JPEG",
                quality=_JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
        return output_path