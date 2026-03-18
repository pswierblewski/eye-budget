"""
Targeted delegation tests to boost coverage of App methods.
Covers simple pass-through methods and basic branching paths.
"""
import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


# ---------------------------------------------------------------------------
# Vendor / product CRUD (lines 208-228)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_vendors_delegates():
    # Arrange
    app = make_app()

    # Act
    result = app.get_all_vendors()

    # Assert
    app.vendors_repository.get_all_vendors.assert_called_once()


@pytest.mark.unit
def test_create_vendor_returns_none_on_failure():
    # Arrange
    app = make_app()
    app.vendors_repository.insert_vendor.return_value = None

    # Act
    result = app.create_vendor("Test")

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_vendor_returns_item_on_success():
    # Arrange
    app = make_app()
    app.vendors_repository.insert_vendor.return_value = 5

    # Act
    result = app.create_vendor("Test")

    # Assert
    assert result is not None
    assert result.id == 5
    assert result.name == "Test"


@pytest.mark.unit
def test_get_all_products_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_all_products()

    # Assert
    app.products_repository.get_all_products.assert_called_once()


@pytest.mark.unit
def test_create_product_returns_none_on_failure():
    # Arrange
    app = make_app()
    app.products_repository.insert_product.return_value = None

    # Act
    result = app.create_product("Test")

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_product_returns_item_on_success():
    # Arrange
    app = make_app()
    app.products_repository.insert_product.return_value = 7

    # Act
    result = app.create_product("TestProd")

    # Assert
    assert result is not None
    assert result.id == 7


# ---------------------------------------------------------------------------
# run() method (lines 243-247)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_no_evaluate():
    # Arrange
    app = make_app()
    app.files_repository.list_input_files.return_value = []

    # Act
    result = app.run(evaluate=False)

    # Assert
    assert result is None


@pytest.mark.unit
def test_run_with_evaluate():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.evaluation_service.run_evaluation.return_value = expected

    # Act
    result = app.run(evaluate=True)

    # Assert
    app.evaluation_service.run_evaluation.assert_called_once()
    assert result is expected


# ---------------------------------------------------------------------------
# _run_localization (lines 256-259)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_localization_delegates():
    # Arrange
    app = make_app()

    # Act
    app._run_localization(scan_id=1, image_path="/tmp/img.jpg", products=[])

    # Assert
    app.text_localization_service.detect.assert_called_once_with("/tmp/img.jpg")
    app.text_matching_service.match.assert_called_once()
    app.receipts_scans_repository.set_text_regions.assert_called_once_with(1, app.text_matching_service.match.return_value)


# ---------------------------------------------------------------------------
# _run_production (lines 263-282)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_production_no_files():
    # Arrange
    app = make_app()
    app.files_repository.list_input_files.return_value = []

    # Act
    app._run_production()

    # Assert
    app.receipts_scans_repository.add_receipt.assert_not_called()


@pytest.mark.unit
def test_run_production_processes_new_files():
    # Arrange
    app = make_app()
    app.files_repository.list_input_files.return_value = ["file1.jpg"]
    app.receipts_scans_repository.add_receipt.return_value = True
    app.preprocessing_service.preprocess_image.side_effect = Exception("skip")

    # Act
    app._run_production()

    # Assert
    app.receipts_scans_repository.add_receipt.assert_called_once_with("file1.jpg")


# ---------------------------------------------------------------------------
# Ground truth delegation (lines 418-432)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_ground_truth_delegates():
    # Arrange
    app = make_app()

    # Act
    app.create_ground_truth("file.jpg", b"data")

    # Assert
    app.ground_truth_service.create.assert_called_once_with("file.jpg", b"data")


@pytest.mark.unit
def test_update_ground_truth_delegates():
    # Arrange
    app = make_app()
    tx_mock = MagicMock()

    # Act
    app.update_ground_truth(1, tx_mock)

    # Assert
    app.ground_truth_service.update.assert_called_once_with(1, tx_mock)


@pytest.mark.unit
def test_get_ground_truth_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_ground_truth(1)

    # Assert
    app.ground_truth_service.get.assert_called_once_with(1)


@pytest.mark.unit
def test_list_ground_truth_delegates():
    # Arrange
    app = make_app()

    # Act
    app.list_ground_truth()

    # Assert
    app.ground_truth_service.list.assert_called_once()


# ---------------------------------------------------------------------------
# Receipt listing (lines 455-471)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_receipts_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_all_receipts()

    # Assert
    app.receipts_scans_repository.get_all.assert_called_once()


