import pytest
import psycopg2
from decimal import Decimal
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def insert_transaction(migrated_db, amount: float, reference: str = "REF001") -> int:
    """Insert a bank transaction directly via SQL and return its id."""
    pg = migrated_db
    conn = psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bank_transactions
                (reference_number, booking_date, amount, currency)
            VALUES (%s, '2026-04-09', %s, 'PLN')
            RETURNING id
            """,
            (reference, amount),
        )
        tx_id = cur.fetchone()[0]
    conn.close()
    return tx_id


def insert_category(migrated_db, name: str) -> int:
    """Insert a category and return its id."""
    pg = migrated_db
    conn = psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO categories (name, c_type) VALUES (%s, 'expense') RETURNING id",
            (name,),
        )
        cat_id = cur.fetchone()[0]
    conn.close()
    return cat_id


@pytest.mark.integration
def test_put_splits_happy_path(client, integration_app, migrated_db):
    # Arrange
    tx_id = insert_transaction(migrated_db, amount=200.0)
    cat1 = insert_category(migrated_db, "Jedzenie")
    cat2 = insert_category(migrated_db, "Chemia")

    # Act
    response = client.put(
        f"/bank-transactions/{tx_id}/splits",
        json={"splits": [
            {"category_id": cat1, "amount": 120.0},
            {"category_id": cat2, "amount": 80.0},
        ]},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tx_id
    assert data["category_id"] is None
    assert len(data["category_splits"]) == 2
    amounts_by_cat = {s["category_id"]: s["amount"] for s in data["category_splits"]}
    assert amounts_by_cat[cat1] == 120.0
    assert amounts_by_cat[cat2] == 80.0


@pytest.mark.integration
def test_put_splits_sum_mismatch_returns_409(client, integration_app, migrated_db):
    # Arrange
    tx_id = insert_transaction(migrated_db, amount=200.0, reference="REF002")
    cat1 = insert_category(migrated_db, "Kat1")
    cat2 = insert_category(migrated_db, "Kat2")

    # Act
    response = client.put(
        f"/bank-transactions/{tx_id}/splits",
        json={"splits": [
            {"category_id": cat1, "amount": 100.0},
            {"category_id": cat2, "amount": 50.0},  # sum = 150 ≠ 200
        ]},
    )

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_put_splits_fewer_than_two_returns_409(client, integration_app, migrated_db):
    # Arrange
    tx_id = insert_transaction(migrated_db, amount=200.0, reference="REF003")
    cat1 = insert_category(migrated_db, "Kat3")

    # Act
    response = client.put(
        f"/bank-transactions/{tx_id}/splits",
        json={"splits": [{"category_id": cat1, "amount": 200.0}]},
    )

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_put_splits_unknown_tx_returns_404(client, integration_app, migrated_db):
    # Arrange
    cat1 = insert_category(migrated_db, "Kat4")
    cat2 = insert_category(migrated_db, "Kat5")

    # Act
    response = client.put(
        "/bank-transactions/99999/splits",
        json={"splits": [
            {"category_id": cat1, "amount": 100.0},
            {"category_id": cat2, "amount": 100.0},
        ]},
    )

    # Assert
    assert response.status_code == 404


@pytest.mark.integration
def test_delete_splits_removes_split_and_returns_detail(client, integration_app, migrated_db):
    # Arrange — first create splits
    tx_id = insert_transaction(migrated_db, amount=200.0, reference="REF004")
    cat1 = insert_category(migrated_db, "Kat6")
    cat2 = insert_category(migrated_db, "Kat7")
    client.put(
        f"/bank-transactions/{tx_id}/splits",
        json={"splits": [
            {"category_id": cat1, "amount": 120.0},
            {"category_id": cat2, "amount": 80.0},
        ]},
    )

    # Act
    response = client.delete(f"/bank-transactions/{tx_id}/splits")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["category_splits"] is None or data["category_splits"] == []
    assert data["category_id"] is None


@pytest.mark.integration
def test_patch_category_after_splits_clears_splits(client, integration_app, migrated_db):
    # Arrange — create splits first
    tx_id = insert_transaction(migrated_db, amount=200.0, reference="REF005")
    cat1 = insert_category(migrated_db, "Kat8")
    cat2 = insert_category(migrated_db, "Kat9")
    client.put(
        f"/bank-transactions/{tx_id}/splits",
        json={"splits": [
            {"category_id": cat1, "amount": 120.0},
            {"category_id": cat2, "amount": 80.0},
        ]},
    )

    # Act — set single category via existing PATCH endpoint
    response = client.patch(
        f"/bank-transactions/{tx_id}/category",
        json={"category_id": cat1},
    )

    # Assert — splits should be gone, category_id set
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == cat1
    assert not data.get("category_splits")
