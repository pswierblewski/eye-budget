import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.version import VERSION


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_get_version_returns_200(client):
    # Arrange / Act
    response = client.get("/version")

    # Assert
    assert response.status_code == 200


@pytest.mark.integration
def test_get_version_returns_correct_version(client):
    # Arrange / Act
    response = client.get("/version")

    # Assert
    assert response.json()["version"] == VERSION


@pytest.mark.integration
def test_get_version_returns_backend_component(client):
    # Arrange / Act
    response = client.get("/version")

    # Assert
    assert response.json()["component"] == "backend"


@pytest.mark.integration
def test_get_version_requires_no_authentication(client):
    # Arrange — no auth headers provided
    # Act
    response = client.get("/version")

    # Assert — endpoint is public
    assert response.status_code != 401
    assert response.status_code != 403
