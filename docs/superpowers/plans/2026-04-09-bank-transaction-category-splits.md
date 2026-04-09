# Bank Transaction Category Splits — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to split a bank transaction amount across multiple categories (≥ 2), each with an explicit PLN amount that must sum to the transaction total.

**Architecture:** New `bank_transaction_category_splits` table coexists with `bank_transactions.category_id`. Invariant: if splits exist → `category_id` is NULL; if `category_id` is set → no splits. Two new backend endpoints (`PUT`/`DELETE /bank-transactions/{id}/splits`) and a shared `BankTransactionSplitEditor` React component used in both the list expanded row and the detail page.

**Tech Stack:** Python/FastAPI/psycopg2/Pydantic v2 (backend), TypeScript/Next.js 14/React Query v5/Tailwind (frontend), PostgreSQL, yoyo migrations.

---

## File Map

**Create:**
- `backend/migrations/20260409_01_bank-transaction-category-splits.sql`
- `backend/src/repositories/bank_transaction_splits.py`
- `backend/tests/unit/test_bank_transaction_splits_repository.py`
- `backend/tests/integration/test_bank_transaction_splits_routes.py`
- `frontend/app/api/bank-transactions/[id]/splits/route.ts`
- `frontend/components/BankTransactionSplitEditor.tsx`

**Modify:**
- `backend/src/data.py` — new models, extend list/detail models
- `backend/src/repositories/bank_transactions.py` — `update_category`, `get_list`, `get_by_id`
- `backend/src/app.py` — wire repository, add two App methods, update `dispose()`
- `backend/tests/unit/conftest.py` — add `bank_transaction_splits_repository` to `ALL_PARAMS`
- `backend/src/main.py` — two new routes
- `frontend/lib/types.ts` — new schema, extend existing schemas
- `frontend/lib/api.ts` — two new API functions
- `frontend/app/bank-transactions/page.tsx` — category column + split editor in expanded row
- `frontend/app/bank-transactions/[id]/page.tsx` — category card with split editor

---

## Task 1: Database Migration

**Files:**
- Create: `backend/migrations/20260409_01_bank-transaction-category-splits.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- depends: 20260227_01_bank_transactions

CREATE TABLE IF NOT EXISTS bank_transaction_category_splits (
    id                  SERIAL PRIMARY KEY,
    bank_transaction_id INTEGER NOT NULL
                            REFERENCES bank_transactions(id) ON DELETE CASCADE,
    category_id         INTEGER NOT NULL
                            REFERENCES categories(id) ON DELETE RESTRICT,
    amount              NUMERIC(12, 2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_btcs_bank_transaction_id
    ON bank_transaction_category_splits(bank_transaction_id);
```

- [ ] **Step 2: Apply migration locally and verify**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
yoyo apply --database "$(python -c "import os; from dotenv import load_dotenv; load_dotenv('../.env'); print(f\"postgresql://{os.getenv('POSTGRESQL_USER')}:{os.getenv('POSTGRESQL_PASSWORD')}@{os.getenv('POSTGRESQL_HOST')}:{os.getenv('POSTGRESQL_PORT')}/{os.getenv('POSTGRESQL_DB')}\")")"
```

Expected: migration applied without errors. Table `bank_transaction_category_splits` visible in psql:
```sql
\d bank_transaction_category_splits
```

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/20260409_01_bank-transaction-category-splits.sql
git commit -m "feat: add bank_transaction_category_splits migration"
```

---

## Task 2: Backend Pydantic Models

**Files:**
- Modify: `backend/src/data.py`

- [ ] **Step 1: Add new models and extend existing ones**

In `backend/src/data.py`, add the following models (place them near the existing `BankTransactionListItem` and `BankTransactionDetail` classes):

```python
class BankTransactionSplit(BaseModel):
    """One category slice of a split bank transaction."""
    id: int
    category_id: int
    category_name: str
    amount: float


class SplitItem(BaseModel):
    """One item in an UpdateBankTransactionSplitsRequest."""
    category_id: int
    amount: float


class UpdateBankTransactionSplitsRequest(BaseModel):
    """Request body for PUT /bank-transactions/{id}/splits."""
    splits: list[SplitItem]
```

Extend `BankTransactionListItem` — add two fields at the end:
```python
    split_category_name: str | None = None
    split_count: int | None = None
```

Extend `BankTransactionDetail` — add one field at the end:
```python
    category_splits: list[BankTransactionSplit] | None = None
```

