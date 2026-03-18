import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_make_app_does_not_connect_to_db():
    # Act
    app = make_app()
    # Assert
    app.eye_budget_db_context.connect_db.assert_not_called()


@pytest.mark.unit
def test_make_app_uses_injected_repos():
    # Arrange
    mock = MagicMock()
    # Act
    app = make_app(receipts_scans_repository=mock)
    # Assert
    assert app.receipts_scans_repository is mock


@pytest.mark.unit
def test_make_app_uses_injected_service():
    # Arrange
    mock = MagicMock()
    # Act
    app = make_app(ocr_service=mock)
    # Assert
    assert app.ocr_service is mock


@pytest.mark.unit
def test_make_app_does_not_call_build_on_injected_categories_service():
    # Arrange
    mock = MagicMock()
    # Act
    make_app(categories_service=mock)
    # Assert
    mock.build.assert_not_called()


@pytest.mark.unit
def test_make_app_does_not_call_build_on_injected_bank_categorization_service():
    # Arrange
    mock = MagicMock()
    # Act
    make_app(bank_categorization_service=mock)
    # Assert
    mock.build.assert_not_called()
