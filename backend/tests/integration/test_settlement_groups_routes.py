import pytest
import psycopg2
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def insert_bank_tx(migrated_db, amount: float, ref: str = "SGT1") -> int:
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
            VALUES (%s, '2026-04-20', %s, 'PLN')
            RETURNING id
            """,
            (ref, amount),
        )
        tx_id = cur.fetchone()[0]
    conn.close()
    return tx_id


def insert_cash_tx(migrated_db, amount: float) -> int:
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
            INSERT INTO cash_transactions
                (booking_date, amount, currency, source, description)
            VALUES ('2026-04-20', %s, 'PLN', 'manual', 'cash op')
            RETURNING id
            """,
            (amount,),
        )
        tx_id = cur.fetchone()[0]
    conn.close()
    return tx_id


@pytest.mark.integration
def test_create_empty_group_and_list(client, integration_app, migrated_db):
    r = client.post(
        "/settlement-groups",
        json={"title": "Trip", "note": None, "members": []},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["id"] is not None
    assert data["member_count"] == 0
    assert data["title"] == "Trip"

    lst = client.get("/settlement-groups?search=Trip")
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] >= 1
    assert any(x["id"] == data["id"] for x in body["items"])


@pytest.mark.integration
def test_create_group_with_members_and_by_transaction(
    client, integration_app, migrated_db
):
    b1 = insert_bank_tx(migrated_db, -100.0, "SG1")
    b2 = insert_bank_tx(migrated_db, 50.0, "SG2")
    r = client.post(
        "/settlement-groups",
        json={
            "title": "Split",
            "members": [
                {"source_type": "bank", "id": b1},
                {"source_type": "bank", "id": b2},
            ],
        },
    )
    assert r.status_code == 201, r.text
    gid = r.json()["id"]

    b = client.get(
        f"/settlement-groups/by-transaction?source_type=bank&transaction_id={b1}"
    )
    assert b.status_code == 200
    assert b.json()["id"] == gid
    assert b.json()["member_count"] == 2
    assert float(b.json()["net"]) == pytest.approx(-50.0)

    txlist = client.get("/bank-transactions?limit=5")
    assert txlist.status_code == 200
    rows = {x["id"]: x for x in txlist.json()["items"]}
    assert rows[b1].get("settlement_group_id") == gid
    assert rows[b1].get("settlement_group_title") == "Split"

    d = client.delete(
        f"/settlement-groups/{gid}/members?source_type=bank&transaction_id={b1}"
    )
    assert d.status_code == 200
    assert d.json()["member_count"] == 1

    client.delete(f"/settlement-groups/{gid}")


@pytest.mark.integration
def test_conflict_member_already_grouped(
    client, integration_app, migrated_db
):
    b = insert_bank_tx(migrated_db, -10.0, "G2")
    r1 = client.post(
        "/settlement-groups",
        json={"members": [{"source_type": "bank", "id": b}]},
    )
    assert r1.status_code == 201
    g1 = r1.json()["id"]

    r2 = client.post(
        "/settlement-groups",
        json={"members": [{"source_type": "bank", "id": b}]},
    )
    assert r2.status_code == 409

    client.delete(f"/settlement-groups/{g1}")


@pytest.mark.integration
def test_remove_all_members_leaves_group(client, integration_app, migrated_db):
    c = insert_cash_tx(migrated_db, 25.0)
    r = client.post(
        "/settlement-groups",
        json={"members": [{"source_type": "cash", "id": c}]},
    )
    assert r.status_code == 201
    gid = r.json()["id"]

    d = client.delete(
        f"/settlement-groups/{gid}/members?source_type=cash&transaction_id={c}"
    )
    assert d.status_code == 200
    assert d.json()["member_count"] == 0

    g = client.get(f"/settlement-groups/{gid}")
    assert g.status_code == 200
    assert g.json()["member_count"] == 0

    client.delete(f"/settlement-groups/{gid}")


@pytest.mark.integration
def test_cash_list_has_settlement_group_id(client, integration_app, migrated_db):
    c = insert_cash_tx(migrated_db, 15.0)
    r = client.post(
        "/settlement-groups",
        json={
            "title": "CashGroupTitle",
            "members": [{"source_type": "cash", "id": c}],
        },
    )
    assert r.status_code == 201
    gid = r.json()["id"]

    lst = client.get("/cash-transactions?limit=20")
    assert lst.status_code == 200
    row = next((x for x in lst.json()["items"] if x["id"] == c), None)
    assert row is not None
    assert row.get("settlement_group_id") == gid
    assert row.get("settlement_group_title") == "CashGroupTitle"

    client.delete(f"/settlement-groups/{gid}")


@pytest.mark.integration
def test_get_by_transaction_404(client, integration_app, migrated_db):
    missing = 999_999_999
    r = client.get(
        f"/settlement-groups/by-transaction?source_type=bank&transaction_id={missing}"
    )
    assert r.status_code == 404


@pytest.mark.integration
def test_create_group_invalid_transaction_returns_400(
    client, integration_app, migrated_db
):
    r = client.post(
        "/settlement-groups",
        json={
            "members": [{"source_type": "bank", "id": 999_999_999}],
        },
    )
    assert r.status_code == 400


@pytest.mark.integration
def test_move_member_between_groups(client, integration_app, migrated_db):
    b = insert_bank_tx(migrated_db, -10.0, "MV1")
    r1 = client.post(
        "/settlement-groups",
        json={"title": "A", "members": [{"source_type": "bank", "id": b}]},
    )
    assert r1.status_code == 201
    g1 = r1.json()["id"]

    r2 = client.post(
        "/settlement-groups",
        json={"title": "B", "members": []},
    )
    assert r2.status_code == 201
    g2 = r2.json()["id"]

    mv = client.post(
        f"/settlement-groups/{g1}/members/move",
        json={
            "target_group_id": g2,
            "source_type": "bank",
            "id": b,
        },
    )
    assert mv.status_code == 200, mv.text
    assert mv.json()["id"] == g2
    assert mv.json()["member_count"] == 1

    by = client.get(
        f"/settlement-groups/by-transaction?source_type=bank&transaction_id={b}"
    )
    assert by.status_code == 200
    assert by.json()["id"] == g2

    left = client.get(f"/settlement-groups/{g1}")
    assert left.status_code == 200
    assert left.json()["member_count"] == 0

    client.delete(f"/settlement-groups/{g2}")