- [ ] **Step 2: Verify no import errors**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -c "from src.data import BankTransactionSplit, SplitItem, UpdateBankTransactionSplitsRequest, BankTransactionListItem, BankTransactionDetail; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/src/data.py
git commit -m "feat: add BankTransactionSplit, SplitItem, UpdateBankTransactionSplitsRequest to data.py"
```

---

## Task 3: BankTransactionSplitsRepository (TDD)

**Files:**
- Create: `backend/src/repositories/bank_transaction_splits.py`
- Create: `backend/tests/unit/test_bank_transaction_splits_repository.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_bank_transaction_splits_repository.py`:

```python
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from src.data import BankTransactionSplit, SplitItem
from src.repositories.bank_transaction_splits import BankTransactionSplitsRepository


def make_repo(fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_upsert_splits_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, 5, "Jedzenie", 120.0), (2, 7, "Chemia", 80.0)])
    splits = [SplitItem(category_id=5, amount=120.0), SplitItem(category_id=7, amount=80.0)]

    # Act
    result = repo.upsert_splits(tx_id=1, splits=splits)

    # Assert
    assert len(result) == 2
    assert result[0].category_name == "Jedzenie"
    assert result[0].amount == 120.0
    assert result[1].category_id == 7
    repo.conn.commit.assert_called_once()
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s and "bank_transaction_category_splits" in s for s in executed_sqls)
    assert any("UPDATE" in s and "category_id = NULL" in s for s in executed_sqls)
    assert any("INSERT" in s and "bank_transaction_category_splits" in s for s in executed_sqls)


@pytest.mark.unit
def test_upsert_splits_no_conn_returns_empty():
    # Arrange
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = None

    # Act
    result = repo.upsert_splits(tx_id=1, splits=[SplitItem(category_id=5, amount=100.0)])

    # Assert
    assert result == []


@pytest.mark.unit
def test_upsert_splits_db_error_rolls_back():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.upsert_splits(tx_id=1, splits=[SplitItem(category_id=5, amount=100.0)])

    # Assert
    assert result == []
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_splits_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_splits(tx_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s and "bank_transaction_category_splits" in s for s in executed_sqls)


@pytest.mark.unit
def test_delete_splits_no_conn_returns_false():
    # Arrange
    repo = BankTransactionSplitsRepository.__new__(BankTransactionSplitsRepository)
    repo.conn = None

    # Act
    result = repo.delete_splits(tx_id=1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_splits_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, 5, "Jedzenie", 120.0)])

    # Act
    result = repo.get_splits(tx_id=42)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], BankTransactionSplit)
    assert result[0].id == 1
    assert result[0].category_name == "Jedzenie"
    assert result[0].amount == 120.0


@pytest.mark.unit
def test_get_splits_empty_returns_empty_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    result = repo.get_splits(tx_id=99)

    # Assert
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/test_bank_transaction_splits_repository.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError` or `ImportError` (module does not exist yet).

- [ ] **Step 3: Implement BankTransactionSplitsRepository**

Create `backend/src/repositories/bank_transaction_splits.py`:

```python
"""Repository for bank_transaction_category_splits table."""
from __future__ import annotations

from ..data import BankTransactionSplit, SplitItem


class BankTransactionSplitsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def upsert_splits(self, tx_id: int, splits: list[SplitItem]) -> list[BankTransactionSplit]:
        """Replace all splits for a transaction and clear category_id (invariant)."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM bank_transaction_category_splits WHERE bank_transaction_id = %s",
                    (tx_id,),
                )
                cur.execute(
                    "UPDATE bank_transactions SET category_id = NULL WHERE id = %s",
                    (tx_id,),
                )
                for split in splits:
                    cur.execute(
                        """
                        INSERT INTO bank_transaction_category_splits
                            (bank_transaction_id, category_id, amount)
                        VALUES (%s, %s, %s)
                        """,
                        (tx_id, split.category_id, split.amount),
                    )
            self.conn.commit()
            return self.get_splits(tx_id)
        except Exception as e:
            print(f"BankTransactionSplitsRepository.upsert_splits error: {e}")
            self.conn.rollback()
            return []

    def delete_splits(self, tx_id: int) -> bool:
        """Remove all splits for a transaction."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM bank_transaction_category_splits WHERE bank_transaction_id = %s",
                    (tx_id,),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"BankTransactionSplitsRepository.delete_splits error: {e}")
            self.conn.rollback()
            return False

    def get_splits(self, tx_id: int) -> list[BankTransactionSplit]:
        """Fetch all splits for a transaction with category names resolved."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.category_id, c.name AS category_name, s.amount
                    FROM bank_transaction_category_splits s
                    JOIN categories c ON c.id = s.category_id
                    WHERE s.bank_transaction_id = %s
                    ORDER BY s.id
                    """,
                    (tx_id,),
                )
                rows = cur.fetchall()
            return [
                BankTransactionSplit(
                    id=row[0],
                    category_id=row[1],
                    category_name=row[2],
                    amount=float(row[3]),
                )
                for row in rows
            ]
        except Exception as e:
            print(f"BankTransactionSplitsRepository.get_splits error: {e}")
            return []

    def dispose(self) -> None:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/test_bank_transaction_splits_repository.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories/bank_transaction_splits.py \
        backend/tests/unit/test_bank_transaction_splits_repository.py
