import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, ReceiptScanDetail, TransactionModel
from src.repositories.receipts_scans import ProcessedScan
from src.services.receipt_auto_confirm import AutoConfirmSettings, ProductResolution
from src.services.receipt_categorization import CategorizationResult
from tests.unit.conftest import make_app


def _tx(total=3.99):
    return TransactionModel(
        vendor="LIDL SP. Z O.O.",
        title="P",
        products=[ProductItem(name="MLEKO", quantity=1, price=3.99)],
        total=total,
        date="2026-09-30",
    )


def _result():
    return CategorizationResult(
        candidates={"category_candidates": []},
        resolutions=[ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)],
        vendor_has_history=True,
    )


def _app(scans):
    app = make_app(auto_confirm_settings=AutoConfirmSettings(enabled=False))
    app.receipts_scans_repository.get_pending_for_rescore.return_value = scans
    app.receipts_scans_repository.set_category_candidates_if_pending.return_value = True
    app.receipts_scans_repository.get_by_id.return_value = ReceiptScanDetail(id=1, filename="a.jpg", status="to_confirm")
    app.vendors_repository.get_vendor_by_alternative_name.return_value = 3
    app.vendors_repository.get_normalized_name_by_alternative_name.return_value = "Lidl"
    app.receipt_categorization_service.categorize.return_value = _result()
    app._apply_auto_confirm = MagicMock(return_value=True)
    return app


@pytest.mark.unit
def test_dry_run_counts_eligible_without_confirming():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx()), ProcessedScan(2, "b.jpg", _tx(total=9.99))])

    # Act
    report = app.rescore_pending_receipts(dry_run=True)

    # Assert
    assert report.total == 2
    assert report.eligible == 1
    assert report.confirmed == 0
    app._apply_auto_confirm.assert_not_called()
    assert app.receipts_scans_repository.set_auto_confirm_reasons.call_count == 2
    assert report.top_reasons[0].code == "sum_mismatch"
    assert report.top_reasons[0].count == 1


@pytest.mark.unit
def test_uses_normalized_vendor_for_categorization():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])

    # Act
    app.rescore_pending_receipts(dry_run=True)

    # Assert
    tx_arg, vendor_id = app.receipt_categorization_service.categorize.call_args[0]
    assert tx_arg.vendor == "Lidl"
    assert vendor_id == 3


@pytest.mark.unit
def test_real_run_force_confirms_eligible():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.confirmed == 1
    assert app._apply_auto_confirm.call_args.kwargs["force"] is True


@pytest.mark.unit
def test_scan_confirmed_meanwhile_is_skipped():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipts_scans_repository.set_category_candidates_if_pending.return_value = False

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.skipped == 1
    app._apply_auto_confirm.assert_not_called()


@pytest.mark.unit
def test_status_change_before_confirm_is_skipped():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipts_scans_repository.get_by_id.return_value = ReceiptScanDetail(id=1, filename="a.jpg", status="done")

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.skipped == 1
    assert report.confirmed == 0


@pytest.mark.unit
def test_errors_are_counted_and_progress_reported():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipt_categorization_service.categorize.side_effect = Exception("llm")
    progress = MagicMock()

    # Act
    report = app.rescore_pending_receipts(dry_run=True, on_progress=progress)

    # Assert
    assert report.errors == 1
    progress.assert_called_once_with(index=1, total=1)
