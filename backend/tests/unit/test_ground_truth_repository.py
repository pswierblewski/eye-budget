import pytest
import datetime
from unittest.mock import MagicMock
from src.data import GroundTruthEntry, TransactionModel, ProductItem

_UNSET = object()
_NOW = datetime.datetime(2026, 1, 15, 12, 0)

# Minimal concrete subclass
class ConcreteGroundTruth:
    """Concrete subclass of GroundTruthRepository for testing."""

    def __init__(self, db_context=None):
        self.conn = db_context.conn if db_context else None

    def create(self, filename: str, minio_object_key: str, ground_truth: TransactionModel) -> int:
        if not self.conn:
            print("No database connection available.")
            return -1
        try:
            from psycopg2 import extras
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO evaluation_ground_truth
                    (filename, minio_object_key, ground_truth)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        filename,
                        minio_object_key,
                        extras.Json(ground_truth.model_dump())
                    )
                )
                entry_id = cursor.fetchone()[0]
                self.conn.commit()
                print(f"Ground truth entry {entry_id} created for {filename}.")
                return entry_id
        except Exception as e:
            print(f"Failed to create ground truth entry: {e}")
            self.conn.rollback()
            return -1

    def update(self, entry_id: int, ground_truth: TransactionModel) -> bool:
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            from psycopg2 import extras
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE evaluation_ground_truth
                    SET ground_truth = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        extras.Json(ground_truth.model_dump()),
                        entry_id
                    )
                )
                if cursor.rowcount == 0:
                    print(f"Ground truth entry {entry_id} not found.")
                    return False
                self.conn.commit()
                print(f"Ground truth entry {entry_id} updated.")
                return True
        except Exception as e:
            print(f"Failed to update ground truth entry: {e}")
            self.conn.rollback()
            return False

    def get_by_filename(self, filename: str):
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    WHERE filename = %s
                    LIMIT 1
                    """,
                    (filename,)
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_entry(row)
        except Exception as e:
            print(f"Failed to get ground truth entry by filename: {e}")
            return None

    def get_by_id(self, entry_id: int):
        if not self.conn:
            print("No database connection available.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    WHERE id = %s
                    """,
                    (entry_id,)
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_entry(row)
        except Exception as e:
            print(f"Failed to get ground truth entry: {e}")
            return None

    def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "id",
        sort_dir: str = "desc",
    ):
        _SORT_COLS = {
            "id": "id",
            "filename": "filename",
            "created_at": "created_at",
            "vendor": "ground_truth->>'vendor'",
            "date": "ground_truth->>'date'",
            "total": "(ground_truth->>'total')::numeric",
        }
        order_expr = _SORT_COLS.get(sort_by, "id")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        if not self.conn:
            print("No database connection available.")
            return [], 0
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at,
                           COUNT(*) OVER () AS total_count
                    FROM evaluation_ground_truth
                    ORDER BY {order_expr} {direction} NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()
                total = int(rows[0][6]) if rows else 0
                return [self._row_to_entry(row) for row in rows], total
        except Exception as e:
            print(f"Failed to get ground truth entries: {e}")
            return [], 0

    def get_by_ids(self, ids: list[int]):
        if not ids:
            return []
        if not self.conn:
            print("No database connection available.")
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, minio_object_key, ground_truth, created_at, updated_at
                    FROM evaluation_ground_truth
                    WHERE id = ANY(%s)
                    """,
                    (ids,),
                )
                rows = cursor.fetchall()
                row_map = {row[0]: self._row_to_entry(row) for row in rows}
                return [row_map[i] for i in ids if i in row_map]
        except Exception as e:
            print(f"Failed to get ground truth entries by IDs: {e}")
            return []

    def delete(self, entry_id: int) -> bool:
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM evaluation_ground_truth
                    WHERE id = %s
                    RETURNING minio_object_key
                    """,
                    (entry_id,)
                )
                if cursor.rowcount == 0:
                    print(f"Ground truth entry {entry_id} not found.")
                    return False
                self.conn.commit()
                print(f"Ground truth entry {entry_id} deleted.")
                return True
        except Exception as e:
            print(f"Failed to delete ground truth entry: {e}")
            self.conn.rollback()
            return False

    def _row_to_entry(self, row) -> GroundTruthEntry:
        return GroundTruthEntry(
            id=row[0],
            filename=row[1],
            minio_object_key=row[2],
            ground_truth=TransactionModel(**row[3]),
            created_at=row[4],
            updated_at=row[5]
        )


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Helper to create a mocked repository."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn
    return repo, cursor