git commit -m "feat: add BankTransactionSplitsRepository with unit tests"
```

---

## Task 4: Update BankTransactionsRepository

**Files:**
- Modify: `backend/src/repositories/bank_transactions.py`
- Create test additions: `backend/tests/unit/test_bank_transactions_repository_splits.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_bank_transactions_repository_splits.py`:

```python
import pytest
from unittest.mock import MagicMock, call
from src.repositories.bank_transactions import BankTransactionsRepository


def make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = BankTransactionsRepository.__new__(BankTransactionsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_update_category_deletes_splits_before_setting_category():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.update_category(transaction_id=1, category_id=5)

    # Assert — DELETE from splits must come before UPDATE on bank_transactions
    executed_sqls = [c.args[0] for c in cursor.execute.call_args_list]
    delete_idx = next(
        i for i, s in enumerate(executed_sqls)
        if "DELETE" in s and "bank_transaction_category_splits" in s
    )
    update_idx = next(
        i for i, s in enumerate(executed_sqls)
        if "UPDATE" in s and "bank_transactions" in s
    )
    assert delete_idx < update_idx
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_category_rollback_on_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    repo.update_category(transaction_id=1, category_id=5)

    # Assert
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/test_bank_transactions_repository_splits.py -v
```

Expected: `test_update_category_deletes_splits_before_setting_category` FAILS (current `update_category` doesn't DELETE splits).

- [ ] **Step 3: Update `update_category` in `bank_transactions.py`**

Replace the existing `update_category` method in `backend/src/repositories/bank_transactions.py`:

```python
def update_category(self, transaction_id: int, category_id: Optional[int]) -> None:
    """Set or clear the category on a bank transaction.

    Maintains the splits invariant: any existing splits are deleted first
    so that category_id and splits are never both set simultaneously.
    """
    if not self.conn:
        return
    try:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM bank_transaction_category_splits WHERE bank_transaction_id = %s",
                (transaction_id,),
            )
            cur.execute(
                "UPDATE bank_transactions SET category_id = %s WHERE id = %s",
                (category_id, transaction_id),
            )
        self.conn.commit()
    except Exception as e:
        print(f"BankTransactionsRepository.update_category error: {e}")
        self.conn.rollback()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/test_bank_transactions_repository_splits.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Update `get_list` to include `split_category_name` and `split_count`**

In `backend/src/repositories/bank_transactions.py`, replace the `get_list` method's SQL query.

The current SELECT in `get_list` has 14 columns (indices 0–13), where index 13 is `COUNT(*) OVER () AS total_count`. Add two subqueries before `total_count`, making total_count move to index 15.

Replace the `cur.execute(...)` call in `get_list` with:

```python
                cur.execute(
                    f"""
                    SELECT bt.id, bt.reference_number, bt.booking_date,
                           bt.counterparty, bt.description, bt.amount, bt.currency,
                           bt.operation_type, bt.category_id, c.name,
                           bt.tags,
                           (
                               SELECT CONCAT_WS(' / ', pc.name, cat.name)
                               FROM receipt_bank_links rbl2
                               JOIN receipt_transaction_items rti ON rti.transaction_id = rbl2.receipt_transaction_id
                               JOIN categories cat ON cat.id = rti.category_id
                               LEFT JOIN categories pc ON pc.id = cat.parent_id
                               WHERE rbl2.bank_transaction_id = bt.id
                               GROUP BY cat.id, cat.name, pc.name
                               ORDER BY COUNT(*) DESC
                               LIMIT 1
                           ) AS receipt_category_name,
                           (
                               SELECT COUNT(DISTINCT rti.category_id)
                               FROM receipt_bank_links rbl2
                               JOIN receipt_transaction_items rti ON rti.transaction_id = rbl2.receipt_transaction_id
                               WHERE rbl2.bank_transaction_id = bt.id
                           ) AS receipt_category_count,
                           (
                               SELECT c2.name
                               FROM bank_transaction_category_splits s
                               JOIN categories c2 ON c2.id = s.category_id
                               WHERE s.bank_transaction_id = bt.id
                               ORDER BY s.id ASC
                               LIMIT 1
                           ) AS split_category_name,
                           NULLIF((
                               SELECT COUNT(*)
                               FROM bank_transaction_category_splits s
                               WHERE s.bank_transaction_id = bt.id
                           ), 0) AS split_count,
                           COUNT(*) OVER () AS total_count
                    FROM bank_transactions bt
                    LEFT JOIN categories c ON c.id = bt.category_id
                    {where}
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
```

