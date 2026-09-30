import pytest
import psycopg2


def _connect(pg):
    return psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )


@pytest.mark.integration
def test_receipts_scans_has_auto_confirm_columns(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'receipts_scans' "
            "AND column_name IN ('confirmation_source', 'auto_confirm_reasons')"
        )
        columns = {row[0] for row in cur.fetchall()}
    conn.close()

    # Assert
    assert columns == {"confirmation_source", "auto_confirm_reasons"}


@pytest.mark.integration
def test_prompt_analytics_has_reverted_flag(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'prompt_analytics' AND column_name = 'auto_confirm_reverted'"
        )
        row = cur.fetchone()
    conn.close()

    # Assert
    assert row is not None
    assert "false" in row[0]


@pytest.mark.integration
def test_pg_trgm_installed_in_test_container(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        row = cur.fetchone()
    conn.close()

    # Assert
    assert row is not None
