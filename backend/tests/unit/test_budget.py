import pytest
from unittest.mock import MagicMock
from src.data import CreateFinancialGoalRequest
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_get_monthly_breakdown_delegates_year_and_month():
    app = make_app()
    app.get_monthly_breakdown(2025, 3)
    app.budget_analysis_service.get_monthly_breakdown.assert_called_once_with(2025, 3)


@pytest.mark.unit
def test_check_affordability_fetches_focus_and_allocations():
    app = make_app()
    focus = MagicMock()
    focus.id = 1
    focus.label = "savings"
    app.budget_analysis_service.get_financial_focus.return_value = focus
    app.budget_goals_repository.get_active_goal_allocations_total.return_value = 500.0

    app.check_affordability(1000.0)

    app.budget_analysis_service.check_affordability.assert_called_once_with(
        amount_pln=1000.0,
        financial_focus_label="savings",
        goal_allocations_pln=500.0,
    )


@pytest.mark.unit
def test_check_affordability_uses_none_focus_when_no_focus_set():
    app = make_app()
    focus = MagicMock()
    focus.id = None
    app.budget_analysis_service.get_financial_focus.return_value = focus
    app.budget_goals_repository.get_active_goal_allocations_total.return_value = 0.0

    app.check_affordability(500.0)

    _, kwargs = app.budget_analysis_service.check_affordability.call_args
    assert kwargs["financial_focus_label"] is None


@pytest.mark.unit
def test_get_goals_delegates():
    app = make_app()
    expected = [MagicMock()]
    app.budget_goals_service.get_goals.return_value = expected

    result = app.get_goals()

    app.budget_goals_service.get_goals.assert_called_once()
    assert result is expected


@pytest.mark.unit
def test_create_goal_delegates_request():
    app = make_app()
    req = MagicMock(spec=CreateFinancialGoalRequest)

    app.create_goal(req)

    app.budget_goals_service.create_goal.assert_called_once_with(req)


@pytest.mark.unit
def test_delete_goal_delegates_goal_id():
    app = make_app()

    app.delete_goal(42)

    app.budget_goals_service.delete_goal.assert_called_once_with(42)


@pytest.mark.unit
def test_get_ai_recommendations_delegates():
    app = make_app()
    expected = MagicMock()
    app.budget_simulation_service.get_ai_recommendations_from_db.return_value = expected

    result = app.get_ai_recommendations()

    app.budget_simulation_service.get_ai_recommendations_from_db.assert_called_once()
    assert result is expected