Also update the row unpacking below (change index 13 from `total_count` to index 15, and add new fields at 13 and 14):

```python
            total = int(rows[0][15]) if rows else 0
            return [
                BankTransactionListItem(
                    id=r[0],
                    reference_number=r[1],
                    booking_date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                    counterparty=r[3],
                    description=r[4],
                    amount=float(r[5]),
                    currency=r[6],
                    operation_type=r[7],
                    category_id=r[8],
                    category_name=r[9],
                    tags=list(r[10]) if r[10] else [],
                    receipt_category_name=r[11],
                    receipt_category_count=int(r[12]) if r[12] is not None else None,
                    split_category_name=r[13],
                    split_count=int(r[14]) if r[14] is not None else None,
                )
                for r in rows
            ], total
```

- [ ] **Step 6: Update `get_by_id` to include `category_splits`**

In `get_by_id`, add a third SQL query after the existing `cat_rows` query to fetch splits:

```python
                # Fetch category splits (manual multi-category allocation)
                cur.execute(
                    """
                    SELECT s.id, s.category_id, c.name AS category_name, s.amount
                    FROM bank_transaction_category_splits s
                    JOIN categories c ON c.id = s.category_id
                    WHERE s.bank_transaction_id = %s
                    ORDER BY s.id
                    """,
                    (transaction_id,),
                )
                split_rows = cur.fetchall()
```

Then build `category_splits` and pass it to `BankTransactionDetail`. Add the import at the top of the method's data:

```python
            from ..data import BankTransactionSplit  # already imported via module-level
```

Actually `BankTransactionSplit` must be added to the imports at the top of `bank_transactions.py`:

```python
from ..data import BankTransactionListItem, BankTransactionDetail, ReceiptCategory, BankTransactionSplit
```

Then build and return:

```python
            category_splits = (
                [
                    BankTransactionSplit(
                        id=sr[0],
                        category_id=sr[1],
                        category_name=sr[2],
                        amount=float(sr[3]),
                    )
                    for sr in split_rows
                ]
                if split_rows
                else None
            )
            return BankTransactionDetail(
                # ... all existing fields unchanged ...
                category_splits=category_splits,
            )
```

- [ ] **Step 7: Run full unit test suite**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/ -v
```

Expected: all tests PASS (including the previously passing ones).

- [ ] **Step 8: Commit**

```bash
git add backend/src/repositories/bank_transactions.py \
        backend/tests/unit/test_bank_transactions_repository_splits.py
git commit -m "feat: update BankTransactionsRepository for category splits"
```

---

## Task 5: Wire App and Update Conftest

**Files:**
- Modify: `backend/src/app.py`
- Modify: `backend/tests/unit/conftest.py`

- [ ] **Step 1: Add import and parameter to `app.py`**

In `backend/src/app.py`, add the repository import near the other repository imports (around line 25):

```python
from .repositories.bank_transaction_splits import BankTransactionSplitsRepository
```

Add `bank_transaction_splits_repository=None` to `App.__init__` signature, immediately after `bank_receipt_links_repository=None`:

```python
        bank_receipt_links_repository=None,
        bank_transaction_splits_repository=None,   # ← add this line
        cash_transactions_repository=None,
```

In the `__init__` body, instantiate it after `self.bank_receipt_links_repository = ...`:

```python
        self.bank_transaction_splits_repository = (
            bank_transaction_splits_repository
            or BankTransactionSplitsRepository(self.eye_budget_db_context)
        )
```

- [ ] **Step 2: Add two new App methods**

In `backend/src/app.py`, add these two methods near `update_bank_transaction_category` (around line 1003). Also add the import at the top of the file if not already present:
```python
from .data import UpdateBankTransactionSplitsRequest  # already imported via data module
```

```python
    def upsert_bank_transaction_splits(
        self, tx_id: int, request: UpdateBankTransactionSplitsRequest
    ) -> BankTransactionDetail | None:
        tx = self.bank_transactions_repository.get_by_id(tx_id)
        if tx is None:
            return None
        self.bank_transaction_splits_repository.upsert_splits(tx_id, request.splits)
        return self.get_bank_transaction_by_id(tx_id)

    def delete_bank_transaction_splits(self, tx_id: int) -> BankTransactionDetail | None:
        tx = self.bank_transactions_repository.get_by_id(tx_id)
        if tx is None:
            return None
        self.bank_transaction_splits_repository.delete_splits(tx_id)
        return self.get_bank_transaction_by_id(tx_id)
