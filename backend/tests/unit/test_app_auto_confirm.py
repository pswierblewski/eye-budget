import pytest
from unittest.mock import MagicMock

from src.data import ConfirmReceiptRequest, ProductItem, ReceiptScanDetail, TransactionModel
from src.services.receipt_auto_confirm import (
    AutoConfirmDecision,
    AutoConfirmReason,
    AutoConfirmSettings,
    ProductResolution,
)
from tests.unit.conftest import make_app

ENABLED = AutoConfirmSettings(enabled=True)
DISABLED = AutoConfirmSettings(enabled=False)
RESOLUTIONS = [ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)]


def _scan(status="to_confirm", source=None):
    tx = TransactionModel(
        vendor="Lidl",
        title="P",
        products=[ProductItem(name="MLEKO", quantity=1, price=3.99)],
        total=3.99,
        date="2026-09-30",
    )
    return ReceiptScanDetail(id=1, filename="a.jpg", status=status, result=tx, confirmation_source=source)


def _app(settings=ENABLED):
    app = make_app(auto_confirm_settings=settings)
    app.receipts_scans_repository.get_by_id.return_value = _scan()
    app.transactions_repository.create_transaction.return_value = 42
    app.transactions_repository.get_by_scan_id.return_value = None
    return app


@pytest.mark.unit
def test_confirm_receipt_auto_skips_ground_truth_and_records_source():
    # Arrange
    app = _app()

    # Act
    app.confirm_receipt(1, ConfirmReceiptRequest(product_categories={"MLEKO": 1}), confirmation_source="auto")

    # Assert
    app.receipts_scans_repository.set_status_done.assert_called_once_with(1, "auto")
    app.ground_truth_service.create_from_confirmed_receipt.assert_not_called()


@pytest.mark.unit
def test_confirm_receipt_manual_keeps_ground_truth():
    # Arrange
    app = _app()

    # Act
    app.confirm_receipt(1, ConfirmReceiptRequest(product_categories={"MLEKO": 1}))

    # Assert
    app.receipts_scans_repository.set_status_done.assert_called_once_with(1, "manual")
    app.ground_truth_service.create_from_confirmed_receipt.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_manual_product_normalization_overwrites_mapping():
    # Arrange
    app = _app()
    app.products_repository.get_product_by_name.return_value = 9

    # Act
    app.confirm_receipt(
        1,
        ConfirmReceiptRequest(product_categories={"MLEKO": 1}, normalized_products={"MLEKO": "Mleko"}),
    )

    # Assert
    app.products_repository.upsert_alternative_name.assert_called_once_with("MLEKO", 9)


@pytest.mark.unit
def test_reopen_auto_confirmed_marks_reverted():
    # Arrange
    app = _app()
    app.receipts_scans_repository.get_by_id.return_value = _scan(status="done", source="auto")

    # Act
    app.reopen_receipt(1)

    # Assert
    app.prompt_analytics_repository.mark_auto_confirm_reverted.assert_called_once_with(1)


@pytest.mark.unit
def test_reopen_manual_does_not_mark_reverted():
    # Arrange
    app = _app()
    app.receipts_scans_repository.get_by_id.return_value = _scan(status="done", source="manual")

    # Act
    app.reopen_receipt(1)

    # Assert
    app.prompt_analytics_repository.mark_auto_confirm_reverted.assert_not_called()


@pytest.mark.unit
def test_apply_auto_confirm_confirms_when_enabled_and_ok():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock(return_value=_scan(status="done"))

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is True
    request = app.confirm_receipt.call_args[0][1]
    assert request.product_categories == {"MLEKO": 1}
    assert request.normalized_products == {"MLEKO": "Mleko"}
    assert app.confirm_receipt.call_args.kwargs["confirmation_source"] == "auto"
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once_with(1, [])


@pytest.mark.unit
def test_apply_auto_confirm_disabled_only_stores_reasons():
    # Arrange
    app = _app(DISABLED)
    app.confirm_receipt = MagicMock()

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.confirm_receipt.assert_not_called()
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once()


@pytest.mark.unit
def test_apply_auto_confirm_force_ignores_disabled_flag():
    # Arrange
    app = _app(DISABLED)
    app.confirm_receipt = MagicMock(return_value=_scan(status="done"))

    # Act / Assert
    assert app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS, force=True) is True


@pytest.mark.unit
def test_apply_auto_confirm_blocked_decision_does_not_confirm():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock()
    reason = AutoConfirmReason("sum_mismatch", "m", True)

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(False, [reason]), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.confirm_receipt.assert_not_called()
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once_with(1, [reason.to_dict()])


@pytest.mark.unit
def test_apply_auto_confirm_failure_cleans_up():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock(side_effect=Exception("db"))

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.transactions_repository.delete_by_scan_id.assert_called_once_with(1)
    app.receipts_scans_repository.set_status_to_confirm_by_id.assert_called_once_with(1)
    last_reasons = app.receipts_scans_repository.set_auto_confirm_reasons.call_args[0][1]
    assert last_reasons[-1]["code"] == "confirm_failed"


@pytest.mark.unit
def test_default_settings_are_disabled_in_unit_env(monkeypatch):
    # Arrange
    monkeypatch.delenv("RECEIPT_AUTO_CONFIRM_ENABLED", raising=False)

    # Act
    app = make_app()

    # Assert
    assert app.auto_confirm_settings.enabled is False
