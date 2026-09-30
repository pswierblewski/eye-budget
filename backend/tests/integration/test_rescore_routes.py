import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_rescore_defaults_to_dry_run(client):
    # Arrange
    task = MagicMock(id="t-1")
    with patch("src.main.rescore_pending_receipts_task") as mock_task:
        mock_task.delay.return_value = task

        # Act
        response = client.post("/receipts/rescore")

    # Assert
    assert response.status_code == 202
    assert response.json() == {"task_id": "t-1"}
    mock_task.delay.assert_called_once_with(dry_run=True)


@pytest.mark.integration
def test_rescore_real_run(client):
    # Arrange
    with patch("src.main.rescore_pending_receipts_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t-2")

        # Act
        client.post("/receipts/rescore?dry_run=false")

    # Assert
    mock_task.delay.assert_called_once_with(dry_run=False)


@pytest.mark.integration
def test_list_receipts_rejects_unknown_confirmation_source(client):
    # Act
    response = client.get("/receipts?confirmation_source=robot")

    # Assert
    assert response.status_code == 422