```

- [ ] **Step 3: Add dispose call**

In `app.py`'s `dispose()` method, add after `self.bank_receipt_links_repository.dispose()`:

```python
        self.bank_transaction_splits_repository.dispose()
```

- [ ] **Step 4: Update `ALL_PARAMS` in conftest**

In `backend/tests/unit/conftest.py`, add `"bank_transaction_splits_repository"` to `ALL_PARAMS`, after `"bank_receipt_links_repository"`:

```python
    "bank_transactions_repository",
    "bank_receipt_links_repository",
    "bank_transaction_splits_repository",   # ← add this line
    "cash_transactions_repository",
```

- [ ] **Step 5: Verify unit tests still pass**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/unit/ -v
```

Expected: all unit tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/app.py backend/tests/unit/conftest.py
git commit -m "feat: wire BankTransactionSplitsRepository into App"
```

---

## Task 6: Backend Routes and Integration Tests

**Files:**
- Modify: `backend/src/main.py`
- Create: `backend/tests/integration/test_bank_transaction_splits_routes.py`

- [ ] **Step 1: Write the failing integration tests**

Create `backend/tests/integration/test_bank_transaction_splits_routes.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail before implementation**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/integration/test_bank_transaction_splits_routes.py -v -m integration
```

Expected: tests that import from `src.main` fail because the routes don't exist yet.

- [ ] **Step 3: Add routes to `main.py`**

In `backend/src/main.py`, add the following imports at the top (with existing imports):

```python
from .data import (
    # ... existing imports ...
    UpdateBankTransactionSplitsRequest,
)
```

Also add `Decimal` to the Python standard library imports:
```python
from decimal import Decimal
```

Then add the two routes in the `# --- Bank Transactions ---` section (after the existing bank transaction routes):

```python
# --- Bank Transaction Splits ---

@app.put("/bank-transactions/{tx_id}/splits", response_model=BankTransactionDetail)
async def put_bank_transaction_splits(
    tx_id: int, request: UpdateBankTransactionSplitsRequest
):
    app_instance = App()
    try:
        tx = app_instance.bank_transactions_repository.get_by_id(tx_id)
        if tx is None:
            raise HTTPException(status_code=404, detail="Transakcja nie istnieje")
        if len(request.splits) < 2:
            raise HTTPException(
                status_code=409,
                detail="Podział wymaga co najmniej 2 kategorii",
            )
        tx_amount = round(Decimal(str(tx.amount)), 2)
        splits_sum = round(sum(Decimal(str(s.amount)) for s in request.splits), 2)
        if splits_sum != tx_amount:
            raise HTTPException(
                status_code=409,
                detail=f"Suma podziału ({splits_sum}) nie jest równa kwocie transakcji ({tx_amount})",
            )
        valid_ids = {c.id for c in app_instance.categories_repository.get_all_expense_categories()}
        for s in request.splits:
            if s.category_id not in valid_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Kategoria {s.category_id} nie istnieje",
                )
        result = app_instance.upsert_bank_transaction_splits(tx_id, request)
        if result is None:
            raise HTTPException(status_code=404, detail="Transakcja nie istnieje")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        app_instance.dispose()


@app.delete("/bank-transactions/{tx_id}/splits", response_model=BankTransactionDetail)
async def delete_bank_transaction_splits(tx_id: int):
    app_instance = App()
    try:
        result = app_instance.delete_bank_transaction_splits(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Transakcja nie istnieje")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        app_instance.dispose()
```

- [ ] **Step 4: Run integration tests**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest tests/integration/test_bank_transaction_splits_routes.py -v -m integration
```

Expected: all 6 integration tests PASS.

- [ ] **Step 5: Run full backend test suite**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest -v
```

Expected: all unit + integration tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main.py \
        backend/tests/integration/test_bank_transaction_splits_routes.py
git commit -m "feat: add PUT/DELETE /bank-transactions/{id}/splits routes with integration tests"
```

---

## Task 7: Frontend Types

**Files:**
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Add `BankTransactionSplitSchema` and extend existing schemas**

In `frontend/lib/types.ts`:

1. Add the new schema (place it near `CategoryCandidateSchema`):

```typescript
export const BankTransactionSplitSchema = z.object({
  id: z.number(),
  category_id: z.number(),
  category_name: z.string(),
  amount: z.number(),
});
export type BankTransactionSplit = z.infer<typeof BankTransactionSplitSchema>;
```

2. Extend `BankTransactionListItemSchema` — add two fields at the end of the object:

```typescript
  split_category_name: z.string().nullable().optional(),
  split_count: z.number().nullable().optional(),
