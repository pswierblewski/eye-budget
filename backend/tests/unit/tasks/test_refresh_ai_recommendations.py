import pytest
from unittest.mock import MagicMock, patch

from src.data import AIInsightItem, AIRecommendationsResponse
from src.tasks.refresh_ai_recommendations import refresh_ai_recommendations_task
from tests.unit.tasks.conftest import assert_app_disposed, make_app, triggers_with_event


@pytest.mark.unit
class TestRefreshAiRecommendationsTask:
    def test_happy_path_triggers_done_and_returns_payload(self):
        # Arrange
        app = make_app()
        app.budget_simulation_service.generate_ai_recommendations.return_value = AIRecommendationsResponse(
            insights=[AIInsightItem(title="t", body="b", amount_pln=None, insight_type="info")],
            generated_at="2024-01-01T00:00:00",
            data_through_date=None,
            months_of_data=3,
            has_sufficient_data=True,
        )
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.refresh_ai_recommendations.App", return_value=app),
            patch("src.tasks.refresh_ai_recommendations.PusherService", return_value=mock_pusher),
        ):
            # Act
            result = refresh_ai_recommendations_task.apply(args=[], kwargs={}, throw=True).result

        # Assert
        assert result == {"has_sufficient_data": True}
        done = triggers_with_event(mock_pusher, "budget-channel", "budget.recommendations.done")
        assert len(done) == 1
        payload = done[0][0][2]
        assert "generated_at" in payload
        assert_app_disposed(app)

    def test_service_error_propagates_and_disposes(self):
        # Arrange
        app = make_app()
        app.budget_simulation_service.generate_ai_recommendations.side_effect = RuntimeError("openai down")
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.refresh_ai_recommendations.App", return_value=app),
            patch("src.tasks.refresh_ai_recommendations.PusherService", return_value=mock_pusher),
        ):
            # Act / Assert
            with pytest.raises(RuntimeError, match="openai down"):
                refresh_ai_recommendations_task.apply(args=[], kwargs={}, throw=True)

        mock_pusher.trigger.assert_not_called()
        assert_app_disposed(app)
