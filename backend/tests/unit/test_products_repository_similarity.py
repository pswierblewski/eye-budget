import pytest
from unittest.mock import MagicMock

from src.repositories.products import ProductsRepository
from src.repositories.vendors import VendorsRepository


def _repo(cls, fetchall=None, fetchone=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    repo = cls.__new__(cls)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_has_trigram_support_true():
    # Arrange
    repo, _ = _repo(ProductsRepository, fetchone=(True,))

    # Act / Assert
    assert repo.has_trigram_support() is True


@pytest.mark.unit
def test_has_trigram_support_error_is_false():
    # Arrange
    repo, cursor = _repo(ProductsRepository)
    cursor.execute.side_effect = Exception("boom")

    # Act / Assert
    assert repo.has_trigram_support() is False


@pytest.mark.unit
def test_find_similar_alternative_names_maps_rows():
    # Arrange
    repo, cursor = _repo(ProductsRepository, fetchall=[("MLEKO 2%", 4, 0.72)])

    # Act
    rows = repo.find_similar_alternative_names("MLEKO 3%", limit=5, min_similarity=0.3)

    # Assert
    assert rows == [("MLEKO 2%", 4, 0.72)]
    sql, params = cursor.execute.call_args[0]
    assert "similarity(name, %s)" in sql
    assert params == ("MLEKO 3%", "MLEKO 3%", "MLEKO 3%", 0.3, 5)


@pytest.mark.unit
def test_find_similar_alternative_names_error_rolls_back_and_raises():
    # Arrange
    repo, cursor = _repo(ProductsRepository)
    cursor.execute.side_effect = Exception("function similarity does not exist")

    # Act / Assert
    with pytest.raises(Exception):
        repo.find_similar_alternative_names("X")
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_get_all_alternative_names():
    # Arrange
    repo, _ = _repo(ProductsRepository, fetchall=[("A", 1), ("B", 2)])

    # Act / Assert
    assert repo.get_all_alternative_names() == [("A", 1), ("B", 2)]


@pytest.mark.unit
def test_get_names_by_ids():
    # Arrange
    repo, cursor = _repo(ProductsRepository, fetchall=[(1, "Mleko"), (2, "Chleb")])

    # Act
    result = repo.get_names_by_ids([1, 2])

    # Assert
    assert result == {1: "Mleko", 2: "Chleb"}
    assert cursor.execute.call_args[0][1] == ([1, 2],)


@pytest.mark.unit
def test_get_names_by_ids_empty_skips_query():
    # Arrange
    repo, cursor = _repo(ProductsRepository)

    # Act / Assert
    assert repo.get_names_by_ids([]) == {}
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_product_upsert_alternative_name_overwrites():
    # Arrange
    repo, cursor = _repo(ProductsRepository)

    # Act
    ok = repo.upsert_alternative_name("MLEKO", 7)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "ON CONFLICT (name) DO UPDATE SET product = EXCLUDED.product" in sql
    assert params == ("MLEKO", 7)
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_vendor_upsert_alternative_name_overwrites():
    # Arrange
    repo, cursor = _repo(VendorsRepository)

    # Act
    ok = repo.upsert_alternative_name("BIEDRONKA 1234", 3)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "ON CONFLICT (name) DO UPDATE SET vendor = EXCLUDED.vendor" in sql
    assert params == ("BIEDRONKA 1234", 3)
