import pytest
from unittest.mock import MagicMock, call
from src.data import CategoryItem
from src.repositories.categories import CategoriesRepository


def make_repo(cursor_fetchone_side_effect=None, cursor_fetchone_return=None):
    """Build a CategoriesRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if cursor_fetchone_side_effect is not None:
        cursor.fetchone.side_effect = cursor_fetchone_side_effect
    elif cursor_fetchone_return is not None:
        cursor.fetchone.return_value = cursor_fetchone_return

    db_context = MagicMock()
    db_context.conn = conn

    repo = CategoriesRepository.__new__(CategoriesRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_create_category_happy_path_no_parent():
    # Arrange — duplicate-check returns nothing, INSERT returns new id
    repo, cursor = make_repo(
        cursor_fetchone_side_effect=[
            None,        # duplicate check → no existing row
            (42,),       # INSERT RETURNING id
        ]
    )

    # Act
    result = repo.create_category(name="Jedzenie", parent_id=None)

    # Assert
    assert isinstance(result, CategoryItem)
    assert result.id == 42
    assert result.name == "Jedzenie"
    assert result.parent_name is None
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_category_returns_existing_on_duplicate():
    # Arrange — duplicate-check returns an existing row
    repo, cursor = make_repo(
        cursor_fetchone_side_effect=[
            None,               # parent lookup (parent_id is not None → first call)
            (7, "Jedzenie", "Wydatki"),   # duplicate-check → found
        ]
    )

    # Act
    result = repo.create_category(name="Jedzenie", parent_id=3)

    # Assert — existing record returned, no INSERT
    assert isinstance(result, CategoryItem)
    assert result.id == 7
    assert result.name == "Jedzenie"
    assert result.parent_name == "Wydatki"
    repo.conn.commit.assert_not_called()

    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert not any("INSERT" in sql for sql in executed_sqls), "INSERT must not run when duplicate found"


@pytest.mark.unit
def test_create_category_with_parent():
    # Arrange — parent exists, no duplicate, INSERT succeeds
    repo, cursor = make_repo(
        cursor_fetchone_side_effect=[
            ("Wydatki",),   # parent name lookup
            None,           # duplicate-check → no existing row
            (99,),          # INSERT RETURNING id
        ]
    )

    # Act
    result = repo.create_category(name="Restauracje", parent_id=1)

    # Assert
    assert isinstance(result, CategoryItem)
    assert result.id == 99
    assert result.name == "Restauracje"
    assert result.parent_name == "Wydatki"
    repo.conn.commit.assert_called_once()
