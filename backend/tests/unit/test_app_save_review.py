import pytest
from unittest.mock import MagicMock

from src.data import (
    ConfirmReceiptRequest,
    ProductItem,
    ReceiptScanDetail,
    SingleAutoConfirmResult,
    TransactionModel,
)
from tests.unit.conftest import make_app


def _pending_detail():
    return ReceiptScanDetail(
        id=1,
        filename="a.jpg",
        status="to_confirm",
        result=TransactionModel(
            vendor="Lidl",
            title="P",
            products=[ProductItem(name="A", quantity=1, price=1.0)],
            total=1.0,
            date="2026-09-30",
        ),
    )


@pytest.mark.unit
def test_save_review_persists_result_and_dry_runs_without_confirm():
    # Arrange
    app = make_app()
    detail = _pending_detail()
    app.receipts_scans_repository.get_by_id.return_value = detail
    app.get_receipt_by_id = MagicMock(return_value=detail)
    app._apply_review_overrides = MagicMock(return_value=detail.result)
    app._dry_run_gate = MagicMock(
        return_value=SingleAutoConfirmResult(
            dry_run=True, ok=True, confirmed=False, reasons=[], skipped=False
        )
    )
    request = ConfirmReceiptRequest(product_categories={"A": 1})

    # Act
    out = app.save_review(1, request)

    # Assert
    assert out is not None
    app.receipts_scans_repository.set_category_selections.assert_called_once_with(1, {"A": 1})
    app._dry_run_gate.assert_called_once()
    app._apply_review_overrides.assert_called_once()


@pytest.mark.unit
def test_add_auto_confirm_waiver_appends_and_dry_runs():
    # Arrange
    app = make_app()
    detail = _pending_detail()
    app.receipts_scans_repository.get_by_id.return_value = detail
    app.receipts_scans_repository.append_auto_confirm_waiver.return_value = True
    app.get_receipt_by_id = MagicMock(return_value=detail)
    app._dry_run_gate = MagicMock(
        return_value=SingleAutoConfirmResult(
            dry_run=True, ok=False, confirmed=False, reasons=[], skipped=False
        )
    )
    from src.data import AutoConfirmWaiverRequest

    # Act
    out = app.add_auto_confirm_waiver(1, AutoConfirmWaiverRequest(code="sum_mismatch"))

    # Assert
    assert out is not None
    app.receipts_scans_repository.append_auto_confirm_waiver.assert_called_once()
    app._dry_run_gate.assert_called_once()


@pytest.mark.unit
def test_reopen_clears_save_review_fields():
    # Arrange
    app = make_app()
    detail = ReceiptScanDetail(id=1, filename="a.jpg", status="done", confirmation_source="manual")
    app.receipts_scans_repository.get_by_id.return_value = detail
    app.get_receipt_by_id = MagicMock(return_value=detail)

    # Act
    app.reopen_receipt(1)

    # Assert
    app.receipts_scans_repository.clear_save_review_fields.assert_called_once_with(1)
