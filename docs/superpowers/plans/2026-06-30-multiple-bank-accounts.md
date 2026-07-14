# Multiple Bank Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CRUD management of multiple bank accounts, a Revolut CSV parser, account filtering on the bank-transactions page, and a "Konto" column in the unified transactions table.

**Architecture:** New `bank_accounts` table with FK `account_id` on `bank_transactions`. A `BankAccountsRepository` handles CRUD + stats. The import endpoint accepts `account_id` and selects `PekaoCsvParser` or `RevolutCsvParser` based on `bank_type`. The frontend adds account cards/filter on `/bank-transactions` and a new "Konto" column on `/`.

**Tech Stack:** Python 3.11 / FastAPI / psycopg2 / pydantic v2 / yoyo migrations (backend); Next.js 14 / TypeScript / TanStack Query / Zod (frontend); pytest unit+integration.

## Global Constraints

- SQL via raw psycopg2 with `%s` — no ORM.
- Pydantic v2 models in `backend/src/data.py`.
- Unit tests mock DB via `MagicMock`; integration tests use `migrated_db` + `TestClient`.
- UI text in Polish.
- FE version bump: `1.7.0` → `1.8.0` (MINOR — new feature). BE version bump: `1.8.0` → `1.9.0` (MINOR).
- `bank_type` allowed values: `'pekao'` | `'revolut'` | `'other'`. Niezmienialne po utworzeniu konta.
- Revolut reference_number: `"revolut_" + SHA256(f"{account_id}|{started_date}|{description}|{amount}")`.
- `State == REVERTED` rows in Revolut CSV are skipped (not imported).

---

## File Map

**New files (backend):**
- `backend/migrations/20260630_01_bank-accounts.sql`
- `backend/src/repositories/bank_accounts.py`
- `backend/src/services/revolut_csv_parser.py`
- `backend/tests/unit/test_bank_accounts_repository.py`
- `backend/tests/unit/test_revolut_csv_parser.py`
- `backend/tests/integration/test_bank_accounts_routes.py`

**Modified files (backend):**
- `backend/src/data.py` — add `BankAccount`, `BankAccountStats`, `CreateBankAccountRequest`, `UpdateBankAccountRequest`; update `BankTransactionListItem`, `UnifiedTransaction`
- `backend/src/repositories/bank_transactions.py` — `insert_transactions` takes `account_id`; `get_list` adds `account_id` filter
- `backend/src/repositories/unified_transactions.py` — JOIN `bank_accounts`, expose `account_id`/`account_name`
- `backend/src/app.py` — add `bank_accounts_repository`; modify `import_bank_csv`; add `get_bank_accounts`, `create_bank_account`, `update_bank_account`, `delete_bank_account`; extend `get_all_bank_transactions`
- `backend/src/main.py` — new `/bank-accounts` endpoints; modify `/bank-transactions/import`; modify `/bank-transactions` list query param
- `backend/src/version.py` — bump `1.8.0` → `1.9.0`
- `backend/tests/unit/conftest.py` — add `bank_accounts_repository` to `ALL_PARAMS`
- `backend/tests/unit/test_app_bank_transactions.py` — update 2 tests to pass `account_id`

**New files (frontend):**
- `frontend/app/api/bank-accounts/route.ts`
- `frontend/app/api/bank-accounts/[id]/route.ts`
- `frontend/components/BankAccountsModal.tsx`

**Modified files (frontend):**
- `frontend/lib/types.ts` — add `BankAccountSchema`; update `BankTransactionListItemSchema`, `UnifiedTransactionSchema`
- `frontend/lib/api.ts` — add bank accounts API functions; update `importBankCsv`
- `frontend/app/api/bank-transactions/import/route.ts` — passes `account_id` form field through
- `frontend/app/bank-transactions/page.tsx` — account cards, filter pills, updated import UI, CRUD modal
- `frontend/app/page.tsx` — add "Konto" column
- `frontend/package.json` + `frontend/package-lock.json` — bump `1.7.0` → `1.8.0`

---

## Task 1: DB Migration

**Files:**
- Create: `backend/migrations/20260630_01_bank-accounts.sql`

**Interfaces:**
- Produces: `bank_accounts` table; `bank_transactions.account_id` FK column; existing transactions assigned to "Pekao SA" account

- [ ] **Step 1: Write migration file**

```sql
-- backend/migrations/20260630_01_bank-accounts.sql

-- depends: 20260409_01_bank-transaction-category-splits

CREATE TABLE IF NOT EXISTS bank_accounts (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    bank_type  VARCHAR(50)  NOT NULL,   -- 'pekao' | 'revolut' | 'other'
    color      VARCHAR(20)  NOT NULL DEFAULT 'blue',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE bank_transactions
ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(account_id);

-- Migrate existing transactions to a default Pekao SA account
DO $$
DECLARE
    default_account_id INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM bank_transactions WHERE account_id IS NULL LIMIT 1) THEN
        INSERT INTO bank_accounts (name, bank_type, color)
        VALUES ('Pekao SA', 'pekao', 'blue')
        RETURNING id INTO default_account_id;

        UPDATE bank_transactions SET account_id = default_account_id WHERE account_id IS NULL;
    END IF;
END;
$$;
```

- [ ] **Step 2: Verify the `-- depends:` line**

Check `backend/migrations/` for the latest migration filename, confirm it's `20260409_01_bank-transaction-category-splits`. If not, update the `depends` line to the actual latest file.

```bash
ls backend/migrations/ | sort | tail -3
```

- [ ] **Step 3: Apply migration locally**

```bash
cd backend && source venv/bin/activate && yoyo apply --database postgresql://USER:PASS@HOST/DB migrations/
```

Replace `USER:PASS@HOST/DB` with values from `.env`. Expected: migration applied without errors.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/20260630_01_bank-accounts.sql
git commit -m "feat: add bank_accounts table and account_id FK on bank_transactions"
```

---

## Task 2: Backend Data Models

**Files:**
- Modify: `backend/src/data.py`

**Interfaces:**
- Produces: `BankAccount`, `BankAccountStats`, `CreateBankAccountRequest`, `UpdateBankAccountRequest` Pydantic models; updated `BankTransactionListItem`, `UnifiedTransaction` with `account_id`/`account_name` fields

- [ ] **Step 1: Add new models to `data.py`**

Find the section after `BankImportResult` (around line 407) and add:

```python
class BankAccount(BaseModel):
    """A registered bank account."""
    id: int
    name: str
    bank_type: str   # 'pekao' | 'revolut' | 'other'
    color: str


class BankAccountStats(BankAccount):
    """Bank account with aggregated transaction statistics."""
    total_income: float
    total_expense: float
    transaction_count: int


class CreateBankAccountRequest(BaseModel):
    name: str
    bank_type: str
    color: str = "blue"


class UpdateBankAccountRequest(BaseModel):
    name: str
    color: str
```

- [ ] **Step 2: Update `BankTransactionListItem`**

Add two optional fields at the end of the class (before the closing):

```python
class BankTransactionListItem(BaseModel):
    """Lightweight bank transaction for list views."""
    id: int
    reference_number: str
    booking_date: str
    counterparty: str | None = None
    description: str | None = None
    amount: float
    currency: str
    operation_type: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = []
    receipt_category_name: str | None = None
    receipt_category_count: int | None = None
    split_category_name: str | None = None
    split_count: int | None = None
    ai_top_candidate: CategoryCandidate | None = None
    settlement_group_id: int | None = None
    settlement_group_title: str | None = None
    account_id: int | None = None       # NEW
    account_name: str | None = None     # NEW
```

- [ ] **Step 3: Update `UnifiedTransaction`**

Add two optional fields at the end of the class:

```python
class UnifiedTransaction(BaseModel):
    """A single row in the unified transaction list (bank | cash | receipt)."""
    id: int
    source_type: str
    date: str
    amount: float
    description: str | None = None
    vendor_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = []
    status: str | None = None
    has_receipt: bool = False
    receipt_scan_id: int | None = None
    currency: str = "PLN"
    receipt_category_name: str | None = None
    receipt_category_count: int | None = None
    receipt_categories: list['ReceiptCategory'] | None = None
    settlement_group_id: int | None = None
    settlement_group_title: str | None = None
    account_id: int | None = None       # NEW
    account_name: str | None = None     # NEW
