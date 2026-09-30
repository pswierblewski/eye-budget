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
def test_auto_confirm_defaults_to_dry_run(client):
    # Arrange
    from src.data import AutoConfirmReasonItem, SingleAutoConfirmResult

    payload = SingleAutoConfirmResult(
        dry_run=True,
        ok=True,
        confirmed=False,
        reasons=[AutoConfirmReasonItem(code="ok", message="OK", blocking=False)],
        receipt=None,
    )
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.try_auto_confirm_receipt.return_value = payload
        instance.dispose = MagicMock()

        # Act
        response = client.post("/receipts/42/auto-confirm")

    # Assert
    assert response.status_code == 200
    instance.try_auto_confirm_receipt.assert_called_once_with(42, dry_run=True)
    assert response.json()["ok"] is True


@pytest.mark.integration
def test_auto_confirm_not_found(client):
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.try_auto_confirm_receipt.return_value = None
        instance.dispose = MagicMock()

        response = client.post("/receipts/99/auto-confirm")

    assert response.status_code == 404


@pytest.mark.integration
def test_list_receipts_rejects_unknown_confirmation_source(client):
    # Act
    response = client.get("/receipts?confirmation_source=robot")

    # Assert
    assert response.status_code == 422
