import pytest

from src.services.receipt_ocr_validation import validate_ocr_payload


def _valid() -> dict:
    return {
        "vendor": "Lidl",
        "title": "PARAGON FISKALNY",
        "date": "2026-09-12",
        "total": 42.50,
        "products": [{"name": "Chleb", "quantity": 1, "price": 4.5, "unit_price": 4.5}],
    }


@pytest.mark.unit
def test_validate_happy_path():
    result = validate_ocr_payload(_valid())
    assert result.ok is True
    assert result.errors == []
    assert result.normalized is not None
    assert result.normalized["vendor"] == "Lidl"
    assert result.normalized["date"] == "2026-09-12"


@pytest.mark.unit
def test_validate_empty_date():
    data = _valid()
    data["date"] = ""
    result = validate_ocr_payload(data)
    assert result.ok is False
    assert any("dat" in e.lower() for e in result.errors)


@pytest.mark.unit
def test_validate_zero_total():
    data = _valid()
    data["total"] = 0
    result = validate_ocr_payload(data)
    assert result.ok is False


@pytest.mark.unit
def test_validate_no_products():
    data = _valid()
    data["products"] = []
    result = validate_ocr_payload(data)
    assert result.ok is False
