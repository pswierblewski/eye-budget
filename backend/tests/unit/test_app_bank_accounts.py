"""Unit tests for App bank account creation/update duplicate handling."""
import psycopg2.errors
import pytest
from tests.unit.conftest import make_app

from src.app import DuplicateBankAccountError


@pytest.mark.unit
def test_create_bank_account_delegates_to_repository():
    # Arrange
    app = make_app()
    app.bank_accounts_repository.create.return_value = "created"

    # Act
    result = app.create_bank_account("Pekao SA", "pekao", "blue")

    # Assert
    assert result == "created"
    app.bank_accounts_repository.create.assert_called_once_with("Pekao SA", "pekao", "blue")


@pytest.mark.unit
def test_create_bank_account_raises_duplicate_error_on_unique_violation():
    # Arrange
    app = make_app()
    app.bank_accounts_repository.create.side_effect = psycopg2.errors.UniqueViolation()

    # Act / Assert
    with pytest.raises(DuplicateBankAccountError):
        app.create_bank_account("Pekao SA", "pekao", "blue")


@pytest.mark.unit
def test_update_bank_account_raises_duplicate_error_on_unique_violation():
    # Arrange
    app = make_app()
    app.bank_accounts_repository.update.side_effect = psycopg2.errors.UniqueViolation()

    # Act / Assert
    with pytest.raises(DuplicateBankAccountError):
        app.update_bank_account(1, "Pekao SA", "green")
