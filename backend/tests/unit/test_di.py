import pytest
from unittest.mock import MagicMock
from tests.unit.conftest import make_app


@pytest.mark.unit
def test_make_app_does_not_connect_to_db():
    app = make_app()
    app.eye_budget_db_context.connect_db.assert_not_called()


@pytest.mark.unit
def test_make_app_uses_injected_repos():
    mock = MagicMock()
    app = make_app(receipts_scans_repository=mock)
    assert app.receipts_scans_repository is mock


@pytest.mark.unit
def test_make_app_uses_injected_service():
    mock = MagicMock()
    app = make_app(ocr_service=mock)
    assert app.ocr_service is mock


@pytest.mark.unit
def test_make_app_does_not_call_build_on_injected_categories_service():
    mock = MagicMock()
    make_app(categories_service=mock)
    mock.build.assert_not_called()


@pytest.mark.unit
def test_make_app_does_not_call_build_on_injected_bank_categorization_service():
    mock = MagicMock()
    make_app(bank_categorization_service=mock)
    mock.build.assert_not_called()
