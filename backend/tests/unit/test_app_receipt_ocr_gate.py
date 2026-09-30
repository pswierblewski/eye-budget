import pytest
from unittest.mock import MagicMock

from src.data import ReceiptsScanStatus
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_handle_ocr_dict_rejects_empty_date():
    app = make_app()
    ocr_dict = {
        "vendor": "Lidl",
        "title": "PARAGON",
        "date": "",
        "total": 10.0,
        "products": [{"name": "Chleb", "quantity": 1, "price": 10.0}],
    }

    ok, payload, err = app._handle_ocr_dict("scan.jpg", ocr_dict)

    assert ok is False
    assert payload is None
    assert err is not None
    app.receipts_scans_repository.set_ocr_failure.assert_called_once()
    app.receipts_scans_repository.set_result.assert_not_called()


@pytest.mark.unit
def test_handle_ocr_dict_accepts_valid_payload():
    app = make_app()
    ocr_dict = {
        "vendor": "Lidl",
        "title": "PARAGON",
        "date": "2026-09-12",
        "total": 10.0,
        "products": [{"name": "Chleb", "quantity": 1, "price": 10.0}],
    }

    ok, payload, err = app._handle_ocr_dict("scan.jpg", ocr_dict)

    assert ok is True
    assert payload is not None
    assert err is None
    app.receipts_scans_repository.set_result.assert_called_once()
    app.receipts_scans_repository.set_status.assert_called_with(
        "scan.jpg", ReceiptsScanStatus.PROCESSED
    )