```

3. Extend `BankTransactionDetailSchema` — add one field at the end of the object:

```typescript
  category_splits: z.array(BankTransactionSplitSchema).nullable().optional(),
```

- [ ] **Step 2: TypeScript check**

```bash
cd /home/pawel/eye-budget/frontend
npx tsc --noEmit
```

Expected: zero TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: add BankTransactionSplitSchema and extend list/detail schemas"
```

---

## Task 8: Frontend API Functions and Proxy Route

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/api/bank-transactions/[id]/splits/route.ts`

- [ ] **Step 1: Add API functions to `api.ts`**

In `frontend/lib/api.ts`, import the new type and add two functions near `saveBankTransactionCategory`:

```typescript
import { BankTransactionDetail } from "@/lib/types";
// (BankTransactionDetail is already imported — just verify it's there)
```

Add the two functions:

```typescript
export async function saveBankTransactionSplits(
  id: number,
  splits: { category_id: number; amount: number }[]
): Promise<BankTransactionDetail> {
  return apiFetch(
    `/api/bank-transactions/${id}/splits`,
    BankTransactionDetailSchema,
    { method: "PUT", body: JSON.stringify({ splits }) }
  );
}

export async function deleteBankTransactionSplits(
  id: number
): Promise<BankTransactionDetail> {
  return apiFetch(
    `/api/bank-transactions/${id}/splits`,
    BankTransactionDetailSchema,
    { method: "DELETE" }
  );
}
```

- [ ] **Step 2: Create the Next.js proxy route**

Create `frontend/app/api/bank-transactions/[id]/splits/route.ts`:

```typescript
import { proxyPut, proxyDelete } from "@/lib/proxy";

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/bank-transactions/${params.id}/splits`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/bank-transactions/${params.id}/splits`);
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd /home/pawel/eye-budget/frontend
npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts \
        frontend/app/api/bank-transactions/[id]/splits/route.ts
git commit -m "feat: add saveBankTransactionSplits/deleteBankTransactionSplits API + proxy route"
```

---

## Task 9: BankTransactionSplitEditor Component

**Files:**
- Create: `frontend/components/BankTransactionSplitEditor.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/components/BankTransactionSplitEditor.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveBankTransactionSplits, deleteBankTransactionSplits } from "@/lib/api";
import { BankTransactionSplit } from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { Button } from "@/components/ui";

interface SplitRow {
  category_id: number | undefined;
  amount: string;
}

interface Props {
  transactionId: number;
  transactionAmount: number;
  splits: BankTransactionSplit[] | null | undefined;
  onSaved: () => void;
}

