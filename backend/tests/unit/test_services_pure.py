import pytest
from decimal import Decimal

from PIL import Image

from src.services.bank_csv_parser import PekaoCsvParser
from src.services.markdown_table import MarkdownTableService
from src.services.text_matching import TextMatchingService


def _make_pekao_csv(rows: list[dict], encoding: str = "utf-8-sig") -> bytes:
    """Build a minimal Pekao SA CSV byte string."""
    headers = (
        "Data księgowania;Data waluty;Nadawca / Odbiorca;Adres nadawcy / odbiorcy;"
        "Rachunek źródłowy;Rachunek docelowy;Tytułem;Kwota operacji;Waluta;"
        "Numer referencyjny;Typ operacji"
    )
    lines = [headers]
    for row in rows:
        lines.append(
            f"{row.get('booking_date', '01.01.2024')};"
            f"{row.get('value_date', '01.01.2024')};"
            f"{row.get('counterparty', '')};"
            f"{row.get('address', '')};"
            f"{row.get('source_account', '')};"
            f"{row.get('target_account', '')};"
            f"{row.get('description', '')};"
            f"{row.get('amount', '10,00')};"
            f"{row.get('currency', 'PLN')};"
            f"{row.get('reference_number', 'REF001')};"
            f"{row.get('operation_type', '')}"
        )
    return "\n".join(lines).encode(encoding)


def _tiny_jpeg(tmp_path) -> str:
    """Create a small JPEG in tmp_path and return its absolute path."""
    img = Image.new("RGB", (4, 4), color=(255, 255, 255))
    path = str(tmp_path / "test.jpg")
    img.save(path, format="JPEG")
    return path


@pytest.mark.unit
class TestPekaoCsvParser:
    def test_parse_valid_utf8(self):
        # Arrange
        data = _make_pekao_csv([
            {"amount": "29,99", "reference_number": "REF001", "booking_date": "15.03.2024"},
        ])

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert len(result) == 1
        assert result[0].reference_number == "REF001"
        assert result[0].amount == Decimal("29.99")
        assert result[0].booking_date.day == 15
        assert result[0].booking_date.month == 3

    def test_polish_decimal_format(self):
        # Arrange — space thousands separator, comma decimal
        data = _make_pekao_csv([{"amount": "-1 014,31", "reference_number": "REF002"}])

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert result[0].amount == Decimal("-1014.31")

    def test_row_missing_reference_skipped(self):
        # Arrange
        data = _make_pekao_csv([{"amount": "10,00", "reference_number": ""}])

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert result == []

    def test_cp1250_encoding_fallback(self):
        # Arrange
        data = _make_pekao_csv([{"amount": "5,00", "reference_number": "REF003"}], encoding="cp1250")

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert len(result) == 1
        assert result[0].reference_number == "REF003"

    def test_apostrophe_stripped_from_reference(self):
        # Arrange — Pekao Excel-safe apostrophe prefix
        data = _make_pekao_csv([{"amount": "10,00", "reference_number": "'ABC123"}])

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert result[0].reference_number == "ABC123"

    def test_invalid_amount_skipped(self):
        # Arrange
        data = _make_pekao_csv([{"amount": "not_a_number", "reference_number": "REF004"}])

        # Act
        result = PekaoCsvParser().parse_bytes(data)

        # Assert
        assert result == []


@pytest.mark.unit
class TestMarkdownTableService:
    def test_basic_two_column_table(self):
        # Arrange
        col1 = ["Header1", "Row1A", "Row2A"]
        col2 = ["Header2", "Row1B", "Row2B"]
        svc = MarkdownTableService()

        # Act
        result = svc.table([col1, col2])

        # Assert
        assert "Header1" in result
        assert "Header2" in result
        assert "|" in result
        assert "---" in result

    def test_columns_of_different_lengths_padded(self):
        # Arrange — col2 is shorter; last cell should be empty (no IndexError)
        col1 = ["H1", "A", "B", "C"]
        col2 = ["H2", "X", "Y"]
        svc = MarkdownTableService()

        # Act — should not raise
        result = svc.table([col1, col2])

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    def test_single_column_table(self):
        # Arrange
        col = ["Header", "Value1"]
        svc = MarkdownTableService()

        # Act
        result = svc.table([col])

        # Assert
        assert "Header" in result


@pytest.mark.unit
class TestTextMatchingService:
    def test_products_matched_to_regions(self, tmp_path):
        # Arrange
        image_path = _tiny_jpeg(tmp_path)
        ocr_lines = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Mleko 2%", 0.99),
            ([[0, 30], [100, 30], [100, 50], [0, 50]], "Chleb pszenny", 0.95),
        ]
        products = [{"name": "Mleko"}, {"name": "Chleb"}]
        svc = TextMatchingService()

        # Act
        result = svc.match(ocr_lines, products, image_path)

        # Assert
        assert result.image_width == 4
        assert result.image_height == 4
        assert len(result.product_regions) == 2

    def test_empty_product_list(self, tmp_path):
        # Arrange
        image_path = _tiny_jpeg(tmp_path)
        ocr_lines = [([[0, 0], [100, 0], [100, 20], [0, 20]], "Mleko 2%", 0.99)]
        svc = TextMatchingService()

        # Act
        result = svc.match(ocr_lines, [], image_path)

        # Assert
        assert result.product_regions == {}