```

- [ ] **Step 4: Run backend tests to confirm no regressions**

```bash
cd backend && python -m pytest tests/unit/ -m unit -q
```

Expected: all existing unit tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/data.py
git commit -m "feat: add BankAccount models and account fields to BankTransactionListItem/UnifiedTransaction"
```

---

## Task 3: BankAccountsRepository (TDD)

**Files:**
- Create: `backend/src/repositories/bank_accounts.py`
- Create: `backend/tests/unit/test_bank_accounts_repository.py`

**Interfaces:**
- Consumes: `BankAccount`, `BankAccountStats`, `CreateBankAccountRequest`, `UpdateBankAccountRequest` from `data.py`
- Produces:
  - `BankAccountsRepository.list_with_stats(conn) -> list[BankAccountStats]`
  - `BankAccountsRepository.get_by_id(account_id: int) -> BankAccount | None`
  - `BankAccountsRepository.create(name, bank_type, color) -> BankAccount`
  - `BankAccountsRepository.update(account_id, name, color) -> BankAccount | None`
  - `BankAccountsRepository.delete(account_id) -> bool` (False if has transactions)
  - `BankAccountsRepository.has_transactions(account_id) -> bool`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_bank_accounts_repository.py`:

```python
import pytest
from unittest.mock import MagicMock
from src.repositories.bank_accounts import BankAccountsRepository


def make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    repo = BankAccountsRepository.__new__(BankAccountsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_list_with_stats_returns_empty_when_no_rows():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    result = repo.list_with_stats()

    # Assert
    assert result == []
    cursor.execute.assert_called_once()
    assert "bank_accounts" in cursor.execute.call_args[0][0]


@pytest.mark.unit
def test_list_with_stats_maps_row_to_model():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = [
        (1, "Pekao SA", "pekao", "blue", 500.0, -200.0, 5)
    ]

    # Act
    result = repo.list_with_stats()

    # Assert
    assert len(result) == 1
    acc = result[0]
    assert acc.id == 1
    assert acc.name == "Pekao SA"
    assert acc.bank_type == "pekao"
    assert acc.color == "blue"
    assert acc.total_income == 500.0
    assert acc.total_expense == -200.0
    assert acc.transaction_count == 5


@pytest.mark.unit
def test_get_by_id_returns_none_when_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = None

    # Act
    result = repo.get_by_id(99)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_id_returns_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1, "Pekao SA", "pekao", "blue")

    # Act
    result = repo.get_by_id(1)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.bank_type == "pekao"


@pytest.mark.unit
def test_create_returns_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (7, "Revolut", "revolut", "purple")

    # Act
    result = repo.create("Revolut", "revolut", "purple")

    # Assert
    assert result.id == 7
    assert result.name == "Revolut"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_returns_none_when_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = None

    # Act
    result = repo.update(99, "New Name", "green")

    # Assert
    assert result is None
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_returns_updated_account():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1, "Nowa Nazwa", "pekao", "green")

    # Act
    result = repo.update(1, "Nowa Nazwa", "green")

    # Assert
    assert result is not None
    assert result.name == "Nowa Nazwa"
    assert result.color == "green"


@pytest.mark.unit
def test_has_transactions_returns_true_when_count_positive():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (3,)

    # Act
    result = repo.has_transactions(1)

    # Assert
    assert result is True


