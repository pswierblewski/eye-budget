import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_get_monthly_breakdown_delegates_year_and_month():
    # Arrange
    app = make_app()

    # Act
    app.get_monthly_breakdown(2025, 3)

    # Assert
    app.budget_analysis_service.get_monthly_breakdown.assert_called_once_with(2025, 3)


@pytest.mark.unit
def test_check_affordability_passes_zero_goal_allocations():
    # Arrange
    app = make_app()
    focus = MagicMock()
    focus.id = 1
    focus.label = "savings"
    app.budget_analysis_service.get_financial_focus.return_value = focus

    # Act
    app.check_affordability(1000.0)

    # Assert
    app.budget_analysis_service.check_affordability.assert_called_once_with(
        amount_pln=1000.0,
        financial_focus_label="savings",
        goal_allocations_pln=0.0,
    )


@pytest.mark.unit
def test_check_affordability_uses_none_focus_when_no_focus_set():
    # Arrange
    app = make_app()
    focus = MagicMock()
    focus.id = None
    app.budget_analysis_service.get_financial_focus.return_value = focus
    # Act
    app.check_affordability(500.0)

    # Assert
    _, kwargs = app.budget_analysis_service.check_affordability.call_args
    assert kwargs["financial_focus_label"] is None


@pytest.mark.unit
def test_get_ai_recommendations_delegates():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.budget_simulation_service.get_ai_recommendations_from_db.return_value = expected

    # Act
    result = app.get_ai_recommendations()

    # Assert
    app.budget_simulation_service.get_ai_recommendations_from_db.assert_called_once()
    assert result is expected
