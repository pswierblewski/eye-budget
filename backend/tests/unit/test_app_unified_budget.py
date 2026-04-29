"""Unit tests for App unified transactions, tags, budget analysis, and simulations."""
import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_get_transactions_analytics_returns_repository_value():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.unified_transactions_repository.get_analytics.return_value = expected

    # Act
    result = app.get_transactions_analytics(date_from="2024-01-01", date_to="2024-01-31")

    # Assert
    assert result is expected
    app.unified_transactions_repository.get_analytics.assert_called_once_with(
        date_from="2024-01-01",
        date_to="2024-01-31",
    )


@pytest.mark.unit
def test_get_all_tags_returns_empty_when_no_conn():
    # Arrange
    app = make_app()
    app.receipts_scans_repository.conn = None

    # Act
    result = app.get_all_tags()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_tags_returns_tags():
    # Arrange
    app = make_app()
    cursor_mock = MagicMock()
    cursor_mock.__enter__ = MagicMock(return_value=cursor_mock)
    cursor_mock.__exit__ = MagicMock(return_value=False)
    cursor_mock.fetchall.return_value = [("food",), ("transport",)]
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    app.receipts_scans_repository.conn = conn_mock

    # Act
    result = app.get_all_tags()

    # Assert
    assert result == ["food", "transport"]


@pytest.mark.unit
def test_get_all_tags_returns_empty_on_exception():
    # Arrange
    app = make_app()
    conn_mock = MagicMock()
    conn_mock.cursor.side_effect = Exception("db error")
    app.receipts_scans_repository.conn = conn_mock

    # Act
    result = app.get_all_tags()

    # Assert
    assert result == []


@pytest.mark.unit
def test_seed_and_get_classifications_returns_service_value():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.budget_analysis_service.seed_and_get_classifications.return_value = expected

    # Act
    result = app.seed_and_get_classifications()

    # Assert
    assert result is expected
    app.budget_analysis_service.seed_and_get_classifications.assert_called_once()


@pytest.mark.unit
def test_update_category_classification_returns_service_value():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.budget_analysis_service.update_category_classification.return_value = expected

    # Act
    result = app.update_category_classification(3, "essential")

    # Assert
    assert result is expected
    app.budget_analysis_service.update_category_classification.assert_called_once_with(3, "essential")


@pytest.mark.unit
def test_set_financial_focus_returns_service_response():
    # Arrange
    from src.data import SetFinancialFocusRequest
    app = make_app()
    req = SetFinancialFocusRequest(label="savings", description="Save more")
    expected = MagicMock()
    app.budget_analysis_service.set_financial_focus.return_value = expected

    # Act
    result = app.set_financial_focus(req)

    # Assert
    assert result is expected
    app.budget_analysis_service.set_financial_focus.assert_called_once_with("savings", "Save more")


@pytest.mark.unit
def test_get_emergency_advice_passes_empty_goals_list():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.budget_analysis_service.get_emergency_advice.return_value = expected

    # Act
    result = app.get_emergency_advice(500.0)

    # Assert
    assert result is expected
    app.budget_analysis_service.get_emergency_advice.assert_called_once_with(500.0, [])


@pytest.mark.unit
def test_create_simulation_maps_request_to_repository_and_returns_dict():
    # Arrange
    from src.data import CreateBudgetSimulationRequest
    app = make_app()
    req = CreateBudgetSimulationRequest(
        name="Test Sim",
        expense_name="New Car",
        expense_amount_pln=1000.0,
        expense_type="one_time",
        expense_start_date="2024-06-01",
    )
    expected_row = {"id": 1, "name": "Test Sim"}
    app.budget_simulations_repository.create_simulation.return_value = expected_row

    # Act
    result = app.create_simulation(req)

    # Assert
    assert result == expected_row
    app.budget_simulations_repository.create_simulation.assert_called_once_with(
        name="Test Sim",
        expense_name="New Car",
        amount=1000.0,
        expense_type="one_time",
        start_date="2024-06-01",
    )


@pytest.mark.unit
def test_get_simulation_returns_none_when_missing():
    # Arrange
    app = make_app()
    app.budget_simulations_repository.get_simulation.return_value = None

    # Act
    result = app.get_simulation(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_simulation_returns_detail():
    # Arrange
    app = make_app()
    row = {
        "id": 1, "name": "S", "expense_name": "E",
        "expense_amount": 100.0, "expense_type": "one_time",
        "expense_start_date": "2024-01-01", "status": "done",
        "result_json": None, "error_message": None,
        "created_at": "2024-01-01T00:00:00",
    }
    app.budget_simulations_repository.get_simulation.return_value = row

    # Act
    result = app.get_simulation(1)

    # Assert
    assert result is not None
    assert result.name == "S"


@pytest.mark.unit
def test_get_all_simulations_returns_list():
    # Arrange
    app = make_app()
    app.budget_simulations_repository.get_all_simulations.return_value = [
        {
            "id": 1, "name": "S1", "expense_name": "E1",
            "expense_amount": 50.0, "expense_type": "recurring",
            "expense_start_date": "2024-01-01", "status": "pending",
            "created_at": "2024-01-01T00:00:00",
        }
    ]

    # Act
    result = app.get_all_simulations()

    # Assert
    assert len(result) == 1
    assert result[0].name == "S1"


@pytest.mark.unit
def test_create_category_returns_repository_value():
    # Arrange
    from src.data import CategoryItem
    app = make_app()
    expected = CategoryItem(id=9, name="Groceries", parent_name=None)
    app.categories_repository.create_category.return_value = expected

    # Act
    result = app.create_category("Groceries", None)

    # Assert
    assert result is expected
    app.categories_repository.create_category.assert_called_once_with("Groceries", None)


@pytest.mark.unit
def test_get_all_evaluation_runs_returns_repository_tuple():
    # Arrange
    app = make_app()
    expected = ([], 0)
    app.evaluations_repository.get_all_runs.return_value = expected

    # Act
    result = app.get_all_evaluation_runs()

    # Assert
    assert result == expected
    app.evaluations_repository.get_all_runs.assert_called_once_with(
        limit=50, offset=0, sort_by="id", sort_dir="desc",
    )


@pytest.mark.unit
def test_get_evaluation_run_returns_repository_value():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.evaluations_repository.get_run_with_results.return_value = expected

    # Act
    result = app.get_evaluation_run(5)

    # Assert
    assert result is expected
    app.evaluations_repository.get_run_with_results.assert_called_once_with(5)


@pytest.mark.unit
def test_get_bank_tx_ids_for_recategorization_returns_repository_list():
    # Arrange
    app = make_app()
    app.bank_transactions_repository.get_ids_for_recategorization.return_value = [3, 4]

    # Act
    result = app.get_bank_tx_ids_for_recategorization()

    # Assert
    assert result == [3, 4]
    app.bank_transactions_repository.get_ids_for_recategorization.assert_called_once()