@pytest.mark.unit
def test_has_transactions_returns_false_when_zero():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (0,)

    # Act
    result = repo.has_transactions(1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_returns_false_when_account_has_transactions():
    # Arrange
    repo, cursor = make_repo()
    # First call: has_transactions check
    cursor.fetchone.side_effect = [(3,)]

    # Act
    result = repo.delete(1)

    # Assert
    assert result is False
    repo.conn.commit.assert_not_called()


@pytest.mark.unit
def test_delete_returns_true_on_success():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.side_effect = [(0,)]  # has_transactions → 0

    # Act
    result = repo.delete(1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    executed = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s for s in executed)


@pytest.mark.unit
def test_create_rollback_on_error():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act / Assert — should not raise
    try:
        repo.create("Test", "pekao", "blue")
    except Exception:
        pass

    repo.conn.rollback.assert_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/unit/test_bank_accounts_repository.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.repositories.bank_accounts'`

- [ ] **Step 3: Implement `BankAccountsRepository`**

Create `backend/src/repositories/bank_accounts.py`:

```python
"""Repository for bank_accounts table."""
from __future__ import annotations

from typing import Optional

from ..data import BankAccount, BankAccountStats


class BankAccountsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def list_with_stats(self) -> list[BankAccountStats]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        ba.id, ba.name, ba.bank_type, ba.color,
                        COALESCE(SUM(CASE WHEN bt.amount > 0 THEN bt.amount ELSE 0 END), 0.0) AS total_income,
                        COALESCE(SUM(CASE WHEN bt.amount < 0 THEN bt.amount ELSE 0 END), 0.0) AS total_expense,
                        COUNT(bt.id) AS transaction_count
                    FROM bank_accounts ba
                    LEFT JOIN bank_transactions bt ON bt.account_id = ba.id
                    GROUP BY ba.id, ba.name, ba.bank_type, ba.color
                    ORDER BY ba.id
                    """
                )
                rows = cur.fetchall()
            return [
                BankAccountStats(
                    id=r[0], name=r[1], bank_type=r[2], color=r[3],
                    total_income=float(r[4]),
                    total_expense=float(r[5]),
                    transaction_count=int(r[6]),
                )
                for r in rows
            ]
        except Exception as e:
            print(f"BankAccountsRepository.list_with_stats error: {e}")
            raise

    def get_by_id(self, account_id: int) -> Optional[BankAccount]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, bank_type, color FROM bank_accounts WHERE id = %s",
                    (account_id,),
                )
                r = cur.fetchone()
            if not r:
                return None
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.get_by_id error: {e}")
            raise

    def create(self, name: str, bank_type: str, color: str) -> BankAccount:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bank_accounts (name, bank_type, color)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, bank_type, color
                    """,
                    (name, bank_type, color),
                )
                r = cur.fetchone()
            self.conn.commit()
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.create error: {e}")
            self.conn.rollback()
            raise

    def update(self, account_id: int, name: str, color: str) -> Optional[BankAccount]:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bank_accounts SET name = %s, color = %s WHERE id = %s
                    RETURNING id, name, bank_type, color
                    """,
                    (name, color, account_id),
                )
                r = cur.fetchone()
            self.conn.commit()
            if not r:
                return None
            return BankAccount(id=r[0], name=r[1], bank_type=r[2], color=r[3])
        except Exception as e:
            print(f"BankAccountsRepository.update error: {e}")
            self.conn.rollback()
            raise

    def has_transactions(self, account_id: int) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM bank_transactions WHERE account_id = %s",
                    (account_id,),
                )
                count = cur.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"BankAccountsRepository.has_transactions error: {e}")
            raise

    def delete(self, account_id: int) -> bool:
        """Delete account. Returns False if it has transactions (caller should 409)."""
        try:
            if self.has_transactions(account_id):
                return False
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM bank_accounts WHERE id = %s", (account_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"BankAccountsRepository.delete error: {e}")
            self.conn.rollback()
            raise

    def dispose(self) -> None:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/unit/test_bank_accounts_repository.py -v
```

Expected: all 12 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/repositories/bank_accounts.py backend/tests/unit/test_bank_accounts_repository.py
git commit -m "feat: add BankAccountsRepository with CRUD and stats"
```

---

## Task 4: RevolutCsvParser (TDD)

**Files:**
- Create: `backend/src/services/revolut_csv_parser.py`
- Create: `backend/tests/unit/test_revolut_csv_parser.py`

**Interfaces:**
- Produces: `RevolutCsvParser.parse_bytes(data: bytes, account_id: int) -> list[BankTransactionRow]`
- Rows with `State == "REVERTED"` are skipped.
- `reference_number = "revolut_" + SHA256(f"{account_id}|{started_date}|{description}|{amount}")`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_revolut_csv_parser.py`:

```python
import pytest
from decimal import Decimal
from src.services.revolut_csv_parser import RevolutCsvParser

SAMPLE_CSV = b"""Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
Deposit,Current,2026-01-09 14:16:48,2026-01-09 14:16:49,Payment from SOFTWARE,300.00,0.00,PLN,COMPLETED,484.21
Card Payment,Current,2026-01-12 11:01:02,2026-01-12 16:22:41,IDrive,-432.75,0.00,PLN,COMPLETED,51.46
Card Payment,Current,2026-04-13 15:24:46,,Midjourney,-44.96,0.00,PLN,REVERTED,
Card Payment,Current,2026-06-27 18:07:18,,Google Play,-9.99,0.00,PLN,PENDING,
"""


@pytest.mark.unit
def test_parse_skips_reverted_rows():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    descriptions = [r.description for r in rows]
    assert "Midjourney" not in descriptions


@pytest.mark.unit
def test_parse_includes_pending_rows():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    descriptions = [r.description for r in rows]
    assert "Google Play" in descriptions


@pytest.mark.unit
def test_parse_returns_correct_row_count():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert len(rows) == 3  # REVERTED is filtered out


@pytest.mark.unit
def test_parse_maps_amount_correctly():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    assert deposit.amount == Decimal("300.00")
    card = next(r for r in rows if r.description == "IDrive")
    assert card.amount == Decimal("-432.75")


@pytest.mark.unit
def test_parse_maps_dates_correctly():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    import datetime
    assert deposit.booking_date == datetime.date(2026, 1, 9)
    assert deposit.value_date == datetime.date(2026, 1, 9)


@pytest.mark.unit
def test_parse_value_date_none_when_completed_date_missing():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    pending = next(r for r in rows if r.description == "Google Play")
    assert pending.value_date is None


@pytest.mark.unit
def test_parse_maps_currency():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert all(r.currency == "PLN" for r in rows)


@pytest.mark.unit
def test_reference_number_starts_with_revolut():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    assert all(r.reference_number.startswith("revolut_") for r in rows)


@pytest.mark.unit
def test_reference_number_is_deterministic():
    parser = RevolutCsvParser()
    rows1 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    rows2 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    refs1 = [r.reference_number for r in rows1]
    refs2 = [r.reference_number for r in rows2]
    assert refs1 == refs2


@pytest.mark.unit
def test_reference_number_differs_by_account_id():
    parser = RevolutCsvParser()
    rows1 = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    rows2 = parser.parse_bytes(SAMPLE_CSV, account_id=2)
    assert rows1[0].reference_number != rows2[0].reference_number


@pytest.mark.unit
def test_operation_type_maps_from_type_column():
    parser = RevolutCsvParser()
    rows = parser.parse_bytes(SAMPLE_CSV, account_id=1)
    deposit = next(r for r in rows if r.description == "Payment from SOFTWARE")
    assert deposit.operation_type == "Deposit"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/unit/test_revolut_csv_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.services.revolut_csv_parser'`

- [ ] **Step 3: Implement `RevolutCsvParser`**

Create `backend/src/services/revolut_csv_parser.py`:

```python
"""
Parser for Revolut CSV exports.

Expected columns (comma-separated, English):
  Type, Product, Started Date, Completed Date, Description,
  Amount, Fee, Currency, State, Balance
"""

import csv
import io
import hashlib
import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from .bank_csv_parser import BankTransactionRow


class RevolutCsvParser:
    ENCODINGS = ("utf-8-sig", "utf-8")

    def parse_bytes(self, data: bytes, account_id: int) -> list[BankTransactionRow]:
        text = self._decode(data)
        return self._parse_text(text, account_id)

    def _decode(self, data: bytes) -> str:
        for enc in self.ENCODINGS:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")

    def _parse_text(self, text: str, account_id: int) -> list[BankTransactionRow]:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[BankTransactionRow] = []
        for raw in reader:
            row = self._parse_row(raw, account_id)
            if row is not None:
                rows.append(row)
        return rows

    def _parse_row(self, raw: dict, account_id: int) -> Optional[BankTransactionRow]:
        state = (raw.get("State") or "").strip()
        if state == "REVERTED":
            return None

        started = (raw.get("Started Date") or "").strip()
        completed = (raw.get("Completed Date") or "").strip()
        description = (raw.get("Description") or "").strip()
        amount_str = (raw.get("Amount") or "").strip()
        currency = (raw.get("Currency") or "PLN").strip()
        op_type = (raw.get("Type") or "").strip()

        try:
            amount = Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None

        booking_date = self._parse_date(started)
        if booking_date is None:
            return None

        reference_number = self._make_reference(account_id, started, description, amount_str)

        return BankTransactionRow(
            reference_number=reference_number,
            booking_date=booking_date,
            value_date=self._parse_date(completed),
            counterparty=None,
            counterparty_address=None,
            source_account=None,
            target_account=None,
            description=description or None,
            amount=amount,
            currency=currency,
            operation_type=op_type or None,
        )

    @staticmethod
    def _make_reference(account_id: int, started: str, description: str, amount: str) -> str:
        raw = f"{account_id}|{started}|{description}|{amount}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"revolut_{digest}"

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime.date]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/unit/test_revolut_csv_parser.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/revolut_csv_parser.py backend/tests/unit/test_revolut_csv_parser.py
git commit -m "feat: add RevolutCsvParser with SHA256 dedup key, REVERTED filter"
```

---

## Task 5: Update BankTransactionsRepository

**Files:**
- Modify: `backend/src/repositories/bank_transactions.py`

**Interfaces:**
- Consumes: existing `BankTransactionRow` dataclass
- Produces:
  - `insert_transactions(rows, account_id: int)` — adds `account_id` to INSERT
  - `get_list(..., account_id: Optional[int] = None)` — filters by account; returns `account_id` and `account_name` in items

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_bank_transactions_repository_account.py`:

```python
import pytest
from unittest.mock import MagicMock
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
def test_insert_transactions_includes_account_id_in_sql():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchone.return_value = (1,)  # RETURNING id
    row = MagicMock()
    row.reference_number = "REF001"
    row.booking_date = "2026-01-01"
    row.value_date = None
    row.counterparty = None
    row.counterparty_address = None
    row.source_account = None
    row.target_account = None
    row.description = "Test"
    row.amount = MagicMock(__float__=lambda s: -10.0)
    row.currency = "PLN"
    row.operation_type = None

    # Act
    repo.insert_transactions([row], account_id=3)

    # Assert — account_id must appear in the INSERT SQL and params
    sql = cursor.execute.call_args[0][0]
    params = cursor.execute.call_args[0][1]
    assert "account_id" in sql
    assert 3 in params


@pytest.mark.unit
def test_get_list_adds_account_id_filter_to_where():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    repo.get_list(account_id=2)

    # Assert
    sql = cursor.execute.call_args[0][0]
    params = cursor.execute.call_args[0][1]
    assert "account_id" in sql
    assert 2 in params


@pytest.mark.unit
def test_get_list_no_account_id_filter_omits_clause():
    # Arrange
    repo, cursor = make_repo()
    cursor.fetchall.return_value = []

    # Act
    repo.get_list()

    # Assert — account_id filter should NOT appear in params
    params = cursor.execute.call_args[0][1]
    assert 2 not in params
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/unit/test_bank_transactions_repository_account.py -v
```

Expected: tests fail because `insert_transactions` doesn't accept `account_id`.

- [ ] **Step 3: Update `insert_transactions` in `bank_transactions.py`**

Change the method signature and INSERT SQL. Find the `insert_transactions` method (around line 30) and replace:

```python
def insert_transactions(self, rows: list[BankTransactionRow], account_id: int) -> tuple[int, int]:
    """Bulk-insert parsed CSV rows.  Returns (inserted, duplicates)."""
    if not self.conn or not rows:
        return 0, 0
    inserted = 0
    duplicates = 0
    try:
        with self.conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO bank_transactions
                        (reference_number, booking_date, value_date, counterparty,
                         counterparty_address, source_account, target_account,
                         description, amount, currency, operation_type, account_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reference_number) DO NOTHING
                    RETURNING id
                    """,
                    (
                        row.reference_number,
                        row.booking_date,
                        row.value_date,
                        row.counterparty,
                        row.counterparty_address,
                        row.source_account,
                        row.target_account,
                        row.description,
                        float(row.amount),
                        row.currency,
                        row.operation_type,
                        account_id,
                    ),
                )
                result = cur.fetchone()
                if result:
                    inserted += 1
                else:
                    duplicates += 1
        self.conn.commit()
    except Exception as e:
        print(f"BankTransactionsRepository.insert_transactions error: {e}")
        self.conn.rollback()
    return inserted, duplicates
```

- [ ] **Step 4: Update `get_list` to accept `account_id` filter and expose `account_id`/`account_name`**

In the `get_list` method signature, add `account_id: Optional[int] = None`. In the conditions block (after the `tag` condition), add:

```python
if account_id is not None:
    conditions.append("bt.account_id = %s")
    params.append(account_id)
```

In the SELECT, add `bt.account_id, ba.name AS account_name` after `bt.category_candidates`:

The full SELECT becomes (replace existing):
```sql
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
       sgm.group_id,
       sg.title AS settlement_group_title,
       bt.category_candidates,
       bt.account_id,
       ba.name AS account_name,
       COUNT(*) OVER () AS total_count
FROM bank_transactions bt
LEFT JOIN categories c ON c.id = bt.category_id
LEFT JOIN settlement_group_members sgm ON sgm.bank_transaction_id = bt.id
LEFT JOIN settlement_groups sg ON sg.id = sgm.group_id
LEFT JOIN bank_accounts ba ON ba.id = bt.account_id
{where}
ORDER BY {order_clause}
LIMIT %s OFFSET %s
```

Update the result mapping. The new column positions are:
- r[0]–r[17]: unchanged (id through category_candidates)
- r[18]: account_id (NEW)
- r[19]: account_name (NEW)
- r[20]: total_count (was r[18])

Update `total` extraction and add the two new fields to `BankTransactionListItem`:

```python
total = int(rows[0][20]) if rows else 0
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
        settlement_group_id=(int(r[15]) if r[15] is not None else None),
        settlement_group_title=r[16],
        ai_top_candidate=(
            CategoryCandidate(**raw_top)
            if (raw_top := top_category_candidate_from_stored_json(r[17]))
            else None
        ),
        account_id=r[18],
        account_name=r[19],
    )
    for r in rows
], total
```

- [ ] **Step 5: Run all repository tests**

```bash
cd backend && python -m pytest tests/unit/test_bank_transactions_repository_account.py tests/unit/test_bank_transactions_repository_splits.py tests/unit/test_bank_transactions_repository_recategorization.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/repositories/bank_transactions.py backend/tests/unit/test_bank_transactions_repository_account.py
git commit -m "feat: add account_id to bank_transactions insert and get_list filter"
```

---

## Task 6: Update UnifiedTransactionsRepository

**Files:**
- Modify: `backend/src/repositories/unified_transactions.py`

**Interfaces:**
- Produces: `UnifiedTransaction` rows with `account_id` and `account_name` populated for bank rows; `None` for cash and receipt rows

- [ ] **Step 1: Update the bank branch of the UNION ALL**

In the bank branch SELECT (starts with `bt.id, 'bank'::text AS source_type, ...`), add after `sg_u.title AS settlement_group_title`:

```sql
bt.account_id,
ba.name AS account_name
```

Add the JOIN after `LEFT JOIN settlement_groups sg_u ON sg_u.id = sgm_u.group_id`:

```sql
LEFT JOIN bank_accounts ba ON ba.id = bt.account_id
```

- [ ] **Step 2: Add `NULL` columns to cash and receipt branches**

In the cash branch SELECT, after `sg_uc.title AS settlement_group_title` add:

```sql
NULL::int AS account_id,
NULL::text AS account_name
```

In the receipt branch SELECT, after `NULL::text AS settlement_group_title` add:

```sql
NULL::int AS account_id,
NULL::text AS account_name
```

- [ ] **Step 3: Update the outer SELECT**

In the outer query's SELECT list, add `account_id, account_name` after `settlement_group_title`:

```sql
SELECT
    id, source_type, date, amount, description,
    vendor_name, category_id, category_name,
    tags, status, has_receipt, receipt_scan_id, currency,
    receipt_category_name, receipt_category_count,
    receipt_categories, settlement_group_id, settlement_group_title,
    account_id, account_name,
    COUNT(*) OVER () AS total_count
FROM (...)
```

- [ ] **Step 4: Update the row mapping**

New column positions (after adding account_id at [18] and account_name at [19]):
- r[18]: account_id (NEW)
- r[19]: account_name (NEW)
- r[20]: total_count (was r[18])

Update `total` and add new fields to `UnifiedTransaction` constructor:

```python
total = int(rows[0][20]) if rows else 0
return [
    UnifiedTransaction(
        id=r[0],
        source_type=r[1],
        date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
        amount=float(r[3]),
        description=r[4],
        vendor_name=r[5],
        category_id=r[6],
        category_name=r[7],
        tags=list(r[8]) if r[8] else [],
        status=r[9],
        has_receipt=bool(r[10]),
        receipt_scan_id=r[11],
        currency=r[12] or "PLN",
        receipt_category_name=r[13],
        receipt_category_count=int(r[14]) if r[14] is not None else None,
        receipt_categories=[
            ReceiptCategory(id=cat['id'], name=cat['name'], product_count=cat['product_count'])
            for cat in (r[15] or [])
        ] or None,
        settlement_group_id=(int(r[16]) if r[16] is not None else None),
        settlement_group_title=r[17],
        account_id=r[18],
        account_name=r[19],
    )
    for r in rows
], total
```

- [ ] **Step 5: Run unit tests**

```bash
cd backend && python -m pytest tests/unit/test_unified_transactions_repository.py -v
```

Expected: all existing tests pass (they mock the cursor so column count changes don't affect them unless they check column values — inspect failures if any).

- [ ] **Step 6: Commit**

```bash
git add backend/src/repositories/unified_transactions.py
git commit -m "feat: expose account_id and account_name in unified transactions query"
```

---

## Task 7: Update App + Endpoints

**Files:**
- Modify: `backend/src/app.py`
- Modify: `backend/src/main.py`
- Modify: `backend/tests/unit/conftest.py`
- Modify: `backend/tests/unit/test_app_bank_transactions.py`
- Modify: `backend/src/version.py`

**Interfaces:**
- Produces: `/bank-accounts` CRUD endpoints; modified `/bank-transactions/import` accepting `account_id`; modified `/bank-transactions` list accepting `account_id` query param

- [ ] **Step 1: Add `bank_accounts_repository` to `tests/unit/conftest.py`**

Open `backend/tests/unit/conftest.py`. In the `ALL_PARAMS` list, after `"bank_csv_parser"` add:

```python
"bank_accounts_repository",
```

- [ ] **Step 2: Update the two affected tests in `test_app_bank_transactions.py`**

`test_import_bank_csv_empty_returns_zeros` — add account mock and pass `account_id`:

```python
@pytest.mark.unit
def test_import_bank_csv_empty_returns_zeros():
    # Arrange
    app = make_app()
    app.bank_accounts_repository.get_by_id.return_value = MagicMock(bank_type='pekao')
    app.bank_csv_parser.parse_bytes.return_value = []

    # Act
    result, ids = app.import_bank_csv(b"data", account_id=1)

    # Assert
    assert result.imported == 0
    assert result.duplicates == 0
    assert result.errors == 0
    assert ids == []
```

`test_import_bank_csv_with_rows` — same additions:

```python
@pytest.mark.unit
def test_import_bank_csv_with_rows():
    # Arrange
    app = make_app()
    app.bank_accounts_repository.get_by_id.return_value = MagicMock(bank_type='pekao')
    app.bank_csv_parser.parse_bytes.return_value = [MagicMock()]
    app.bank_transactions_repository.insert_transactions.return_value = (2, 0)
    app.bank_transactions_repository.get_new_ids_for_categorization.return_value = [1, 2]
    app.bank_receipt_links_repository.find_receipt_candidates.return_value = []
    app.bank_receipt_links_repository.find_auto_match_receipt.return_value = None

    # Act
    result, ids = app.import_bank_csv(b"data", account_id=1)

    # Assert
    assert result.imported == 2
    assert result.duplicates == 0
    assert result.errors == 0
    assert result.auto_linked == 0
    assert result.needs_manual_link == 0
    assert ids == [1, 2]
```

- [ ] **Step 3: Update `App.__init__` in `app.py`**

Add `bank_accounts_repository=None` parameter and wiring. Find the `__init__` signature and add alongside other repositories:

```python
bank_accounts_repository=None,
```

Add in the body after the other repository wiring lines:

```python
from .repositories.bank_accounts import BankAccountsRepository
self.bank_accounts_repository = bank_accounts_repository or BankAccountsRepository(self.eye_budget_db_context)
```

Also add the import at the top of the file with the other repository imports:

```python
from .repositories.bank_accounts import BankAccountsRepository
```

- [ ] **Step 4: Update `import_bank_csv` in `app.py`**

Replace the existing method:

```python
def import_bank_csv(self, data: bytes, account_id: int) -> tuple[BankImportResult, list[int]]:
    """Parse a bank CSV and insert new rows. Parser is selected by account bank_type.

    Returns result + IDs pending categorization. LLM categorization is NOT run
    here — the caller should dispatch it as a background Celery task.
    """
    from .services.revolut_csv_parser import RevolutCsvParser

    account = self.bank_accounts_repository.get_by_id(account_id)
    if account is None:
        raise ValueError(f"Bank account {account_id} not found")

    if account.bank_type == "revolut":
        rows = RevolutCsvParser().parse_bytes(data, account_id)
    else:
        rows = self.bank_csv_parser.parse_bytes(data)

    if not rows:
        return BankImportResult(imported=0, duplicates=0, errors=0), []

    inserted, duplicates = self.bank_transactions_repository.insert_transactions(rows, account_id)
    new_ids = self.bank_transactions_repository.get_new_ids_for_categorization()
    auto_linked, needs_manual_link = self._auto_link_bank_transactions(new_ids)

    return BankImportResult(
        imported=inserted,
        duplicates=duplicates,
        errors=0,
        auto_linked=auto_linked,
        needs_manual_link=needs_manual_link,
    ), new_ids
```

- [ ] **Step 5: Add bank account methods to `App`**

Add after `import_bank_csv`:

```python
def get_bank_accounts(self) -> list:
    return self.bank_accounts_repository.list_with_stats()

def create_bank_account(self, name: str, bank_type: str, color: str):
    return self.bank_accounts_repository.create(name, bank_type, color)

def update_bank_account(self, account_id: int, name: str, color: str):
    return self.bank_accounts_repository.update(account_id, name, color)

def delete_bank_account(self, account_id: int) -> bool:
    return self.bank_accounts_repository.delete(account_id)
```

- [ ] **Step 6: Update `get_all_bank_transactions` in `app.py`**

Add `account_id` param:

```python
def get_all_bank_transactions(
    self, limit: int = 50, offset: int = 0,
    sort_by: str = "booking_date", sort_dir: str = "desc",
    tag: str | None = None,
    account_id: int | None = None,
) -> tuple[list[BankTransactionListItem], int]:
    return self.bank_transactions_repository.get_list(
        limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
        tag=tag, account_id=account_id,
    )
```

- [ ] **Step 7: Update `/bank-transactions` endpoint and add `/bank-accounts` endpoints in `main.py`**

**a)** Add imports at the top of `main.py`, in the `from src.data import (...)` block:

```python
BankAccount,
BankAccountStats,
CreateBankAccountRequest,
UpdateBankAccountRequest,
```

**b)** Add `account_id` query param to `list_bank_transactions` endpoint:

```python
@app.get("/bank-transactions", response_model=PaginatedResponse[BankTransactionListItem])
def list_bank_transactions(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "booking_date",
    sort_dir: str = "desc",
    tag: str | None = None,
    account_id: int | None = None,
) -> PaginatedResponse[BankTransactionListItem]:
    """List bank transactions, paginated."""
    my_app = App()
    try:
        items, total = my_app.get_all_bank_transactions(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            tag=tag, account_id=account_id,
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
    finally:
        my_app.dispose()
```

**c)** Update `/bank-transactions/import` to require `account_id`:

```python
@app.post("/bank-transactions/import", response_model=BankImportResult, status_code=201)
async def import_bank_transactions(
    file: UploadFile = File(...),
    account_id: int = Form(...),
) -> BankImportResult:
    """Import a bank CSV export. Parser selected by account bank_type (pekao/revolut)."""
    my_app = App()
    try:
        data = await file.read()
        result, new_ids = my_app.import_bank_csv(data, account_id)
        if new_ids:
            task = categorize_bank_transactions_task.delay(new_ids)
            result.task_id = task.id
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()
```

**d)** Add bank accounts endpoints (add before the bank-transactions section):

```python
# ------------------------------------------------------------------
# Bank Accounts (CRUD)
# ------------------------------------------------------------------

@app.get("/bank-accounts", response_model=list[BankAccountStats])
def list_bank_accounts() -> list[BankAccountStats]:
    """List all bank accounts with aggregated statistics."""
    my_app = App()
    try:
        return my_app.get_bank_accounts()
    finally:
        my_app.dispose()


@app.post("/bank-accounts", response_model=BankAccount, status_code=201)
def create_bank_account(request: CreateBankAccountRequest) -> BankAccount:
    """Create a new bank account."""
    my_app = App()
    try:
        return my_app.create_bank_account(request.name, request.bank_type, request.color)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()


@app.put("/bank-accounts/{account_id}", response_model=BankAccount)
def update_bank_account(account_id: int, request: UpdateBankAccountRequest) -> BankAccount:
    """Update account name and color."""
    my_app = App()
    try:
        result = my_app.update_bank_account(account_id, request.name, request.color)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank account {account_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()


@app.delete("/bank-accounts/{account_id}", status_code=204)
def delete_bank_account(account_id: int) -> None:
    """Delete account. Returns 409 if account has transactions."""
    my_app = App()
    try:
        deleted = my_app.delete_bank_account(account_id)
        if not deleted:
            raise HTTPException(
                status_code=409,
                detail="Nie można usunąć konta z transakcjami."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()
```

- [ ] **Step 8: Bump backend version**

In `backend/src/version.py`:

```python
VERSION = "1.9.0"
```

Update `backend/tests/unit/test_version.py` if it asserts an exact version (check the file). If it uses a semver pattern, no change needed.

- [ ] **Step 9: Run all unit tests**

```bash
cd backend && python -m pytest tests/unit/ -m unit -q
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add backend/src/app.py backend/src/main.py backend/src/version.py \
        backend/tests/unit/conftest.py backend/tests/unit/test_app_bank_transactions.py
git commit -m "feat: wire BankAccountsRepository into App, add /bank-accounts endpoints, update import to require account_id"
```

---

## Task 8: Integration Tests

**Files:**
- Create: `backend/tests/integration/test_bank_accounts_routes.py`

**Interfaces:**
- Consumes: running `integration_app`, `migrated_db`, `TestClient(app)`
- Tests: GET/POST/PUT/DELETE /bank-accounts; DELETE 409 guard; POST /bank-transactions/import with account_id

- [ ] **Step 1: Write integration tests**

Create `backend/tests/integration/test_bank_accounts_routes.py`:

```python
import pytest
import psycopg2
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def db_conn(migrated_db):
    pg = migrated_db
    conn = psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )
    conn.autocommit = True
    return conn


REVOLUT_CSV = b"""Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
Deposit,Current,2026-01-09 14:16:48,2026-01-09 14:16:49,Payment from ACME,300.00,0.00,PLN,COMPLETED,484.21
Card Payment,Current,2026-01-12 11:01:02,2026-01-12 16:22:41,IDrive,-432.75,0.00,PLN,COMPLETED,51.46
"""

PEKAO_CSV = (
    "Data księgowania;Data waluty;Nadawca / Odbiorca;Adres nadawcy / odbiorcy;"
    "Rachunek źródłowy;Rachunek docelowy;Tytułem;Kwota operacji;Waluta;"
    "Numer referencyjny;Typ operacji\n"
    "01.01.2026;01.01.2026;Jan Kowalski;;12345;67890;Przelew;-100,00;PLN;REF001;Przelew\n"
).encode("utf-8")


@pytest.mark.integration
def test_create_and_list_bank_account(client, integration_app, migrated_db):
    # Arrange + Act
    response = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pekao SA"
    assert data["bank_type"] == "pekao"
    assert "id" in data

    # List
    list_resp = client.get("/bank-accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["transaction_count"] == 0


@pytest.mark.integration
def test_update_bank_account(client, integration_app, migrated_db):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Old Name", "bank_type": "pekao", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.put(
        f"/bank-accounts/{account_id}",
        json={"name": "New Name", "color": "green"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["color"] == "green"


@pytest.mark.integration
def test_update_nonexistent_account_returns_404(client, integration_app, migrated_db):
    response = client.put("/bank-accounts/9999", json={"name": "X", "color": "blue"})
    assert response.status_code == 404


@pytest.mark.integration
def test_delete_empty_account(client, integration_app, migrated_db):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "To Delete", "bank_type": "other", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.delete(f"/bank-accounts/{account_id}")

    # Assert
    assert response.status_code == 204


@pytest.mark.integration
def test_delete_account_with_transactions_returns_409(client, integration_app, migrated_db):
    # Arrange — create account then import a CSV to add transactions
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Revolut", "bank_type": "revolut", "color": "purple"},
    )
    account_id = create_resp.json()["id"]

    import_resp = client.post(
        "/bank-transactions/import",
        data={"account_id": str(account_id)},
        files={"file": ("revolut.csv", REVOLUT_CSV, "text/csv")},
    )
    assert import_resp.status_code == 201

    # Act
    response = client.delete(f"/bank-accounts/{account_id}")

    # Assert
    assert response.status_code == 409


@pytest.mark.integration
def test_import_pekao_csv_with_account_id(client, integration_app, migrated_db):
    # Arrange
    create_resp = client.post(
        "/bank-accounts",
        json={"name": "Pekao SA", "bank_type": "pekao", "color": "blue"},
    )
    account_id = create_resp.json()["id"]

    # Act
    response = client.post(
        "/bank-transactions/import",
        data={"account_id": str(account_id)},
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 1

    # Verify account stats updated
    list_resp = client.get("/bank-accounts")
    accounts = list_resp.json()
    assert accounts[0]["transaction_count"] == 1


@pytest.mark.integration
def test_import_without_account_id_returns_422(client, integration_app, migrated_db):
    response = client.post(
        "/bank-transactions/import",
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_list_bank_transactions_filter_by_account(client, integration_app, migrated_db):
    # Arrange — two accounts, import into each
    acc1 = client.post("/bank-accounts", json={"name": "Pekao", "bank_type": "pekao", "color": "blue"}).json()["id"]
    acc2 = client.post("/bank-accounts", json={"name": "Revolut", "bank_type": "revolut", "color": "purple"}).json()["id"]

    client.post(
        "/bank-transactions/import",
        data={"account_id": str(acc1)},
        files={"file": ("pekao.csv", PEKAO_CSV, "text/csv")},
    )
    client.post(
        "/bank-transactions/import",
        data={"account_id": str(acc2)},
        files={"file": ("revolut.csv", REVOLUT_CSV, "text/csv")},
    )

    # Act — filter by acc1
    resp = client.get(f"/bank-transactions?account_id={acc1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert all(item["account_id"] == acc1 for item in data["items"])
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && python -m pytest tests/integration/test_bank_accounts_routes.py -m integration -v
```

Expected: all 8 tests pass.

- [ ] **Step 3: Run full test suite**

```bash
cd backend && python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_bank_accounts_routes.py
git commit -m "test: add integration tests for bank accounts CRUD and import"
```

---

## Task 9: Frontend — Types, API Layer, Proxy Routes

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/api/bank-accounts/route.ts`
- Create: `frontend/app/api/bank-accounts/[id]/route.ts`
- Modify: `frontend/app/api/bank-transactions/import/route.ts`

**Interfaces:**
- Produces: `BankAccount`, `BankAccountStats` TS types; updated `BankTransactionListItem`, `UnifiedTransaction`; `listBankAccounts`, `createBankAccount`, `updateBankAccount`, `deleteBankAccount` API functions; updated `importBankCsv(file, accountId)` signature

- [ ] **Step 1: Update `frontend/lib/types.ts`**

**a)** Add `BankAccount` and `BankAccountStats` schemas after `BankImportResultSchema`:

```typescript
export const BankAccountSchema = z.object({
  id: z.number(),
  name: z.string(),
  bank_type: z.string(),
  color: z.string(),
});
export type BankAccount = z.infer<typeof BankAccountSchema>;

export const BankAccountStatsSchema = BankAccountSchema.extend({
  total_income: z.number(),
  total_expense: z.number(),
  transaction_count: z.number(),
});
export type BankAccountStats = z.infer<typeof BankAccountStatsSchema>;
```

**b)** Add `account_id` and `account_name` to `BankTransactionListItemSchema` (after `settlement_group_title`):

```typescript
  account_id: z.number().nullable().optional(),
  account_name: z.string().nullable().optional(),
```

**c)** Add `account_id` and `account_name` to `UnifiedTransactionSchema` (after `settlement_group_title`):

```typescript
  account_id: z.number().nullable().optional(),
  account_name: z.string().nullable().optional(),
```

- [ ] **Step 2: Add bank accounts functions to `frontend/lib/api.ts`**

Add after the `listBankTransactions` function:

```typescript
// ------------------------------------------------------------------
// Bank accounts
// ------------------------------------------------------------------

export async function listBankAccounts(): Promise<BankAccountStats[]> {
  return apiFetch("/api/bank-accounts", z.array(BankAccountStatsSchema));
}

export async function createBankAccount(data: {
  name: string;
  bank_type: string;
  color: string;
}): Promise<BankAccount> {
  return apiFetch("/api/bank-accounts", BankAccountSchema, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateBankAccount(
  id: number,
  data: { name: string; color: string }
): Promise<BankAccount> {
  return apiFetch(`/api/bank-accounts/${id}`, BankAccountSchema, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteBankAccount(id: number): Promise<void> {
  const res = await fetch(`/api/bank-accounts/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}
```

Add the missing type imports at the top of api.ts (the schema imports):

```typescript
import { BankAccountSchema, BankAccountStats, BankAccountStatsSchema } from "@/lib/types";
```

(Add to the existing import from `"@/lib/types"`)

- [ ] **Step 3: Update `importBankCsv` to accept `accountId`**

```typescript
export async function importBankCsv(file: File, accountId: number): Promise<BankImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("account_id", String(accountId));
  const res = await fetch("/api/bank-transactions/import", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  const json = await res.json();
  return BankImportResultSchema.parse(json);
}
```

- [ ] **Step 4: Add `account_id` to `listBankTransactions` API function**

Find `listBankTransactions` in `api.ts` and add `account_id` to params:

```typescript
export async function listBankTransactions(
  params: {
    page?: number;
    limit?: number;
    sort_by?: string;
    sort_dir?: string;
    tag?: string;
    account_id?: number;
  } = {}
): Promise<PaginatedResponse<BankTransactionListItem>> {
```

And in the query string building (wherever it maps params to search params), add:

```typescript
if (params.account_id !== undefined) qs.set("account_id", String(params.account_id));
```

(Look at how existing params like `sort_by` are added and follow the same pattern.)

- [ ] **Step 5: Create `frontend/app/api/bank-accounts/route.ts`**

```typescript
import { proxyGet, proxyPost } from "@/lib/proxy";

export async function GET() {
  return proxyGet("/bank-accounts");
}

export async function POST(req: Request) {
  const body = await req.json();
  return proxyPost("/bank-accounts", body);
}
```

- [ ] **Step 6: Create `frontend/app/api/bank-accounts/[id]/route.ts`**

```typescript
import { proxyPut, proxyDelete } from "@/lib/proxy";

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  const body = await req.json();
  return proxyPut(`/bank-accounts/${params.id}`, body);
}

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string } }
) {
  return proxyDelete(`/bank-accounts/${params.id}`);
}
```

- [ ] **Step 7: The import proxy route needs no changes**

The existing `frontend/app/api/bank-transactions/import/route.ts` already passes the full `formData` through — the new `account_id` field is automatically forwarded as part of `FormData`.

- [ ] **Step 8: Run frontend lint and tests**

```bash
cd frontend && npm run lint && npm run test:run
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts \
        frontend/app/api/bank-accounts/route.ts \
        "frontend/app/api/bank-accounts/[id]/route.ts"
git commit -m "feat: add BankAccount types, API functions, and proxy routes"
```

---

## Task 10: BankAccountsModal Component

**Files:**
- Create: `frontend/components/BankAccountsModal.tsx`

**Interfaces:**
- Consumes: `listBankAccounts`, `createBankAccount`, `updateBankAccount`, `deleteBankAccount` from `api.ts`; `BankAccountStats` type
- Produces: `<BankAccountsModal open onClose />` — modal with list, add form, inline edit, delete with guard

- [ ] **Step 1: Create the component**

Create `frontend/components/BankAccountsModal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listBankAccounts,
  createBankAccount,
  updateBankAccount,
  deleteBankAccount,
} from "@/lib/api";
import { BankAccountStats } from "@/lib/types";
import { Button, SectionLabel } from "@/components/ui";
import { MutationErrorNotice, QueryState } from "@/components/QueryState";
import { Pencil, Trash2, X } from "lucide-react";

const BANK_TYPE_OPTIONS = [
  { value: "pekao", label: "Pekao SA" },
  { value: "revolut", label: "Revolut" },
  { value: "other", label: "Inne" },
];

const COLOR_OPTIONS = [
  { value: "blue", label: "Niebieski" },
  { value: "green", label: "Zielony" },
  { value: "purple", label: "Fioletowy" },
  { value: "orange", label: "Pomarańczowy" },
  { value: "red", label: "Czerwony" },
];

const COLOR_CLASSES: Record<string, string> = {
  blue: "bg-blue-500",
  green: "bg-green-500",
  purple: "bg-purple-500",
  orange: "bg-orange-500",
  red: "bg-red-500",
};

type EditState = { id: number; name: string; color: string } | null;

type Props = {
  open: boolean;
  onClose: () => void;
};

export function BankAccountsModal({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const [addName, setAddName] = useState("");
  const [addBankType, setAddBankType] = useState("pekao");
  const [addColor, setAddColor] = useState("blue");
  const [editState, setEditState] = useState<EditState>(null);

  const accountsQuery = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: listBankAccounts,
    enabled: open,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["bank-accounts"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createBankAccount({ name: addName, bank_type: addBankType, color: addColor }),
    onSuccess: () => {
      invalidate();
      setAddName("");
      setAddBankType("pekao");
      setAddColor("blue");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (acc: EditState) =>
      updateBankAccount(acc!.id, { name: acc!.name, color: acc!.color }),
    onSuccess: () => {
      invalidate();
      setEditState(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBankAccount,
    onSuccess: invalidate,
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Zarządzaj kontami bankowymi</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        <MutationErrorNotice mutation={createMutation} />
        <MutationErrorNotice mutation={updateMutation} />
        <MutationErrorNotice mutation={deleteMutation} />

        {/* Account list */}
        <QueryState query={accountsQuery} errorTitle="Nie udało się pobrać kont.">
          {(accounts: BankAccountStats[]) => (
            <div className="space-y-2">
              {accounts.length === 0 && (
                <p className="text-sm text-gray-400 italic">Brak kont.</p>
              )}
              {accounts.map((acc) =>
                editState?.id === acc.id ? (
                  <div key={acc.id} className="flex items-center gap-2 p-2 border rounded-lg">
                    <input
                      className="flex-1 border rounded px-2 py-1 text-sm"
                      value={editState.name}
                      onChange={(e) =>
                        setEditState({ ...editState, name: e.target.value })
                      }
                    />
                    <select
                      className="border rounded px-2 py-1 text-sm"
                      value={editState.color}
                      onChange={(e) =>
                        setEditState({ ...editState, color: e.target.value })
                      }
                    >
                      {COLOR_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={updateMutation.isPending}
                      onClick={() => updateMutation.mutate(editState)}
                    >
                      Zapisz
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setEditState(null)}
                    >
                      Anuluj
                    </Button>
                  </div>
                ) : (
                  <div
                    key={acc.id}
                    className="flex items-center gap-3 p-2 border rounded-lg"
                  >
                    <span
                      className={`w-3 h-3 rounded-full shrink-0 ${COLOR_CLASSES[acc.color] ?? "bg-gray-400"}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{acc.name}</p>
                      <p className="text-xs text-gray-400">
                        {BANK_TYPE_OPTIONS.find((o) => o.value === acc.bank_type)?.label ?? acc.bank_type}
                        {" · "}
                        {acc.transaction_count} transakcji
                      </p>
                    </div>
                    <button
                      className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700"
                      onClick={() =>
                        setEditState({ id: acc.id, name: acc.name, color: acc.color })
                      }
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      className={`p-1 rounded text-gray-400 ${
                        acc.transaction_count > 0
                          ? "opacity-40 cursor-not-allowed"
                          : "hover:bg-red-50 hover:text-red-600"
                      }`}
                      disabled={acc.transaction_count > 0 || deleteMutation.isPending}
                      title={
                        acc.transaction_count > 0
                          ? "Nie można usunąć konta z transakcjami"
                          : "Usuń konto"
                      }
                      onClick={() => deleteMutation.mutate(acc.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )
              )}
            </div>
          )}
        </QueryState>

        {/* Add account form */}
        <div className="border-t pt-4">
          <SectionLabel className="mb-2">Dodaj nowe konto</SectionLabel>
          <div className="flex flex-col gap-2">
            <input
              className="border rounded px-2 py-1.5 text-sm w-full"
              placeholder="Nazwa konta (np. Pekao SA Główne)"
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
            />
            <div className="flex gap-2">
              <select
                className="flex-1 border rounded px-2 py-1.5 text-sm"
                value={addBankType}
                onChange={(e) => setAddBankType(e.target.value)}
              >
                {BANK_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <select
                className="flex-1 border rounded px-2 py-1.5 text-sm"
                value={addColor}
                onChange={(e) => setAddColor(e.target.value)}
              >
                {COLOR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <Button
              variant="primary"
              size="sm"
              disabled={!addName.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
              className="self-end"
            >
              {createMutation.isPending ? "Dodawanie…" : "Dodaj konto"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/BankAccountsModal.tsx
git commit -m "feat: add BankAccountsModal component for CRUD management"
```

---

## Task 11: `/bank-transactions` Page Updates

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx`

**Interfaces:**
- Consumes: `listBankAccounts`, `BankAccountStats`, `BankAccountsModal`
- Produces: account summary cards at top; filter pills by account; import triggers account selection first

- [ ] **Step 1: Add imports to `bank-transactions/page.tsx`**

Add to the import block:

```typescript
import { listBankAccounts } from "@/lib/api";
import { BankAccountStats } from "@/lib/types";
import { BankAccountsModal } from "@/components/BankAccountsModal";
import { Settings } from "lucide-react";
```

- [ ] **Step 2: Add state and query in `BankTransactionsPage`**

After existing state declarations, add:

```typescript
const [selectedAccountId, setSelectedAccountId] = useState<number | undefined>(undefined);
const [showAccountsModal, setShowAccountsModal] = useState(false);
const [pendingImportAccountId, setPendingImportAccountId] = useState<number | undefined>(undefined);
const accountFileRef = useRef<HTMLInputElement>(null);

const accountsQuery = useQuery({
  queryKey: ["bank-accounts"],
  queryFn: listBankAccounts,
  staleTime: 60_000,
});
```

- [ ] **Step 3: Update `listQuery` to pass `selectedAccountId`**

```typescript
const listQuery = useQuery({
  queryKey: ["bank-transactions", page, sortBy, sortDir, selectedAccountId],
  queryFn: () =>
    listBankTransactions({
      page,
      limit: PAGE_SIZE,
      sort_by: sortBy,
      sort_dir: sortDir,
      account_id: selectedAccountId,
    }),
  staleTime: 30_000,
});
```

- [ ] **Step 4: Update import handler to require account selection**

Replace `handleFileChange` with:

```typescript
function handleImportClick(accountId: number) {
  setPendingImportAccountId(accountId);
  accountFileRef.current?.click();
}

function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file || pendingImportAccountId === undefined) return;
  setImportResult(null);
  setImportError(null);
  setProgress(null);
  setCategorizingDone(false);
  importMutation.mutate({ file, accountId: pendingImportAccountId });
  e.target.value = "";
  setPendingImportAccountId(undefined);
}
```

Update `importMutation` mutationFn:

```typescript
const importMutation = useMutation({
  mutationFn: ({ file, accountId }: { file: File; accountId: number }) =>
    importBankCsv(file, accountId),
  ...
```

- [ ] **Step 5: Add account cards and filter pills to the JSX**

In the returned JSX, add between `<PageHeader>` and `<MutationErrorNotice>` blocks:

```tsx
{/* Account summary cards */}
{accountsQuery.data && accountsQuery.data.length > 0 && (
  <div className="flex flex-wrap gap-3">
    {accountsQuery.data.map((acc: BankAccountStats) => (
      <button
        key={acc.id}
        onClick={() => {
          setSelectedAccountId(selectedAccountId === acc.id ? undefined : acc.id);
          setPage(1);
        }}
        className={`flex flex-col gap-0.5 rounded-lg border px-4 py-3 text-left transition-colors min-w-[160px] ${
          selectedAccountId === acc.id
            ? "border-blue-400 bg-blue-50"
            : "border-gray-200 bg-white hover:bg-gray-50"
        }`}
      >
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${
              {
                blue: "bg-blue-500",
                green: "bg-green-500",
                purple: "bg-purple-500",
                orange: "bg-orange-500",
                red: "bg-red-500",
              }[acc.color] ?? "bg-gray-400"
            }`}
          />
          <span className="text-sm font-semibold text-gray-800 truncate">{acc.name}</span>
        </div>
        <div className="text-xs text-green-600">+{acc.total_income.toFixed(0)} PLN</div>
        <div className="text-xs text-red-600">{acc.total_expense.toFixed(0)} PLN</div>
        <div className="text-xs text-gray-400">{acc.transaction_count} transakcji</div>
      </button>
    ))}
    {selectedAccountId !== undefined && (
      <button
        onClick={() => { setSelectedAccountId(undefined); setPage(1); }}
        className="self-start text-xs text-gray-500 hover:underline mt-1 px-2"
      >
        Pokaż wszystkie
      </button>
    )}
  </div>
)}

<BankAccountsModal
  open={showAccountsModal}
  onClose={() => {
    setShowAccountsModal(false);
    queryClient.invalidateQueries({ queryKey: ["bank-accounts"] });
  }}
/>
```

- [ ] **Step 6: Update the Import CSV button to show account dropdown**

Replace the single "Import CSV" button in `PageHeader actions` with:

```tsx
{/* Hidden file input */}
<input
  ref={accountFileRef}
  type="file"
  accept=".csv"
  className="hidden"
  onChange={handleFileChange}
/>

{/* Manage accounts button */}
<Button
  variant="secondary"
  size="md"
  onClick={() => setShowAccountsModal(true)}
>
  <Settings className="h-4 w-4 mr-2" />
  Zarządzaj kontami
</Button>

{/* Import — account selector + file picker */}
{accountsQuery.data && accountsQuery.data.length > 0 ? (
  <div className="relative group">
    <Button
      variant="primary"
      size="md"
      disabled={importMutation.isPending}
    >
      <Upload className="h-4 w-4 mr-2" />
      Import CSV
    </Button>
    <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 hidden group-hover:block min-w-[180px]">
      {accountsQuery.data.map((acc: BankAccountStats) => (
        <button
          key={acc.id}
          className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
          onClick={() => handleImportClick(acc.id)}
        >
          {acc.name}
        </button>
      ))}
    </div>
  </div>
) : (
  <Button
    variant="primary"
    size="md"
    disabled
    title="Najpierw dodaj konto bankowe"
  >
    <Upload className="h-4 w-4 mr-2" />
    Import CSV
  </Button>
)}
```

Note: the `group-hover:block` dropdown is a simple CSS approach. If `group` is not styled correctly with the existing Tailwind setup, add `group` class to the outer `div`.

- [ ] **Step 7: Remove the old `fileRef` and replace all references**

The original `const fileRef = useRef<HTMLInputElement>(null)` and its `onClick={() => fileRef.current?.click()}` should be replaced by the new `accountFileRef` and `handleImportClick`. Remove `fileRef`.

- [ ] **Step 8: Run lint**

```bash
cd frontend && npm run lint
```

Fix any TypeScript errors (unused imports, type mismatches).

- [ ] **Step 9: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "feat: add account cards, filter, and account-aware import to bank-transactions page"
```

---

## Task 12: Main Table — "Konto" Column

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `UnifiedTransaction.account_name`, `UnifiedTransaction.account_id`
- Produces: new "Konto" column visible only for `source_type === 'bank'`; empty cell for cash/receipt

- [ ] **Step 1: Add "Konto" column to the columns array in `page.tsx`**

Find the `columns` array definition (it's a `Column<UnifiedTransaction>[]` array). Add a new column between the "Typ" (source type) column and the "Data" column:

```tsx
{
  header: "Konto",
  accessor: (r) =>
    r.source_type === "bank" && r.account_name ? (
      <span className="text-xs text-gray-600 truncate max-w-[120px] block">
        {r.account_name}
      </span>
    ) : null,
  className: "whitespace-nowrap",
},
```

- [ ] **Step 2: Verify the column order**

Check that the columns array follows the order: Typ → Konto → Data → ... Adjust position as needed by reading the current column definitions.

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 4: Bump frontend version**

In `frontend/package.json`, update `"version": "1.7.0"` → `"version": "1.8.0"`.

Run `npm install` in the frontend directory to update `package-lock.json`:

```bash
cd frontend && npm install
```

- [ ] **Step 5: Run all frontend tests**

```bash
cd frontend && npm run test:run
```

Expected: all pass.

- [ ] **Step 6: Final backend test run**

```bash
cd backend && python -m pytest -q
```

Expected: all pass.

- [ ] **Step 7: Final commit**

```bash
git add frontend/app/page.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add Konto column to unified transactions table; bump FE to 1.8.0"
```

---

## Self-Review Checklist

- [x] **Migration**: `bank_accounts` table created; `account_id` FK added to `bank_transactions`; existing data migrated to "Pekao SA" default account
- [x] **RevolutCsvParser**: filters REVERTED, SHA256 dedup key, parses `YYYY-MM-DD HH:MM:SS` dates
- [x] **BankAccountsRepository**: CRUD + stats; delete guard returns False → endpoint returns 409
- [x] **insert_transactions**: now takes `account_id` param
- [x] **get_list**: optional `account_id` filter; returns `account_id`/`account_name`
- [x] **UnifiedTransaction**: bank branch gets account data; cash/receipt get `NULL`
- [x] **App**: `bank_accounts_repository` wired; `import_bank_csv(data, account_id)` updated
- [x] **main.py**: `/bank-accounts` CRUD; `/bank-transactions/import` requires `account_id`; `/bank-transactions` accepts `account_id` filter
- [x] **`tests/unit/conftest.py`**: `bank_accounts_repository` in `ALL_PARAMS`
- [x] **`test_app_bank_transactions.py`**: 2 tests updated with `account_id`
- [x] **Integration tests**: CRUD, delete guard (409), import with account_id, list filter
- [x] **Frontend types**: `BankAccount`, `BankAccountStats` schemas; `account_id`/`account_name` in list items
- [x] **Frontend api.ts**: CRUD functions; `importBankCsv(file, accountId)` updated
- [x] **Proxy routes**: `bank-accounts` GET/POST; `bank-accounts/[id]` PUT/DELETE
- [x] **BankAccountsModal**: CRUD, delete disabled with tooltip when account has transactions
- [x] **bank-transactions page**: account cards, filter, account-aware import dropdown
- [x] **Main table**: "Konto" column, empty for non-bank rows
- [x] **Versions**: FE 1.7.0 → 1.8.0; BE 1.8.0 → 1.9.0