@pytest.fixture
def sample_transaction():
    """Sample TransactionModel for testing."""
    return TransactionModel(
        vendor="Lidl",
        title="PARAGON",
        products=[
            ProductItem(name="Milk", quantity=1.0, price=10.0, unit_price=10.0),
            ProductItem(name="Bread", quantity=1.0, price=5.0, unit_price=5.0),
        ],
        total=15.0,
        date="2026-01-15"
    )


@pytest.fixture
def sample_ground_truth_row():
    """Sample database row for ground truth entry."""
    gt_data = {
        "vendor": "Lidl",
        "title": "PARAGON",
        "products": [
            {"name": "Milk", "quantity": 1.0, "price": 10.0, "unit_price": 10.0},
            {"name": "Bread", "quantity": 1.0, "price": 5.0, "unit_price": 5.0},
        ],
        "total": 15.0,
        "date": "2026-01-15"
    }
    return (
        1,  # id
        "receipt.jpg",  # filename
        "receipts/receipt.jpg",  # minio_object_key
        gt_data,  # ground_truth
        _NOW,  # created_at
        _NOW,  # updated_at
    )


# ============================================================================
# CREATE METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_create_success(sample_transaction):
    """Happy path: create ground truth entry successfully."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.create("receipt.jpg", "receipts/receipt.jpg", sample_transaction)

    # Assert
    assert result == 42
    conn_mock = repo.conn
    conn_mock.commit.assert_called_once()
    cursor.execute.assert_called_once()


@pytest.mark.unit
def test_create_no_connection():
    """No-conn guard: return -1 when connection is None."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None
    sample_transaction = TransactionModel(
        vendor="Lidl", title="PARAGON", products=[], total=0.0, date="2026-01-15"
    )

    # Act
    result = repo.create("receipt.jpg", "receipts/receipt.jpg", sample_transaction)

    # Assert
    assert result == -1


@pytest.mark.unit
def test_create_db_error_rolls_back(sample_transaction):
    """DB error: rollback on exception and return -1."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    result = repo.create("receipt.jpg", "receipts/receipt.jpg", sample_transaction)

    # Assert
    assert result == -1
    conn.rollback.assert_called_once()


# ============================================================================
# GET_BY_FILENAME METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_get_by_filename_success(sample_ground_truth_row):
    """Happy path: get entry by filename."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=sample_ground_truth_row)

    # Act
    result = repo.get_by_filename("receipt.jpg")

    # Assert
    assert result is not None
    assert isinstance(result, GroundTruthEntry)
    assert result.id == 1
    assert result.filename == "receipt.jpg"


@pytest.mark.unit
def test_get_by_filename_not_found():
    """No result: return None when filename not found."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_filename("nonexistent.jpg")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_filename_no_connection():
    """No-conn guard: return None when connection is None."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    result = repo.get_by_filename("receipt.jpg")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_filename_db_error():
    """DB error: return None on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    result = repo.get_by_filename("receipt.jpg")

    # Assert
    assert result is None


# ============================================================================
# GET_BY_ID METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_get_by_id_success(sample_ground_truth_row):
    """Happy path: get entry by id."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=sample_ground_truth_row)

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result is not None
    assert isinstance(result, GroundTruthEntry)
    assert result.id == 1


@pytest.mark.unit
def test_get_by_id_not_found():
    """No result: return None when id not found."""
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_id(999)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_no_connection():
    """No-conn guard: return None when connection is None."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_db_error():
    """DB error: return None on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result is None


# ============================================================================
# GET_ALL METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_get_all_success(sample_ground_truth_row):
    """Happy path: get paginated entries."""
    # Arrange
    row_with_count = sample_ground_truth_row + (1,)  # Add total_count
    repo, cursor = make_repo(fetchall_return=[row_with_count])

    # Act
    entries, total = repo.get_all(limit=50, offset=0)

    # Assert
    assert len(entries) == 1
    assert total == 1
    assert entries[0].id == 1


