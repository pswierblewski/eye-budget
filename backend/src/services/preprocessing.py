from abc import ABC
import os

import fitz
from PIL import Image

# Quality setting for JPEG output – high enough for accurate OCR (text legible),
# low enough that file sizes are 60-80 % smaller than lossless PNG.
_JPEG_QUALITY = int(os.getenv("PREPROCESSED_JPEG_QUALITY", "90"))


def _is_pdf_filename(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == ".pdf"


def _page_to_rgb_image(page: fitz.Page, matrix: fitz.Matrix) -> Image.Image:
    pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _stack_pages_vertically(page_images: list[Image.Image]) -> Image.Image:
    if not page_images:
        raise ValueError("PDF has no pages to render")
    max_w = max(im.width for im in page_images)
    strips: list[Image.Image] = []
    for im in page_images:
        if im.width == max_w:
            strips.append(im if im.mode == "RGB" else im.convert("RGB"))
            continue
        if im.mode != "RGB":
            im = im.convert("RGB")
        canvas = Image.new("RGB", (max_w, im.height), (255, 255, 255))
        x_off = (max_w - im.width) // 2
        canvas.paste(im, (x_off, 0))
        strips.append(canvas)
    total_h = sum(s.height for s in strips)
    out = Image.new("RGB", (max_w, total_h), (255, 255, 255))
    y = 0
    for s in strips:
        out.paste(s, (0, y))
        y += s.height
    return out


def _load_stacked_pil_from_pdf(pdf_path: str) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise ValueError("PDF is password-protected or encrypted")
        if doc.page_count < 1:
            raise ValueError("PDF has no pages")
        matrix = fitz.Matrix(2, 2)
        page_images: list[Image.Image] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            page_images.append(_page_to_rgb_image(page, matrix))
    finally:
        doc.close()
    return _stack_pages_vertically(page_images)


class PreprocessingService(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")

    def _write_preprocessed_jpeg(self, image: Image.Image, output_path: str) -> str:
        """Apply half-size resize, mode normalization, and JPEG write. Does not close `image`."""
        new_size = (image.width // 2, image.height // 2)
        resized_img = image.resize(new_size, Image.Resampling.LANCZOS)
        if resized_img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", resized_img.size, (255, 255, 255))
            background.paste(
                resized_img,
                mask=resized_img.split()[-1] if resized_img.mode in ("RGBA", "LA") else None,
            )
            resized_img = background
        elif resized_img.mode != "RGB":
            resized_img = resized_img.convert("RGB")
        os.makedirs(self.output_dir, exist_ok=True)
        resized_img.save(
            output_path,
            format="JPEG",
            quality=_JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
        return output_path

    def preprocess_image(self, image_path: str) -> str:
        input_image_path = os.path.join(self.input_dir, image_path)
        stem = os.path.splitext(os.path.basename(image_path))[0]
        # Always store as JPEG regardless of the source format.
        output_filename = f"{stem}.jpg"
        output_path = os.path.join(self.output_dir, output_filename)
        if _is_pdf_filename(image_path):
            stacked = _load_stacked_pil_from_pdf(input_image_path)
            try:
                return self._write_preprocessed_jpeg(stacked, output_path)
            finally:
                stacked.close()
        with Image.open(input_image_path) as img:
            return self._write_preprocessed_jpeg(img, output_path)
