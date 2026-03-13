import asyncio
from typing import Any


OcrLine = tuple[list[list[int]], str, float]

_ocr_singleton = None


def _get_ocr():
    global _ocr_singleton
    if _ocr_singleton is None:
        from paddleocr import PaddleOCR
        _ocr_singleton = PaddleOCR(use_angle_cls=True, lang="en")
    return _ocr_singleton


class TextLocalizationService:
    """Wraps PaddleOCR to extract text lines and their polygon coordinates from an image."""

    def detect(self, image_path: str) -> list[OcrLine]:
        """
        Run OCR on the image and return a list of (polygon, text, score) tuples.
        polygon is a list of 4 [x, y] points (quadrilateral).
        """
        result = _get_ocr().ocr(image_path)
        return self._parse_result(result)

    async def detect_async(self, image_path: str) -> list[OcrLine]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detect, image_path)

    def _parse_result(self, result: Any) -> list[OcrLine]:
        lines: list[OcrLine] = []
        if not result:
            return lines
        for page in result:
            if not page:
                continue
            try:
                # PaddleOCR 2.10+ returns dict-like result objects with
                # dt_polys / rec_texts / rec_scores arrays.
                if "rec_texts" in page:
                    polys = page.get("rec_polys") or page.get("dt_polys") or []
                    for polygon_raw, text, score in zip(
                        polys, page["rec_texts"], page["rec_scores"]
                    ):
                        try:
                            polygon = [[int(pt[0]), int(pt[1])] for pt in polygon_raw]
                            lines.append((polygon, str(text), float(score)))
                        except Exception as line_err:
                            print(f"OCR line parse error (skipped): {line_err}")
                    continue
            except (TypeError, KeyError):
                pass

            # Legacy format: page is a list of [polygon, [text, score]] items
            for item in page:
                if not item or len(item) < 2:
                    continue
                try:
                    polygon_raw = item[0]
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text, score = text_info[0], text_info[1]
                    else:
                        text, score = str(text_info), 1.0
                    polygon = [[int(pt[0]), int(pt[1])] for pt in polygon_raw]
                    lines.append((polygon, str(text), float(score)))
                except Exception as parse_err:
                    print(f"OCR item parse error (skipped): {parse_err} — item={item}")
        return lines

    def dispose(self) -> None:
        pass  # singleton lives for the process lifetime; do not destroy it