export function BankTransactionSplitEditor({
  transactionId,
  transactionAmount,
  splits,
  onSaved,
}: Props) {
  const hasSplits = splits != null && splits.length >= 2;
  const [isEditing, setIsEditing] = useState(hasSplits);
  const [rows, setRows] = useState<SplitRow[]>(
    hasSplits
      ? splits.map((s) => ({ category_id: s.category_id, amount: String(s.amount) }))
      : []
  );

  const splitSum = rows.reduce((acc, r) => acc + (parseFloat(r.amount) || 0), 0);
  const isValid =
    rows.length >= 2 &&
    rows.every((r) => r.category_id != null && r.amount.trim() !== "") &&
    Math.abs(splitSum - transactionAmount) < 0.01;

  const saveMutation = useMutation({
    mutationFn: () =>
      saveBankTransactionSplits(
        transactionId,
        rows.map((r) => ({ category_id: r.category_id!, amount: parseFloat(r.amount) }))
      ),
    onSuccess: () => onSaved(),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteBankTransactionSplits(transactionId),
    onSuccess: () => {
      setIsEditing(false);
      setRows([]);
      onSaved();
    },
  });

  const sumColor =
    rows.length === 0 || Math.abs(splitSum - transactionAmount) < 0.01
      ? "text-green-600"
      : "text-red-500";

  if (!isEditing) {
    return (
      <button
        type="button"
        onClick={() => {
          setRows([
            { category_id: undefined, amount: "" },
            { category_id: undefined, amount: "" },
          ]);
          setIsEditing(true);
        }}
        className="text-xs text-accent hover:text-accent-hover mt-1"
      >
        + Podziel na kategorie
      </button>
    );
  }

  return (
    <div className="space-y-2 mt-2">
      <p className="text-xs font-medium text-gray-700">Podział na kategorie:</p>

      {rows.map((row, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <div className="flex-1">
            <CategoryDropdown
              value={row.category_id}
              onChange={(id) =>
                setRows((prev) =>
                  prev.map((r, i) => (i === idx ? { ...r, category_id: id } : r))
                )
              }
            />
          </div>
          <input
            type="number"
            step="0.01"
            min="0"
            value={row.amount}
            onChange={(e) =>
              setRows((prev) =>
                prev.map((r, i) => (i === idx ? { ...r, amount: e.target.value } : r))
              )
            }
            className="w-24 text-sm border border-gray-200 rounded-md px-2 py-1
              focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="0.00"
          />
          {rows.length > 2 && (
            <button
              type="button"
              onClick={() => setRows((prev) => prev.filter((_, i) => i !== idx))}
              className="text-gray-400 hover:text-red-500 text-sm font-medium"
            >
              ×
            </button>
          )}
        </div>
      ))}

      <button
        type="button"
        onClick={() => setRows((prev) => [...prev, { category_id: undefined, amount: "" }])}
        className="text-xs text-accent hover:text-accent-hover"
      >
        + Dodaj kategorię
      </button>

      <p className={`text-xs ${sumColor}`}>
        Suma: {splitSum.toFixed(2)} / {transactionAmount.toFixed(2)} PLN
        {Math.abs(splitSum - transactionAmount) < 0.01 && rows.length >= 2 ? " ✓" : ""}
      </p>

      <div className="flex gap-2 flex-wrap">
        <Button
          variant="primary"
          size="sm"
          disabled={!isValid || saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          {saveMutation.isPending ? "Zapisywanie…" : "Zapisz podział"}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            if (hasSplits) {
              setRows(
                splits.map((s) => ({ category_id: s.category_id, amount: String(s.amount) }))
              );
            } else {
              setIsEditing(false);
              setRows([]);
            }
          }}
        >
          Anuluj
        </Button>
      </div>

      {hasSplits && (
        <button
          type="button"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          className="text-xs text-gray-400 hover:text-red-500"
        >
          {deleteMutation.isPending ? "Usuwanie…" : "Wróć do jednej kategorii"}
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /home/pawel/eye-budget/frontend
npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/BankTransactionSplitEditor.tsx
git commit -m "feat: add BankTransactionSplitEditor component"
```

---

## Task 10: List Page — Category Column and Expanded Row

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx`

- [ ] **Step 1: Update category column accessor**

In `frontend/app/bank-transactions/page.tsx`, find the category column accessor (around line 513). Replace the current `accessor` function with:

```typescript
      accessor: (t) => {
        if (t.receipt_category_name) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">{t.receipt_category_name}</span>
              {(t.receipt_category_count ?? 1) > 1 && (
                <span className="text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium shrink-0">
                  +{t.receipt_category_count! - 1}
                </span>
              )}
            </div>
          );
        }
        if (t.split_category_name && (t.split_count ?? 0) >= 2) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">{t.split_category_name}</span>
              <span className="text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium shrink-0">
                +{t.split_count! - 1}
              </span>
            </div>
          );
        }
        return t.category_name ? (
          <span className="text-gray-700 text-xs truncate max-w-[160px] block">
            {t.category_name}
          </span>
        ) : (
          <span className="text-gray-400 italic text-xs">Nie przypisano</span>
        );
      },
```

- [ ] **Step 2: Add import for `BankTransactionSplitEditor` and update `ExpandedRowContent`**

At the top of the file, add the import:

```typescript
import { BankTransactionSplitEditor } from "@/components/BankTransactionSplitEditor";
```

Also update the `ExpandedRowContent` query to use the typed API function. Find:

```typescript
  const { data: detail } = useQuery({
    queryKey: ["bank-transaction", tx.id],
    queryFn: () =>
      fetch(`/api/bank-transactions/${tx.id}`).then((r) => r.json()),
  });
```

Replace with:

```typescript
  const { data: detail } = useQuery({
    queryKey: ["bank-transaction", tx.id],
    queryFn: () => getBankTransaction(tx.id),
  });
```

And add `getBankTransaction` to the existing `lib/api` import at the top.

- [ ] **Step 3: Add `BankTransactionSplitEditor` in the expanded row category section**

In `ExpandedRowContent`, find the Right column section. The current structure when not receipt-linked is:

```typescript
              ) : (
                <CategoryDropdown ... />
              )}
            </div>
            {!receiptLink && (
              <div className="flex gap-2">
                <Button ... >Zapisz kategorię</Button>
              </div>
            )}
```

Replace the entire `{!receiptLink && ...}` block and the closing `</div>` of the category section with:

```typescript
              ) : (
                <>
                  {!(detail?.category_splits && detail.category_splits.length >= 2) && (
                    <CategoryDropdown
                      value={selectedCategory}
                      onChange={setSelectedCategory}
                      candidates={candidates2.map((c) => ({
                        category_id: c.category_id,
                        category_name: c.category_name,
                        category_score: c.category_score,
                      }))}
                    />
                  )}
                </>
              )}
            </div>
            {!receiptLink && !(detail?.category_splits && detail.category_splits.length >= 2) && (
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!selectedCategory || saveCategoryMutation.isPending}
                  onClick={() => saveCategoryMutation.mutate(selectedCategory ?? null)}
                  className="flex-1"
                >
                  {saveCategoryMutation.isPending ? "Zapisywanie…" : "Zapisz kategorię"}
                </Button>
              </div>
            )}
            {!receiptLink && (
              <BankTransactionSplitEditor
                key={
                  detail?.category_splits
                    ? detail.category_splits.map((s) => `${s.id}:${s.amount}`).join(",")
                    : "none"
                }
                transactionId={tx.id}
                transactionAmount={tx.amount}
                splits={detail?.category_splits ?? null}
                onSaved={() => {
                  queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
                  queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
                }}
              />
            )}
```

- [ ] **Step 4: TypeScript check and lint**

```bash
cd /home/pawel/eye-budget/frontend
npx tsc --noEmit && npm run lint
```

Expected: zero errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "feat: add split category display and BankTransactionSplitEditor to list page"
```

---

## Task 11: Detail Page — Category Card

**Files:**
- Modify: `frontend/app/bank-transactions/[id]/page.tsx`

- [ ] **Step 1: Add import for `BankTransactionSplitEditor`**

At the top of `frontend/app/bank-transactions/[id]/page.tsx`, add:

```typescript
import { BankTransactionSplitEditor } from "@/components/BankTransactionSplitEditor";
```

- [ ] **Step 2: Update the category card section**

In the file, find the category card — the `{/* Category card */}` block. It currently renders either receipt categories or the manual dropdown + AI candidates. Modify the non-receipt-linked branch to show the split editor when splits exist, and add the split editor below in all non-receipt cases.

Find the else-branch (starting with `<>` after the `receiptLink ?` check) and replace it with:

```typescript
  ) : (
    <>
      {!(tx.category_splits && tx.category_splits.length >= 2) && (
        <>
          {candidates2.length > 0 && (
            <div className="space-y-1.5 mb-3">
              <p className="text-xs text-gray-400 mb-1">Propozycje AI</p>
              {[...candidates2]
                .sort((a, b) => b.category_score - a.category_score)
                .map((c) => (
                  <CandidateBar
                    key={c.category_id}
                    name={c.category_name}
                    score={c.category_score}
                  />
                ))}
            </div>
          )}
          <div className="flex items-end gap-3">
            <div className="flex-1 max-w-sm">
              <CategoryDropdown
                value={selectedCategory}
                onChange={setSelectedCategory}
                candidates={candidates2.map((c) => ({
                  category_id: c.category_id,
                  category_name: c.category_name,
                  category_score: c.category_score,
                }))}
              />
            </div>
            <Button
              variant="primary"
              size="md"
              disabled={!selectedCategory || saveCategoryMutation.isPending}
              onClick={() =>
                selectedCategory && saveCategoryMutation.mutate(selectedCategory)
              }
            >
              {saveCategoryMutation.isPending ? "Zapisywanie…" : "Zapisz kategorię"}
            </Button>
          </div>
        </>
      )}
      <BankTransactionSplitEditor
        key={
          tx.category_splits
            ? tx.category_splits.map((s) => `${s.id}:${s.amount}`).join(",")
            : "none"
        }
        transactionId={txId}
        transactionAmount={tx.amount}
        splits={tx.category_splits ?? null}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
          queryClient.invalidateQueries({ queryKey: ["bank-transaction", txId] });
        }}
      />
    </>
  )}
```

- [ ] **Step 3: TypeScript check, lint and build**

```bash
cd /home/pawel/eye-budget/frontend
npx tsc --noEmit && npm run lint && npm run build
```

Expected: zero TypeScript errors, zero lint errors, build succeeds.

- [ ] **Step 4: Run full backend test suite one final time**

```bash
cd /home/pawel/eye-budget
source venv/bin/activate
cd backend
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/bank-transactions/[id]/page.tsx
git commit -m "feat: add BankTransactionSplitEditor to transaction detail page"
```

---

## Done

All 11 tasks complete. The feature is now fully implemented:

- Migration adds `bank_transaction_category_splits` table
- Backend enforces the single-category / split invariant everywhere
- Two new endpoints: `PUT` and `DELETE /bank-transactions/{id}/splits`
- List view shows split categories using the same `name + +N badge` pattern as receipt categories
- Both the expanded list row and the detail page support the split editor
- All new code is covered by unit and integration tests
