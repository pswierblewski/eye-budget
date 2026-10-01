import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.data import AutoConfirmReasonItem, ReceiptScanDetail, SaveReviewResponse, SingleAutoConfirmResult
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_save_review_returns_receipt_and_auto_confirm(client):
    # Arrange
    receipt = ReceiptScanDetail(id=42, filename="a.jpg", status="to_confirm")
    payload = SaveReviewResponse(
        receipt=receipt,
        auto_confirm=SingleAutoConfirmResult(
            dry_run=True,
            ok=True,
            confirmed=False,
            reasons=[AutoConfirmReasonItem(code="ok", message="OK", blocking=False)],
        ),
    )
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.save_review.return_value = payload
        instance.dispose = MagicMock()

        # Act
        response = client.post(
            "/receipts/42/save-review",
            json={"product_categories": {"MLEKO": 1}},
        )

    # Assert
    assert response.status_code == 200
    instance.save_review.assert_called_once()
    body = response.json()
    assert body["receipt"]["id"] == 42
    assert body["auto_confirm"]["ok"] is True


@pytest.mark.integration
def test_save_review_not_found_when_not_pending(client):
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.save_review.return_value = None
        instance.dispose = MagicMock()

        response = client.post(
            "/receipts/99/save-review",
            json={"product_categories": {}},
        )

    assert response.status_code == 404


@pytest.mark.integration
def test_waiver_route_returns_save_review_response(client):
    receipt = ReceiptScanDetail(id=5, filename="b.jpg", status="to_confirm")
    payload = SaveReviewResponse(
        receipt=receipt,
        auto_confirm=SingleAutoConfirmResult(
            dry_run=True,
            ok=False,
            confirmed=False,
            reasons=[],
        ),
    )
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.add_auto_confirm_waiver.return_value = payload
        instance.dispose = MagicMock()

        response = client.post(
            "/receipts/5/auto-confirm-waiver",
            json={"code": "sum_mismatch"},
        )

    assert response.status_code == 200
    instance.add_auto_confirm_waiver.assert_called_once()


@pytest.mark.integration
def test_waiver_not_found_when_not_pending(client):
    with patch("src.main.App") as mock_app_cls:
        instance = mock_app_cls.return_value
        instance.add_auto_confirm_waiver.return_value = None
        instance.dispose = MagicMock()

        response = client.post(
            "/receipts/99/auto-confirm-waiver",
            json={"code": "sum_mismatch"},
        )

    assert response.status_code == 404
