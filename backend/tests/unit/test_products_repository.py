import pytest
from unittest.mock import MagicMock
from src.data import NormalizedProductItem
from src.repositories.products import ProductsRepository


class ConcreteProducts(ProductsRepository):
    pass


def make_repo(fetchone_return=None, fetchone_side_effect=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    elif fetchone_return is not None:
        cursor.fetchone.return_value = fetchone_return
    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_all_products_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, "Mleko"), (2, "Chleb")])

    # Act
    result = repo.get_all_products()

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], NormalizedProductItem)
    assert result[0].id == 1
    assert result[0].name == "Mleko"
    assert result[1].id == 2
    assert result[1].name == "Chleb"


@pytest.mark.unit
def test_get_all_products_empty():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_all_products()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_products_no_conn_returns_empty():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.get_all_products()

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_all_products_db_error_returns_empty():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_all_products()

    # Assert
    assert result == []


@pytest.mark.unit
def test_insert_product_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.insert_product("Masło")

    # Assert
    assert result == 42
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "products" in s for s in sqls)


@pytest.mark.unit
def test_insert_product_no_result():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn

    # Act
    result = repo.insert_product("Masło")

    # Assert
    assert result is None


@pytest.mark.unit
def test_insert_product_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_product("Masło")

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_insert_product_no_conn_returns_none():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.insert_product("Masło")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_product_by_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(7,))

    # Act
    result = repo.get_product_by_name("Mleko")

    # Assert
    assert result == 7


@pytest.mark.unit
def test_get_product_by_name_not_found():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn

    # Act
    result = repo.get_product_by_name("Nieznany")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_product_by_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.get_product_by_name("Mleko")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_product_by_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_product_by_name("Mleko")

    # Assert
    assert result is None


@pytest.mark.unit
def test_insert_alternative_name_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.insert_alternative_name("MLEKO UHT 3.2%", 7)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "products_alternative_names" in s for s in sqls)


@pytest.mark.unit
def test_insert_alternative_name_conflict_returns_false():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn

    # Act
    result = repo.insert_alternative_name("MLEKO UHT 3.2%", 7)

    # Assert
    assert result is False
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_insert_alternative_name_db_error_returns_false():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_alternative_name("MLEKO UHT 3.2%", 7)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_insert_alternative_name_no_conn_returns_false():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.insert_alternative_name("MLEKO UHT 3.2%", 7)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_product_by_alternative_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(3,))

    # Act
    result = repo.get_product_by_alternative_name("MLEKO UHT")

    # Assert
    assert result == 3


@pytest.mark.unit
def test_get_product_by_alternative_name_not_found():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn

    # Act
    result = repo.get_product_by_alternative_name("UNKNOWN PRODUCT")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_product_by_alternative_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.get_product_by_alternative_name("MLEKO UHT")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_product_by_alternative_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_product_by_alternative_name("MLEKO UHT")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("Mleko",))

    # Act
    result = repo.get_normalized_name_by_alternative_name("MLEKO UHT 3.2%")

    # Assert
    assert result == "Mleko"


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_not_found():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = conn

    # Act
    result = repo.get_normalized_name_by_alternative_name("UNKNOWN PRODUCT")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_no_conn_returns_none():
    # Arrange
    repo = ConcreteProducts.__new__(ConcreteProducts)
    repo.conn = None

    # Act
    result = repo.get_normalized_name_by_alternative_name("MLEKO UHT")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.get_normalized_name_by_alternative_name("MLEKO UHT")

    # Assert
    assert result is None
