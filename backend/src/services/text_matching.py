import re
from PIL import Image

from src.data import ProductTextRegion, TextRegionsResult
from src.services.text_localization import OcrLine


class TextMatchingService:
    """
    Matches LLM-extracted product names to PaddleOCR-detected text lines.

    Uses a greedy exclusive-match strategy with index-based keys ("0", "1", ...)
    so that duplicate names (e.g. multiple "Rabat" entries) each get their own slot.
    """

    # Minimum OCR line length to consider for matching (filters stray VAT codes, etc.)
    _MIN_LINE_LEN = 3

    # Regex that matches lines containing only price/quantity noise (not product names)
    _PRICE_ONLY_RE = re.compile(
        r"^[\d\s.,/*xXsztSZT=:()\-+%]+$"
    )

    def match(
        self,
        ocr_lines: list[OcrLine],
        products: list[dict],
        image_path: str,
    ) -> TextRegionsResult:
        """
        Build a TextRegionsResult mapping product indices to bounding polygons.

        Args:
            ocr_lines: Output of TextLocalizationService.detect().
            products: List of product dicts from the LLM result (each has a "name" key).
            image_path: Path to the preprocessed image (used to get dimensions).
        """
        with Image.open(image_path) as img:
            image_width, image_height = img.size

        consumed: set[int] = set()
        product_regions: dict[str, ProductTextRegion] = {}

        for idx, product in enumerate(products):
            name = product.get("name", "")
            polygon = self._find_polygon(name, ocr_lines, consumed)
            if polygon is not None:
                product_regions[str(idx)] = ProductTextRegion(polygon=polygon)

        return TextRegionsResult(
            image_width=image_width,
            image_height=image_height,
            product_regions=product_regions,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_polygon(
        self, name: str, ocr_lines: list[OcrLine], consumed: set[int]
    ) -> list[list[int]] | None:
        best_idx: int | None = None
        best_score: float = -1.0

        name_stripped = self._strip_barcode(name).lower()
        name_lower = name.lower()

        for i, (polygon, text, _score) in enumerate(ocr_lines):
            if i in consumed:
                continue
            if len(text) < self._MIN_LINE_LEN:
                continue
            text_lower = text.lower()
            text_stripped = self._strip_barcode(text).lower()

            score = self._overlap_score(name_lower, text_lower)
            score = max(score, self._overlap_score(name_stripped, text_lower))
            score = max(score, self._overlap_score(name_lower, text_stripped))
            score = max(score, self._overlap_score(name_stripped, text_stripped))

            # Bonus for exact substring containment
            if name_lower in text_lower or text_lower in name_lower:
                score = max(score, 0.8)
            if name_stripped in text_stripped or text_stripped in name_stripped:
                score = max(score, 0.8)

            if score > best_score and score > 0.3:
                best_score = score
                best_idx = i

        if best_idx is None:
            return None

        consumed.add(best_idx)
        best_polygon = list(ocr_lines[best_idx][0])

        # Merge consecutive price-only lines that follow the matched line
        j = best_idx + 1
        while j < len(ocr_lines) and j not in consumed:
            next_text = ocr_lines[j][1]
            if self._is_price_only_line(next_text):
                consumed.add(j)
                best_polygon = self._merge_polygons(best_polygon, list(ocr_lines[j][0]))
                j += 1
            else:
                break

        return best_polygon

    @staticmethod
    def _strip_barcode(text: str) -> str:
        """Remove a leading numeric barcode/SKU (e.g. '8085759 FIGI 5-PACK' → 'FIGI 5-PACK')."""
        return re.sub(r"^\d{6,}\s*", "", text).strip()

    def _is_price_only_line(self, text: str) -> bool:
        return len(text) <= 40 and bool(self._PRICE_ONLY_RE.match(text.strip()))

    @staticmethod
    def _overlap_score(a: str, b: str) -> float:
        """Token-overlap Jaccard similarity between two strings."""
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    @staticmethod
    def _merge_polygons(
        poly_a: list[list[int]], poly_b: list[list[int]]
    ) -> list[list[int]]:
        """Return the axis-aligned bounding box that covers both polygons."""
        all_pts = poly_a + poly_b
        xs = [pt[0] for pt in all_pts]
        ys = [pt[1] for pt in all_pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
