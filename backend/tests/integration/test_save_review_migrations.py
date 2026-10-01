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
def test_receipts_scans_has_save_review_columns(migrated_db):
    conn = _connect(migrated_db)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'receipts_scans' "
            "AND column_name IN ('category_selections', 'auto_confirm_waivers')"
        )
        columns = {row[0] for row in cur.fetchall()}
    conn.close()
    assert columns == {"category_selections", "auto_confirm_waivers"}
