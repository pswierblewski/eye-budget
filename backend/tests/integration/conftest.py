import os
import pytest
import psycopg2
from testcontainers.postgres import PostgresContainer
from testcontainers.minio import MinioContainer
from yoyo import get_backend, read_migrations


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer() as minio:
        yield minio


@pytest.fixture(scope="session")
def migrated_db(postgres_container):
    url = postgres_container.get_connection_url()
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    backend = get_backend(url)
    migrations_path = os.path.join(os.path.dirname(__file__), "../../migrations")
    migrations = read_migrations(migrations_path)
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    return postgres_container


@pytest.fixture
def integration_app(migrated_db, minio_container):
    pg = migrated_db
    os.environ.update({
        "POSTGRESQL_HOST": pg.get_container_host_ip(),
        "POSTGRESQL_PORT": str(pg.get_exposed_port(5432)),
        "POSTGRESQL_DB": pg.dbname,
        "POSTGRESQL_USER": pg.username,
        "POSTGRESQL_PASSWORD": pg.password,
        "MINIO_ENDPOINT": f"{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}",
        "MINIO_ACCESS_KEY": minio_container.access_key,
        "MINIO_SECRET_KEY": minio_container.secret_key,
        # Dummy API key so LLM services can be constructed (they will be mocked in tests)
        "OPENAI_API_KEY": "sk-dummy-integration-test",
        "ANTHROPIC_API_KEY": "sk-dummy-integration-test",
    })
    from src.app import App
    app = App()
    yield app
    app.dispose()


@pytest.fixture(autouse=True)
def truncate_tables(migrated_db):
    """Truncate all public tables before each integration test for isolation."""
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
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        if tables:
            cur.execute(
                "TRUNCATE TABLE {} CASCADE".format(
                    ", ".join(f'"{t}"' for t in tables)
                )
            )
    conn.close()
