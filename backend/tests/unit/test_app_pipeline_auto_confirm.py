import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, TransactionModel
from src.services.receipt_auto_confirm import AutoConfirmSettings, ProductResolution
from src.services.receipt_categorization import CategorizationResult
from tests.unit.conftest import make_app

TX = TransactionModel(
    vendor="Lidl",
    title="P",
    products=[ProductItem(name="MLEKO", quantity=1, price=3.99)],
    total=3.99,
    date="2026-09-30",
)
RESULT = CategorizationResult(
    candidates={"category_candidates": []},
    resolutions=[ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)],
    vendor_has_history=True,
)


@pytest.mark.unit
def test_categorize_receipt_stores_candidates():
    # Arrange
    app = make_app()
    app.receipt_categorization_service.categorize.return_value = RESULT

    # Act
    result = app._categorize_receipt(1, "a.jpg", TX, vendor_id=3)

    # Assert
    assert result is RESULT
    app.receipt_categorization_service.categorize.assert_called_once_with(TX, 3)
    app.receipts_scans_repository.set_category_candidates.assert_called_once_with("a.jpg", RESULT.candidates)


@pytest.mark.unit
def test_categorize_receipt_falls_back_to_plain_llm_on_error():
    # Arrange
    app = make_app()
    app.receipt_categorization_service.categorize.side_effect = Exception("boom")
    app.categories_service.assign_category_candidates.return_value = {"category_candidates": []}

    # Act
    result = app._categorize_receipt(1, "a.jpg", TX, vendor_id=None)

    # Assert
    assert result is None
    app.categories_service.assign_category_candidates.assert_called_once_with(TX)
    app.receipts_scans_repository.set_category_candidates.assert_called_once_with("a.jpg", {"category_candidates": []})
    reasons = app.receipts_scans_repository.set_auto_confirm_reasons.call_args[0][1]
    assert reasons[0]["code"] == "evaluation_error"


@pytest.mark.unit
def test_evaluate_and_auto_confirm_uses_gate():
    # Arrange
    app = make_app(auto_confirm_settings=AutoConfirmSettings(enabled=True))
    app._apply_auto_confirm = MagicMock(return_value=True)

    # Act
    confirmed = app._evaluate_and_auto_confirm(1, TX, RESULT)

    # Assert
    assert confirmed is True
    decision = app._apply_auto_confirm.call_args[0][1]
    assert decision.ok is True


@pytest.mark.unit
def test_evaluate_and_auto_confirm_none_categorization_returns_false():
    # Arrange
    app = make_app()
    app._apply_auto_confirm = MagicMock()

    # Act / Assert
    assert app._evaluate_and_auto_confirm(1, TX, None) is False
    app._apply_auto_confirm.assert_not_called()


@pytest.mark.unit
def test_process_single_file_runs_history_pipeline(tmp_path):
    # Arrange
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    app = make_app()
    app.preprocessing_service.preprocess_image.return_value = str(img)
    app.receipts_scans_repository.get_scan_id_by_filename.return_value = 1
    app.ocr_service.process_image.return_value = TX.model_dump()
    app.vendors_service.process_vendor.return_value = MagicMock(vendor_name="Lidl")
    app.vendors_repository.process_vendor_mapping.return_value = 3
    app._categorize_receipt = MagicMock(return_value=RESULT)
    app._evaluate_and_auto_confirm = MagicMock(return_value=False)

    # Act
    ok = app._process_single_file("a.jpg")

    # Assert
    assert ok is True
    assert app._categorize_receipt.call_args[0][3] == 3
    app._evaluate_and_auto_confirm.assert_called_once()
    app.products_service.process_products.assert_not_called()
