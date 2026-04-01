import asyncio
import concurrent.futures
import multiprocessing
from concurrent.futures.process import BrokenProcessPool
from typing import Any


OcrLine = tuple[list[list[int]], str, float]

# Executor running a single spawned subprocess that owns the PaddleOCR instance.
# Using spawn (not fork) prevents SIGSEGV from Celery ForkPoolWorker corruption.
_executor: concurrent.futures.ProcessPoolExecutor | None = None


def _to_serializable(result: Any) -> list:
    """
    Convert PaddleOCR result to plain Python lists so it can be pickled
    when sent back from a ProcessPoolExecutor subprocess.

    Normalises both the new dict-like format (PaddleOCR 2.10+, which contains
    CopyableWeakMethod objects) and the legacy list-of-lists format into the
    legacy shape: [[polygon, [text, score]], ...] per page.
    """
    if result is None:
        return []
    pages = []
    for page in result:
        if not page:
            pages.append([])
            continue
        items: list = []
        try:
            if "rec_texts" in page:
                polys = page.get("rec_polys") or page.get("dt_polys") or []
                for polygon_raw, text, score in zip(polys, page["rec_texts"], page["rec_scores"]):
                    polygon = [[int(pt[0]), int(pt[1])] for pt in polygon_raw]
                    items.append([polygon, [str(text), float(score)]])
                pages.append(items)
                continue
        except (TypeError, KeyError):
            pass
        for item in page:
            if not item or len(item) < 2:
                continue
            polygon_raw = item[0]
            text_info = item[1]
            polygon = [[int(pt[0]), int(pt[1])] for pt in polygon_raw]
            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                text, score = str(text_info[0]), float(text_info[1])
            else:
                text, score = str(text_info), 1.0
            items.append([polygon, [text, score]])
        pages.append(items)
    return pages


def _ocr_worker(image_path: str):
    """Runs inside a spawned subprocess — PaddleOCR singleton lives here."""
    global _worker_ocr  # noqa: PLW0603
    try:
        ocr = _worker_ocr
    except NameError:
        from paddleocr import PaddleOCR
        _worker_ocr = PaddleOCR(use_angle_cls=True, lang="en")
        ocr = _worker_ocr
    return _to_serializable(ocr.ocr(image_path))


def _get_executor() -> concurrent.futures.ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
        )
    return _executor


def _reset_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
    _executor = None


class TextLocalizationService:
    """Wraps PaddleOCR to extract text lines and their polygon coordinates from an image."""

    def detect(self, image_path: str) -> list[OcrLine]:
        """
        Run OCR on the image and return a list of (polygon, text, score) tuples.
        polygon is a list of 4 [x, y] points (quadrilateral).
        PaddleOCR runs in a dedicated spawned subprocess to avoid SIGSEGV
        caused by Celery's fork-based worker pool.
        """
        for attempt in range(2):
            try:
                future = _get_executor().submit(_ocr_worker, image_path)
                result = future.result(timeout=120)
                return self._parse_result(result)
            except BrokenProcessPool:
                _reset_executor()
                if attempt == 1:
                    raise
        return []  # unreachable, but satisfies type checker

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
        pass  # executor lifetime managed at module level