@pytest.mark.unit
def test_get_receipt_status_counts_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_receipt_status_counts()

    # Assert
    app.receipts_scans_repository.get_status_counts.assert_called_once()


# ---------------------------------------------------------------------------
# get_receipt_by_id (lines 485-501)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_by_id_returns_none_when_missing():
    # Arrange
    app = make_app()
    app.receipts_scans_repository.get_by_id.return_value = None

    # Act
    result = app.get_receipt_by_id(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_receipt_by_id_with_transaction():
    # Arrange
    from src.data import ReceiptScanDetail, TransactionModel, ProductItem
    app = make_app()
    tx_model = TransactionModel(
        vendor="Shop", title="PARAGON", date="2024-01-01", total=10.0,
        products=[ProductItem(name="Item", quantity=1, price=10.0)]
    )
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", result=tx_model)
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.transactions_repository.get_by_scan_id.return_value = None

    # Act
    result = app.get_receipt_by_id(1)

    # Assert
    assert result is not None


# ---------------------------------------------------------------------------
# Image methods (lines 505-515)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_receipt_image_bytes_returns_none_when_no_key():
    # Arrange
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", minio_object_key=None)
    app.receipts_scans_repository.get_by_id.return_value = scan

    # Act
    result = app.get_receipt_image_bytes(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_receipt_image_bytes_downloads_when_key_exists():
    # Arrange
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", minio_object_key="receipts/1.jpg")
    app.receipts_scans_repository.get_by_id.return_value = scan
    app.minio_service.download_image.return_value = b"imgdata"

    # Act
    result = app.get_receipt_image_bytes(1)

    # Assert
    app.minio_service.download_image.assert_called_once_with("receipts/1.jpg")


@pytest.mark.unit
def test_get_receipt_image_url_returns_none_when_no_key():
    # Arrange
    from src.data import ReceiptScanDetail
    app = make_app()
    scan = ReceiptScanDetail(id=1, filename="f.jpg", status="done", minio_object_key=None)
    app.receipts_scans_repository.get_by_id.return_value = scan

    # Act
    result = app.get_receipt_image_url(1)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# update_transaction_item / delete_transaction_item (lines 784-791)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_delete_transaction_item_delegates():
    # Arrange
    app = make_app()

    # Act
    app.delete_transaction_item(42)

    # Assert
    app.transactions_repository.delete_transaction_item.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# Category / evaluation delegation (lines 918-980)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_expense_categories_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_all_expense_categories()

    # Assert
    app.categories_repository.get_all_expense_categories.assert_called_once()


@pytest.mark.unit
def test_get_all_bank_transactions_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_all_bank_transactions()

    # Assert
    app.bank_transactions_repository.get_list.assert_called_once()


# ---------------------------------------------------------------------------
# Bank transaction by ID (lines 993-999)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_bank_transaction_by_id_returns_none():
    # Arrange
    app = make_app()
    app.bank_transactions_repository.get_by_id.return_value = None

    # Act
    result = app.get_bank_transaction_by_id(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_bank_transaction_by_id_returns_detail():
    # Arrange
    from src.data import BankTransactionDetail
    app = make_app()
    detail = BankTransactionDetail(
        id=1, reference_number="REF001", booking_date="2024-01-01",
        amount=100.0, currency="PLN"
    )
    app.bank_transactions_repository.get_by_id.return_value = detail
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = None

    # Act
    result = app.get_bank_transaction_by_id(1)

    # Assert
    assert result is not None


# ---------------------------------------------------------------------------
# Bank candidates (lines 1018-1040)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_bank_tx_candidates_for_receipt_returns_empty_when_no_tx():
    # Arrange
    app = make_app()
    app.transactions_repository.get_by_scan_id.return_value = None

    # Act
    result = app.get_bank_tx_candidates_for_receipt(1)

    # Assert
    assert result == []


# ---------------------------------------------------------------------------
# unlink_bank_transaction (lines 1158-1159)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_unlink_bank_transaction_deletes_link():
    # Arrange
    app = make_app()
    app.bank_transactions_repository.get_by_id.return_value = None

    # Act
    app.unlink_bank_transaction(5)

    # Assert
    app.bank_receipt_links_repository.delete_link_by_bank_tx.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# Cash transactions (lines 1223-1315)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_all_cash_transactions_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_all_cash_transactions()

    # Assert
    app.cash_transactions_repository.get_list.assert_called_once()


@pytest.mark.unit
def test_get_cash_transaction_by_id_returns_none():
    # Arrange
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = None

    # Act
    result = app.get_cash_transaction_by_id(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_delete_cash_transaction_delegates():
    # Arrange
    app = make_app()

    # Act
    app.delete_cash_transaction(3)

    # Assert
    app.cash_transactions_repository.delete.assert_called_once_with(3)


@pytest.mark.unit
def test_delete_bank_transaction_delegates():
    # Arrange
    app = make_app()

    # Act
    app.delete_bank_transaction(3)

    # Assert
    app.bank_transactions_repository.delete.assert_called_once_with(3)


@pytest.mark.unit
def test_get_receipt_candidates_for_cash_tx_delegates():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.find_receipt_candidates.return_value = []

    # Act
    result = app.get_receipt_candidates_for_cash_tx(1)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_cash_tx_candidates_for_receipt_returns_empty_when_no_tx():
    # Arrange
    app = make_app()
    app.transactions_repository.get_by_scan_id.return_value = None

    # Act
    result = app.get_cash_tx_candidates_for_receipt(1)

    # Assert
    assert result == []


@pytest.mark.unit
def test_link_cash_to_receipt_returns_none_on_conflict():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.create_link.return_value = False
    from src.data import LinkCashReceiptRequest
    req = LinkCashReceiptRequest(receipt_transaction_id=10)

    # Act
    result = app.link_cash_to_receipt(1, req)

    # Assert
    assert result is None


@pytest.mark.unit
def test_unlink_cash_transaction_delegates():
    # Arrange
    app = make_app()
    app.cash_transactions_repository.get_by_id.return_value = None

    # Act
    app.unlink_cash_transaction(5)

    # Assert
    app.cash_receipt_links_repository.delete_link_by_cash_tx.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# Tag update propagation (lines 1319-1353)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_update_receipt_tags_no_linked_tx():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.get_bank_tx_id_for_scan.return_value = None
    app.cash_receipt_links_repository.get_cash_tx_id_for_scan.return_value = None

    # Act
    app.update_receipt_tags(1, ["a"])

    # Assert
    app.receipts_scans_repository.update_tags.assert_called_with(1, ["a"])


@pytest.mark.unit
def test_update_receipt_tags_merges_bank_tags():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.get_bank_tx_id_for_scan.return_value = 10
    app.bank_transactions_repository.get_tags_for_tx.return_value = ["b"]
    app.cash_receipt_links_repository.get_cash_tx_id_for_scan.return_value = None

    # Act
    app.update_receipt_tags(1, ["a"])

    # Assert
    app.bank_transactions_repository.update_tags.assert_called_with(10, ["a", "b"])


@pytest.mark.unit
def test_update_bank_transaction_tags_no_link():
    # Arrange
    app = make_app()
    app.bank_receipt_links_repository.get_receipt_link_info.return_value = None

    # Act
    app.update_bank_transaction_tags(5, ["x"])

    # Assert
    app.bank_transactions_repository.update_tags.assert_called_with(5, ["x"])


@pytest.mark.unit
def test_update_cash_transaction_tags_no_link():
    # Arrange
    app = make_app()
    app.cash_receipt_links_repository.get_receipt_link_info.return_value = None

    # Act
    app.update_cash_transaction_tags(5, ["x"])

    # Assert
    app.cash_transactions_repository.update_tags.assert_called_with(5, ["x"])


# ---------------------------------------------------------------------------
# Unified + analytics (lines 1376-1422)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_financial_focus_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_financial_focus()

    # Assert
    app.budget_analysis_service.get_financial_focus.assert_called_once()


@pytest.mark.unit
def test_get_recurring_expenses_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_recurring_expenses()

    # Assert
    app.budget_analysis_service.get_recurring_expenses.assert_called_once()


@pytest.mark.unit
def test_get_cyclical_alerts_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_cyclical_alerts()

    # Assert
    app.budget_analysis_service.get_cyclical_alerts.assert_called_once()


@pytest.mark.unit
def test_get_monthly_surplus_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_monthly_surplus()

    # Assert
    app.budget_goals_service.get_monthly_surplus.assert_called_once()


@pytest.mark.unit
def test_update_goal_delegates():
    # Arrange
    app = make_app()
    req = MagicMock()

    # Act
    app.update_goal(1, req)

    # Assert
    app.budget_goals_service.update_goal.assert_called_once_with(1, req)


@pytest.mark.unit
def test_delete_simulation_delegates():
    # Arrange
    app = make_app()

    # Act
    app.delete_simulation(3)

    # Assert
    app.budget_simulations_repository.delete_simulation.assert_called_once_with(3)
