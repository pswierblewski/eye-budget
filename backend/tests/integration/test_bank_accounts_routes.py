import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task dispatch so integration tests don't need a running Redis broker."""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    with patch(
        "src.main.categorize_bank_transactions_task.delay",
        return_value=mock_task,
    ):
        yield


REVOLUT_CSV = b"""Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
Deposit,Current,2026-01-09 14:16:48,2026-01-09 14:16:49,Payment from ACME,300.00,0.00,PLN,COMPLETED,484.21
Card Payment,Current,2026-01-12 11:01:02,2026-01-12 16:22:41,IDrive,-432.75,0.00,PLN,COMPLETED,51.46
"""

PEKAO_CSV = (
    "Data księgowania;Data waluty;Nadawca / Odbiorca;Adres nadawcy / odbiorcy;"
    "Rachunek źródłowy;Rachunek docelowy;Tytułem;Kwota operacji;Waluta;"
    "Numer referencyjny;Typ operacji\n"
    "01.01.2026;01.01.2026;Jan Kowalski;;12345;67890;Przelew;-100,00;PLN;REF001;Przelew\n"
).encode("utf-8")


@pytest.mark.integration
def test_create_and_list_bank_account(client, integration_app, migrated_db):
    # Arrange + Act
    response = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pekao SA"
    assert data["bank_type"] == "pekao"
    assert "id" in data

    # List
    list_resp = client.get("/bank-accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["transaction_count"] == 0


@pytest.mark.integration
def test_update_bank_account(client, integration_app, migrated_db):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Old Name", "bank_type": "pekao", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.put(
        f"/bank-accounts/{account_id}",
        json={"name": "New Name", "color": "green"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["color"] == "green"


@pytest.mark.integration
def test_create_duplicate_bank_account_returns_409(client, integration_app, migrated_db):
    # Arrange
    client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )

    # Act — same name + bank_type as an existing account
    response = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "green"},
    )

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_update_bank_account_to_duplicate_name_returns_409(client, integration_app, migrated_db):
    # Arrange
    client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )
    other_id = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA Konto 2", "bank_type": "pekao", "color": "green"},
    ).json()["id"]

    # Act — rename the second account to collide with the first
    response = client.put(
        f"/bank-accounts/{other_id}",
        json={"name": "Pekao SA", "color": "green"},
    )

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_update_nonexistent_account_returns_404(client, integration_app, migrated_db):
    response = client.put("/bank-accounts/9999", json={"name": "X", "color": "blue"})
    assert response.status_code == 404


@pytest.mark.integration
def test_delete_empty_account(client, integration_app, migrated_db):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "To Delete", "bank_type": "other", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.delete(f"/bank-accounts/{account_id}")

    # Assert
    assert response.status_code == 204


@pytest.mark.integration
def test_delete_account_with_transactions_returns_409(client, integration_app, migrated_db, mock_celery_task):
    # Arrange — create account then import a CSV to add transactions
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Revolut", "bank_type": "revolut", "color": "purple"},
    )
    account_id = create_resp.json()["id"]

    import_resp = client.post(
        "/bank-transactions/import",
        data={"account_id": str(account_id)},
        files={"file": ("revolut.csv", REVOLUT_CSV, "text/csv")},
    )
    assert import_resp.status_code == 201

    # Act
    response = client.delete(f"/bank-accounts/{account_id}")

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_import_pekao_csv_with_account_id(client, integration_app, migrated_db, mock_celery_task):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.post(
        "/bank-transactions/import",
        data={"account_id": str(account_id)},
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 1

    # Verify account stats updated
    list_resp = client.get("/bank-accounts")
    accounts = list_resp.json()
    assert accounts[0]["transaction_count"] == 1


@pytest.mark.integration
def test_import_without_account_id_returns_422(client, integration_app, migrated_db):
    response = client.post(
        "/bank-transactions/import",
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_list_bank_transactions_filter_by_account(client, integration_app, migrated_db, mock_celery_task):
    # Arrange — two accounts, import into each
    acc1 = client.post("/bank-accounts", json={"name": "Pekao", "bank_type": "pekao", "color": "blue"}).json()["id"]
    acc2 = client.post("/bank-accounts", json={"name": "Revolut", "bank_type": "revolut", "color": "purple"}).json()["id"]

    client.post(
        "/bank-transactions/import",
        data={"account_id": str(acc1)},
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )
    client.post(
        "/bank-transactions/import",
        data={"account_id": str(acc2)},
        files={"file": ("revolut.csv", REVOLUT_CSV, "text/csv")},
    )

    # Act — filter by acc1
    resp = client.get(f"/bank-transactions?account_id={acc1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert all(item["account_id"] == acc1 for item in data["items"])