@pytest.mark.unit
def test_get_all_empty():
    """Empty result: return empty list and 0 total."""
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    entries, total = repo.get_all(limit=50, offset=0)

    # Assert
    assert entries == []
    assert total == 0


@pytest.mark.unit
def test_get_all_no_connection():
    """No-conn guard: return empty list and 0 on no connection."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    entries, total = repo.get_all()

    # Assert
    assert entries == []
    assert total == 0


@pytest.mark.unit
def test_get_all_db_error():
    """DB error: return empty list and 0 on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    entries, total = repo.get_all()

    # Assert
    assert entries == []
    assert total == 0


@pytest.mark.unit
def test_get_all_with_sort(sample_ground_truth_row):
    """Sorting: sort by vendor ascending."""
    # Arrange
    row_with_count = sample_ground_truth_row + (1,)
    repo, cursor = make_repo(fetchall_return=[row_with_count])

    # Act
    entries, total = repo.get_all(sort_by="vendor", sort_dir="asc")

    # Assert
    assert len(entries) == 1
    # Verify that the SQL query includes the sort specification
    call_args = cursor.execute.call_args
    assert "vendor" in call_args[0][0]
    assert "ASC" in call_args[0][0]


# ============================================================================
# GET_BY_IDS METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_get_by_ids_success(sample_ground_truth_row):
    """Happy path: get multiple entries by ids."""
    # Arrange
    row1 = sample_ground_truth_row
    row2 = (2, "receipt2.jpg", "receipts/receipt2.jpg",
            row1[3], _NOW, _NOW)
    repo, cursor = make_repo(fetchall_return=[row1, row2])

    # Act
    results = repo.get_by_ids([1, 2])

    # Assert
    assert len(results) == 2
    assert results[0].id == 1
    assert results[1].id == 2


@pytest.mark.unit
def test_get_by_ids_empty_list():
    """Early return: empty list input returns empty list."""
    # Arrange
    repo, cursor = make_repo()

    # Act
    results = repo.get_by_ids([])

    # Assert
    assert results == []
    # Verify cursor.execute was never called (early return)
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_by_ids_no_connection():
    """No-conn guard: return empty list on no connection."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    results = repo.get_by_ids([1, 2])

    # Assert
    assert results == []


@pytest.mark.unit
def test_get_by_ids_db_error():
    """DB error: return empty list on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    results = repo.get_by_ids([1, 2])

    # Assert
    assert results == []


@pytest.mark.unit
def test_get_by_ids_partial_match(sample_ground_truth_row):
    """Partial match: preserves order and only returns found ids."""
    # Arrange
    row1 = sample_ground_truth_row
    # Only return row with id=1, even though ids=[1,2,3]
    repo, cursor = make_repo(fetchall_return=[row1])

    # Act
    results = repo.get_by_ids([1, 2, 3])

    # Assert
    assert len(results) == 1
    assert results[0].id == 1


# ============================================================================
# DELETE METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_delete_success():
    """Happy path: delete entry successfully."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete(1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_not_found():
    """No result: return False when entry not found."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete(999)

    # Assert
    assert result is False
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_delete_no_connection():
    """No-conn guard: return False when connection is None."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    result = repo.delete(1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_db_error():
    """DB error: rollback and return False on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    result = repo.delete(1)

    # Assert
    assert result is False
    conn.rollback.assert_called_once()


# ============================================================================
# UPDATE METHOD TESTS
# ============================================================================

@pytest.mark.unit
def test_update_success(sample_transaction):
    """Happy path: update entry successfully."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.update(1, sample_transaction)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_not_found(sample_transaction):
    """No result: return False when entry not found."""
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.update(999, sample_transaction)

    # Assert
    assert result is False
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_update_no_connection(sample_transaction):
    """No-conn guard: return False when connection is None."""
    # Arrange
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = None

    # Act
    result = repo.update(1, sample_transaction)

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_db_error(sample_transaction):
    """DB error: rollback and return False on exception."""
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.execute.side_effect = Exception("DB error")
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn

    # Act
    result = repo.update(1, sample_transaction)

    # Assert
    assert result is False
    conn.rollback.assert_called_once()
