# Backend Code Coverage — Repository Unit Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand pytest coverage scope to all of `src/` and write unit tests for all 15 uncovered repository files.

**Architecture:** All tests follow the established `make_repo()` pattern — create mock `conn`+`cursor`, wire context manager, instantiate repository via `__new__()`, inject `conn` directly. ABC repositories get a minimal concrete subclass. Minimum 3 scenarios per method: happy path, no-conn guard, DB error + rollback.

**Tech Stack:** Python 3.11.7, pytest, unittest.mock, pytest-cov

---

### Task 1: Expand coverage scope in pytest.ini

**Files:**
- Modify: `backend/pytest.ini`

- [ ] **Step 1: Edit pytest.ini**

Replace:
```
addopts = --cov=src/services --cov-report=term-missing --cov-fail-under=80
```
With:
```
addopts = --cov=src --cov-report=term-missing
```

- [ ] **Step 2: Verify tests still pass**

Run: `cd backend && python -m pytest tests/unit/ -q --tb=short`
Expected: all 266 tests pass, coverage now shows all `src/` modules

- [ ] **Step 3: Commit**

```bash
git add backend/pytest.ini
git commit -m "test: expand coverage scope to all src/, remove threshold"
```

---

### Task 2: Products repository tests

**Files:**
- Create: `backend/tests/unit/test_products_repository.py`

- [ ] **Step 1: Write tests**

```python
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


@pytest.mark.unit
def test_get_all_products_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

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
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_product_by_name("Nieznany")

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


@pytest.mark.unit
def test_insert_alternative_name_conflict_returns_false():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

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
def test_get_normalized_name_by_alternative_name_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_normalized_name_by_alternative_name("UNKNOWN PRODUCT")

    # Assert
    assert result is None
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_products_repository.py -v --tb=short`
Expected: 10 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_products_repository.py
git commit -m "test: add unit tests for ProductsRepository"
```

---

### Task 3: Vendors repository tests

**Files:**
- Create: `backend/tests/unit/test_vendors_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import MagicMock
from src.data import VendorItem
from src.repositories.vendors import VendorsRepository


class ConcreteVendors(VendorsRepository):
    pass


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    if fetchall_return is not None:
        cursor.fetchall.return_value = fetchall_return
    repo = ConcreteVendors.__new__(ConcreteVendors)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_all_vendors_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[(1, "Biedronka"), (2, "Lidl")])

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], VendorItem)
    assert result[0].name == "Biedronka"


@pytest.mark.unit
def test_get_all_vendors_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_all_vendors()

    # Assert
    assert result == []


@pytest.mark.unit
def test_insert_vendor_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(5,))

    # Act
    result = repo.insert_vendor("Żabka")

    # Assert
    assert result == 5
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_insert_vendor_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_vendor("Żabka")

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_get_vendor_by_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(3,))

    # Act
    result = repo.get_vendor_by_name("Lidl")

    # Assert
    assert result == 3


@pytest.mark.unit
def test_get_vendor_by_alternative_name_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_vendor_by_alternative_name("LIDL PL")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_normalized_name_by_alternative_name_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("Lidl",))

    # Act
    result = repo.get_normalized_name_by_alternative_name("LIDL PL")

    # Assert
    assert result == "Lidl"


@pytest.mark.unit
def test_insert_alternative_name_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(10,))

    # Act
    result = repo.insert_alternative_name("LIDL PL", vendor_id=3)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_vendors_repository.py -v --tb=short`
Expected: 8 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_vendors_repository.py
git commit -m "test: add unit tests for VendorsRepository"
```

---

### Task 4: Files repository tests

**Files:**
- Create: `backend/tests/unit/test_files_repository.py`

- [ ] **Step 1: Write tests**

`FilesRepository` is an ABC with no DB — uses `os.listdir`. Tests use `tmp_path` fixture and bypass `__init__` to avoid env var dependency.

```python
import pytest
from src.repositories.files import FilesRepository


class ConcreteFiles(FilesRepository):
    pass


def make_repo(input_dir):
    repo = ConcreteFiles.__new__(ConcreteFiles)
    repo.input_dir = str(input_dir)
    repo.output_dir = str(input_dir)
    return repo


@pytest.mark.unit
def test_list_input_files_returns_files(tmp_path):
    # Arrange
    (tmp_path / "receipt.jpg").touch()
    (tmp_path / "other.pdf").touch()
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert set(result) == {"receipt.jpg", "other.pdf"}


@pytest.mark.unit
def test_list_input_files_empty_dir(tmp_path):
    # Arrange
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert result == []


@pytest.mark.unit
def test_list_input_files_excludes_directories(tmp_path):
    # Arrange
    (tmp_path / "receipt.jpg").touch()
    (tmp_path / "subdir").mkdir()
    repo = make_repo(tmp_path)

    # Act
    result = repo.list_input_files()

    # Assert
    assert result == ["receipt.jpg"]
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_files_repository.py -v --tb=short`
Expected: 3 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_files_repository.py
git commit -m "test: add unit tests for FilesRepository"
```

---

### Task 5: PromptAnalytics repository tests

**Files:**
- Create: `backend/tests/unit/test_prompt_analytics_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from src.repositories.prompt_analytics import PromptAnalyticsRepository


class ConcretePromptAnalytics(PromptAnalyticsRepository):
    pass


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcretePromptAnalytics.__new__(ConcretePromptAnalytics)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_upsert_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.upsert(
        scan_id=1,
        vendor_name="Lidl",
        category_corrections_count=2,
        product_name_corrections_count=1,
        ocr_product_count=5,
        confirmed_product_count=5,
        details={"category_corrections": []},
    )

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "prompt_analytics" in s for s in sqls)


@pytest.mark.unit
def test_upsert_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.upsert(
        scan_id=1, vendor_name=None,
        category_corrections_count=0, product_name_corrections_count=0,
        ocr_product_count=0, confirmed_product_count=0, details={},
    )

    # Assert
    assert result is False


@pytest.mark.unit
def test_upsert_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.upsert(
        scan_id=1, vendor_name=None,
        category_corrections_count=0, product_name_corrections_count=0,
        ocr_product_count=0, confirmed_product_count=0, details={},
    )

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_get_all_returns_list():
    # Arrange
    now = datetime(2026, 1, 15, 12, 0)
    repo, cursor = make_repo(fetchall_return=[
        (1, 10, "Lidl", 2, 1, 5, 5, {"category_corrections": []}, now)
    ])

    # Act
    result = repo.get_all(limit=10, offset=0)

    # Assert
    assert len(result) == 1
    assert result[0]["scan_id"] == 10
    assert result[0]["vendor_name"] == "Lidl"


@pytest.mark.unit
def test_get_all_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_all()

    # Assert
    assert result == []


@pytest.mark.unit
def test_delete_by_scan_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_by_scan_id(scan_id=5)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s for s in sqls)


@pytest.mark.unit
def test_delete_by_scan_id_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.delete_by_scan_id(scan_id=5)

    # Assert
    assert result is False
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_prompt_analytics_repository.py -v --tb=short`
Expected: 7 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_prompt_analytics_repository.py
git commit -m "test: add unit tests for PromptAnalyticsRepository"
```

---

### Task 6: ReceiptsScans repository tests

**Files:**
- Create: `backend/tests/unit/test_receipts_scans_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import MagicMock
from src.data import ReceiptsScanStatus
from src.repositories.receipts_scans import ReceiptsScansRepository


class ConcreteReceiptsScans(ReceiptsScansRepository):
    pass


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteReceiptsScans.__new__(ConcreteReceiptsScans)
    repo.conn = conn
    repo.table = "receipts_scans"
    return repo, cursor


@pytest.mark.unit
def test_add_receipt_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("receipt.jpg",))

    # Act
    result = repo.add_receipt("receipt.jpg")

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_add_receipt_already_exists_returns_false():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.add_receipt("receipt.jpg")

    # Assert
    assert result is False


@pytest.mark.unit
def test_add_receipt_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.add_receipt("receipt.jpg")

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_set_status_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_status("receipt.jpg", ReceiptsScanStatus.PROCESSING)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_set_status_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.set_status("receipt.jpg", ReceiptsScanStatus.FAILED)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_scan_id_by_filename_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.get_scan_id_by_filename("receipt.jpg")

    # Assert
    assert result == 42


@pytest.mark.unit
def test_get_scan_id_by_filename_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_scan_id_by_filename("missing.jpg")

    # Assert
    assert result is None


@pytest.mark.unit
def test_delete_scan_by_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_scan_by_id(scan_id=10)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s for s in sqls)


@pytest.mark.unit
def test_delete_scan_by_id_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.delete_scan_by_id(scan_id=10)

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_tags_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.update_tags(scan_id=1, tags=["food", "lidl"])

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_reset_for_retry_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=("receipt.jpg",))

    # Act
    result = repo.reset_for_retry(scan_id=1)

    # Assert
    assert result == "receipt.jpg"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_reset_for_retry_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.reset_for_retry(scan_id=999)

    # Assert
    assert result is None


@pytest.mark.unit
def test_set_status_done_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.set_status_done(scan_id=5)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_receipts_scans_repository.py -v --tb=short`
Expected: 13 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_receipts_scans_repository.py
git commit -m "test: add unit tests for ReceiptsScansRepository"
```

---

### Task 7: BankReceiptLinks repository tests

**Files:**
- Create: `backend/tests/unit/test_bank_receipt_links_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
import datetime
from unittest.mock import MagicMock
from src.repositories.bank_receipt_links import BankReceiptLinksRepository, ReceiptCandidate, LinkInfo


def make_repo(fetchone_return=None, fetchall_return=None, fetchmany_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.fetchmany.return_value = fetchmany_return or []
    repo = BankReceiptLinksRepository.__new__(BankReceiptLinksRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_find_receipt_candidates_returns_list():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 99.99, 3)
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result = repo.find_receipt_candidates(bank_transaction_id=5)

    # Assert
    assert len(result) == 1
    assert isinstance(result[0], ReceiptCandidate)
    assert result[0].receipt_transaction_id == 1
    assert result[0].match_score == 3
    assert result[0].total == 99.99


@pytest.mark.unit
def test_find_receipt_candidates_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.find_receipt_candidates(bank_transaction_id=5)

    # Assert
    assert result == []


@pytest.mark.unit
def test_create_link_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.create_link(bank_transaction_id=10, receipt_transaction_id=20)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_link_conflict_returns_false():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.create_link(bank_transaction_id=10, receipt_transaction_id=20)

    # Assert
    assert result is False


@pytest.mark.unit
def test_create_link_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_link(bank_transaction_id=10, receipt_transaction_id=20)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_link_by_bank_tx_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_link_by_bank_tx(bank_transaction_id=10)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("DELETE" in s for s in sqls)


@pytest.mark.unit
def test_get_link_for_bank_tx_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(10, 20))

    # Act
    result = repo.get_link_for_bank_tx(bank_transaction_id=10)

    # Assert
    assert isinstance(result, LinkInfo)
    assert result.bank_transaction_id == 10
    assert result.receipt_transaction_id == 20


@pytest.mark.unit
def test_get_link_for_bank_tx_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_link_for_bank_tx(bank_transaction_id=99)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_receipt_single_match():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 99.99, 3)
    repo, cursor = make_repo(fetchmany_return=[row])

    # Act
    result = repo.find_auto_match_receipt(bank_transaction_id=5)

    # Assert
    assert isinstance(result, ReceiptCandidate)
    assert result.receipt_transaction_id == 1


@pytest.mark.unit
def test_find_auto_match_receipt_ambiguous_returns_none():
    # Arrange
    row1 = (1, 10, "r1.jpg", "Lidl", datetime.date(2026, 1, 10), 99.99, 3)
    row2 = (2, 11, "r2.jpg", "Lidl", datetime.date(2026, 1, 11), 99.99, 2)
    repo, cursor = make_repo(fetchmany_return=[row1, row2])

    # Act
    result = repo.find_auto_match_receipt(bank_transaction_id=5)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_receipt_link_info_found():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 99.99)
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.get_receipt_link_info(bank_transaction_id=5)

    # Assert
    assert result is not None
    assert result["receipt_transaction_id"] == 1
    assert result["total"] == 99.99
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_bank_receipt_links_repository.py -v --tb=short`
Expected: 11 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_bank_receipt_links_repository.py
git commit -m "test: add unit tests for BankReceiptLinksRepository"
```

---

### Task 8: CashReceiptLinks repository tests

**Files:**
- Create: `backend/tests/unit/test_cash_receipt_links_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
import datetime
from unittest.mock import MagicMock
from src.repositories.cash_receipt_links import CashReceiptLinksRepository


def make_repo(fetchone_return=None, fetchall_return=None, fetchmany_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.fetchmany.return_value = fetchmany_return or []
    repo = CashReceiptLinksRepository.__new__(CashReceiptLinksRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_create_link_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.create_link(cash_transaction_id=5, receipt_transaction_id=10)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_link_conflict_returns_false():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.create_link(cash_transaction_id=5, receipt_transaction_id=10)

    # Assert
    assert result is False


@pytest.mark.unit
def test_create_link_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_link(cash_transaction_id=5, receipt_transaction_id=10)

    # Assert
    assert result is False


@pytest.mark.unit
def test_delete_link_by_cash_tx_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_link_by_cash_tx(cash_transaction_id=5)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_find_receipt_candidates_returns_list():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 49.99, 2)
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    result = repo.find_receipt_candidates(cash_transaction_id=3)

    # Assert
    assert len(result) == 1
    assert result[0]["receipt_transaction_id"] == 1
    assert result[0]["total"] == 49.99


@pytest.mark.unit
def test_find_receipt_candidates_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.find_receipt_candidates(cash_transaction_id=3)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_receipt_link_info_found():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 49.99)
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=5)

    # Assert
    assert result is not None
    assert result["receipt_transaction_id"] == 1
    assert result["vendor_name"] == "Lidl"


@pytest.mark.unit
def test_get_receipt_link_info_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_receipt_link_info(cash_transaction_id=99)

    # Assert
    assert result is None


@pytest.mark.unit
def test_find_auto_match_receipt_single_match():
    # Arrange
    row = (1, 10, "receipt.jpg", "Lidl", datetime.date(2026, 1, 10), 49.99, 2)
    repo, cursor = make_repo(fetchmany_return=[row])

    # Act
    result = repo.find_auto_match_receipt(cash_transaction_id=3)

    # Assert
    assert result is not None
    assert result["receipt_transaction_id"] == 1


@pytest.mark.unit
def test_get_cash_tx_id_for_scan_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(7,))

    # Act
    result = repo.get_cash_tx_id_for_scan(scan_id=1)

    # Assert
    assert result == 7
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_cash_receipt_links_repository.py -v --tb=short`
Expected: 10 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_cash_receipt_links_repository.py
git commit -m "test: add unit tests for CashReceiptLinksRepository"
```

---

### Task 9: CashTransactions repository tests

**Files:**
- Create: `backend/tests/unit/test_cash_transactions_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
import datetime
from unittest.mock import MagicMock
from src.repositories.cash_transactions import CashTransactionsRepository


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = CashTransactionsRepository.__new__(CashTransactionsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_insert_transaction_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(99,))

    # Act
    result = repo.insert_transaction(
        booking_date=datetime.date(2026, 1, 15),
        amount=-49.99,
        description="Zakupy",
    )

    # Assert
    assert result == 99
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "cash_transactions" in s for s in sqls)


@pytest.mark.unit
def test_insert_transaction_no_conn_returns_none():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.insert_transaction(
        booking_date=datetime.date(2026, 1, 15),
        amount=-49.99,
    )

    # Assert
    assert result is None


@pytest.mark.unit
def test_insert_transaction_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.insert_transaction(
        booking_date=datetime.date(2026, 1, 15),
        amount=-49.99,
    )

    # Assert
    assert result is None
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete(tx_id=5)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.delete(tx_id=5)

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_category_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.update_category(tx_id=1, category_id=3)

    # Assert
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("UPDATE" in s and "category_id" in s for s in sqls)


@pytest.mark.unit
def test_get_list_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    items, total = repo.get_list()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_list_with_results():
    # Arrange
    # Columns: id, booking_date, description, amount, currency, source,
    #          category_id, category_name, vendor_id, vendor_name, tags,
    #          receipt_category_name, receipt_category_count, total_count
    row = (
        1, datetime.date(2026, 1, 15), "Zakupy", -49.99, "PLN",
        "manual", None, None, None, None, [], None, None, 1
    )
    repo, cursor = make_repo(fetchall_return=[row])

    # Act
    items, total = repo.get_list()

    # Assert
    assert total == 1
    assert len(items) == 1
    assert items[0].id == 1
    assert items[0].amount == -49.99


@pytest.mark.unit
def test_update_tags_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.update_tags(tx_id=1, tags=["food"])

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_update_no_fields_returns_true():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.update(tx_id=1)  # no fields → early return True

    # Assert
    assert result is True
    repo.conn.commit.assert_not_called()
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_cash_transactions_repository.py -v --tb=short`
Expected: 10 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_cash_transactions_repository.py
git commit -m "test: add unit tests for CashTransactionsRepository"
```

---

### Task 10: BudgetGoals repository tests

**Files:**
- Create: `backend/tests/unit/test_budget_goals_repository.py`

- [ ] **Step 1: Write tests**

`get_all_goals` and `get_goal` use `cursor.description` to build column dicts — this must be set explicitly on the mock.

```python
import pytest
from unittest.mock import MagicMock
from src.repositories.budget_goals import BudgetGoalsRepository

_GOAL_COLUMNS = [
    ("id",), ("name",), ("target_amount",), ("target_date",),
    ("priority_rank",), ("monthly_allocation_amount",),
    ("accumulated_progress",), ("is_active",), ("created_at",), ("updated_at",),
]


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.description = _GOAL_COLUMNS
    repo = BudgetGoalsRepository.__new__(BudgetGoalsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_all_goals_returns_list():
    # Arrange
    repo, cursor = make_repo(
        fetchall_return=[(1, "Dom", 50000.0, None, 1, 500.0, 1000.0, True, None, None)]
    )

    # Act
    result = repo.get_all_goals()

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == "Dom"
    assert result[0]["target_amount"] == 50000.0


@pytest.mark.unit
def test_get_all_goals_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_all_goals()

    # Assert
    assert result == []


@pytest.mark.unit
def test_create_goal_happy_path():
    # Arrange
    row = (1, "Dom", 50000.0, None, 1, 500.0, 0.0, True, None, None)
    repo, cursor = make_repo(fetchone_return=row)

    # Act
    result = repo.create_goal(
        name="Dom",
        target_amount=50000.0,
        target_date=None,
        priority_rank=1,
        monthly_allocation=500.0,
    )

    # Assert
    assert result is not None
    assert result["name"] == "Dom"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_goal_no_conn_returns_none():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_goal("Dom", 50000.0, None, 1, 500.0)

    # Assert
    assert result is None


@pytest.mark.unit
def test_soft_delete_goal_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.soft_delete_goal(goal_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_soft_delete_goal_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.soft_delete_goal(goal_id=999)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_active_goal_allocations_total_returns_sum():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1500.0,))

    # Act
    result = repo.get_active_goal_allocations_total()

    # Assert
    assert result == 1500.0


@pytest.mark.unit
def test_advance_monthly_progress_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.advance_monthly_progress_for_all_active_goals()

    # Assert
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("UPDATE" in s and "accumulated_progress" in s for s in sqls)
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_budget_goals_repository.py -v --tb=short`
Expected: 8 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_budget_goals_repository.py
git commit -m "test: add unit tests for BudgetGoalsRepository"
```

---

### Task 11: BudgetSimulations repository tests

**Files:**
- Create: `backend/tests/unit/test_budget_simulations_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import MagicMock
from src.repositories.budget_simulations import BudgetSimulationsRepository

_SIM_ROW = (1, "Test sim", "TV", 200.0, "monthly", "2026-01-01", "pending", None, None, "2026-01-15T10:00:00")


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = BudgetSimulationsRepository.__new__(BudgetSimulationsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_create_simulation_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=_SIM_ROW)

    # Act
    result = repo.create_simulation(
        name="Test sim", expense_name="TV",
        amount=200.0, expense_type="monthly", start_date="2026-01-01"
    )

    # Assert
    assert result is not None
    assert result["name"] == "Test sim"
    assert result["expense_amount"] == 200.0
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_simulation_no_conn_returns_none():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_simulation("T", "E", 100.0, "monthly", "2026-01-01")

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_all_simulations_returns_list():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[_SIM_ROW])

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert len(result) == 1
    assert result[0]["status"] == "pending"


@pytest.mark.unit
def test_get_all_simulations_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_all_simulations()

    # Assert
    assert result == []


@pytest.mark.unit
def test_delete_simulation_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete_simulation(sim_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_simulation_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete_simulation(sim_id=999)

    # Assert
    assert result is False


@pytest.mark.unit
def test_save_recommendations_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.save_recommendations(
        insights_json=[{"text": "Cut spending"}],
        data_through_date="2026-01-31",
        months_of_data=3,
    )

    # Assert
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "budget_ai_recommendations" in s for s in sqls)


@pytest.mark.unit
def test_get_current_recommendations_no_conn_returns_none():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_current_recommendations()

    # Assert
    assert result is None


@pytest.mark.unit
def test_update_simulation_status_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    repo.update_simulation_status(sim_id=1, status="completed", result_json={"months": []})

    # Assert
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("UPDATE" in s and "budget_simulations" in s for s in sqls)
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_budget_simulations_repository.py -v --tb=short`
Expected: 9 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_budget_simulations_repository.py
git commit -m "test: add unit tests for BudgetSimulationsRepository"
```

---

### Task 12: BudgetAnalysis repository tests

**Files:**
- Create: `backend/tests/unit/test_budget_analysis_repository.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import MagicMock
from src.repositories.budget_analysis import BudgetAnalysisRepository

_CLASSIFICATION_COLUMNS = [
    ("category_id",), ("category_name",), ("classification",), ("is_user_override",),
]


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    cursor.description = _CLASSIFICATION_COLUMNS
    repo = BudgetAnalysisRepository.__new__(BudgetAnalysisRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_monthly_category_breakdown_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_monthly_category_breakdown(year=2026, month=1)

    # Assert
    assert result == []


@pytest.mark.unit
def test_get_monthly_totals_no_conn_returns_defaults():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_monthly_totals(year=2026, month=1)

    # Assert
    assert result["income_pln"] == 0.0
    assert result["expenses_pln"] == 0.0


@pytest.mark.unit
def test_get_monthly_totals_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(5000.0, 3000.0, 2800.0))

    # Act
    result = repo.get_monthly_totals(year=2026, month=1)

    # Assert
    assert result["income_pln"] == 5000.0
    assert result["expenses_pln"] == 3000.0


@pytest.mark.unit
def test_upsert_classification_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.upsert_classification(category_id=5, classification="essential", is_user_override=True)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_upsert_classification_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.upsert_classification(category_id=5, classification="essential", is_user_override=True)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_financial_focus_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1, "Oszczędzanie", "Opis", True))

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is not None
    assert result["label"] == "Oszczędzanie"


@pytest.mark.unit
def test_get_financial_focus_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_financial_focus()

    # Assert
    assert result is None


@pytest.mark.unit
def test_set_financial_focus_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(2, "Spłata długów", None, True))

    # Act
    result = repo.set_financial_focus(label="Spłata długów", description=None)

    # Assert
    assert result is not None
    assert result["label"] == "Spłata długów"
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_count_distinct_months_returns_int():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(6,))

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 6


@pytest.mark.unit
def test_count_distinct_months_no_conn_returns_zero():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.count_distinct_months()

    # Assert
    assert result == 0


@pytest.mark.unit
def test_get_all_classifications_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_all_classifications()

    # Assert
    assert result == []
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_budget_analysis_repository.py -v --tb=short`
Expected: 11 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_budget_analysis_repository.py
git commit -m "test: add unit tests for BudgetAnalysisRepository"
```

---

### Task 13: Transactions repository tests

**Files:**
- Create: `backend/tests/unit/test_transactions_repository.py`

- [ ] **Step 1: Write tests**

`TransactionsRepository` is an ABC — tests create a minimal concrete subclass.

```python
import pytest
import datetime
from unittest.mock import MagicMock
from src.data import ReceiptTransaction
from src.repositories.transactions import TransactionsRepository


class ConcreteTransactions(TransactionsRepository):
    pass


def make_repo(fetchone_side_effect=None, fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_side_effect is not None:
        cursor.fetchone.side_effect = fetchone_side_effect
    elif fetchone_return is not None:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteTransactions.__new__(ConcreteTransactions)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_lookup_vendor_id_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(5,))

    # Act
    result = repo.lookup_vendor_id("LIDL POLSKA")

    # Assert
    assert result == 5


@pytest.mark.unit
def test_lookup_vendor_id_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.lookup_vendor_id("UNKNOWN")

    # Assert
    assert result is None


@pytest.mark.unit
def test_lookup_vendor_id_no_conn_returns_none():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.lookup_vendor_id("LIDL")

    # Assert
    assert result is None


@pytest.mark.unit
def test_create_transaction_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(10,))

    # Act
    result = repo.create_transaction(
        scan_id=1, vendor_id=5, raw_vendor_name="LIDL",
        transaction_date=datetime.date(2026, 1, 15), total=99.99
    )

    # Assert
    assert result == 10
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "receipt_transactions" in s for s in sqls)


@pytest.mark.unit
def test_create_transaction_no_conn_returns_minus_one():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_transaction(
        scan_id=1, vendor_id=None, raw_vendor_name="X",
        transaction_date=datetime.date(2026, 1, 1), total=10.0
    )

    # Assert
    assert result == -1


@pytest.mark.unit
def test_get_by_scan_id_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_scan_id(scan_id=99)

    # Assert
    assert result is None


@pytest.mark.unit
def test_get_by_scan_id_found_with_items():
    # Arrange
    # tx_row: id, vendor_id, raw_vendor_name, date, total, normalized_vendor_name
    tx_row = (10, 5, "LIDL", datetime.date(2026, 1, 15), 99.99, "Lidl")
    # item_rows: id, product_id, raw_product_name, category_id, quantity, unit_price, price, normalized_product_name
    item_rows = [(1, None, "Mleko", 3, 1.0, None, 3.99, None)]
    repo, cursor = make_repo(
        fetchone_side_effect=[tx_row],
        fetchall_return=item_rows,
    )

    # Act
    result = repo.get_by_scan_id(scan_id=1)

    # Assert
    assert isinstance(result, ReceiptTransaction)
    assert result.id == 10
    assert len(result.items) == 1
    assert result.items[0].raw_product_name == "Mleko"


@pytest.mark.unit
def test_delete_transaction_item_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete_transaction_item(item_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_transaction_item_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete_transaction_item(item_id=999)

    # Assert
    assert result is False
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_by_scan_id_happy_path():
    # Arrange
    repo, cursor = make_repo()

    # Act
    result = repo.delete_by_scan_id(scan_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_transactions_repository.py -v --tb=short`
Expected: 10 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_transactions_repository.py
git commit -m "test: add unit tests for TransactionsRepository"
```

---

### Task 14: UnifiedTransactions repository tests

**Files:**
- Create: `backend/tests/unit/test_unified_transactions_repository.py`

- [ ] **Step 1: Write tests**

`get_list()` and `get_analytics()` run multi-query SQL. Tests focus on no-conn guards and shape of returned data.

```python
import pytest
from unittest.mock import MagicMock
from src.data import AnalyticsSummary
from src.repositories.unified_transactions import UnifiedTransactionsRepository


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = UnifiedTransactionsRepository.__new__(UnifiedTransactionsRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_get_list_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    items, total = repo.get_list()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_list_empty_db_returns_empty():
    # Arrange
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    items, total = repo.get_list()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_analytics_no_conn_returns_empty_summary():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.get_analytics()

    # Assert
    assert isinstance(result, AnalyticsSummary)
    assert result.total_expense == 0
    assert result.total_income == 0
    assert result.transaction_count == 0
    assert result.monthly_totals == []
    assert result.by_vendor == []
    assert result.by_category == []
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_unified_transactions_repository.py -v --tb=short`
Expected: 3 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_unified_transactions_repository.py
git commit -m "test: add unit tests for UnifiedTransactionsRepository"
```

---

### Task 15: Evaluations repository tests

**Files:**
- Create: `backend/tests/unit/test_evaluations_repository.py`

- [ ] **Step 1: Write tests**

`EvaluationsRepository` is an ABC. `update_run_summary` uses `summary.avg_field_completeness` and `summary.avg_consistency_rate` which are not standard BaseModel fields — use `MagicMock` for the summary parameter.

```python
import pytest
from unittest.mock import MagicMock
from src.data import EvaluationResult, EvaluationMetrics, TransactionModel
from src.repositories.evaluations import EvaluationsRepository


class ConcreteEvaluations(EvaluationsRepository):
    pass


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = conn
    return repo, cursor


def _make_eval_result():
    return EvaluationResult(
        filename="receipt.jpg",
        success=True,
        error_message=None,
        metrics=EvaluationMetrics(
            processing_time_ms=500,
            fields_extracted=3,
            field_completeness=1.0,
            product_count=2,
            has_vendor=True,
            has_date=True,
            has_total=True,
            products_sum=99.99,
            extracted_total=99.99,
            total_difference=0.0,
            is_consistent=True,
        ),
        transaction=TransactionModel(
            vendor="Lidl", title="PARAGON", products=[], total=99.99, date="2026-01-15"
        ),
    )


@pytest.mark.unit
def test_create_run_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))

    # Act
    result = repo.create_run(model_used="gpt-4o", config={"threshold": 0.9})

    # Assert
    assert result == 1
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "evaluation_runs" in s for s in sqls)


@pytest.mark.unit
def test_create_run_no_conn_returns_minus_one():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    result = repo.create_run(model_used="gpt-4o")

    # Assert
    assert result == -1


@pytest.mark.unit
def test_create_run_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.create_run(model_used="gpt-4o")

    # Assert
    assert result == -1
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_add_result_happy_path():
    # Arrange
    repo, cursor = make_repo()
    eval_result = _make_eval_result()

    # Act
    result = repo.add_result(run_id=1, result=eval_result)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_add_result_no_conn_returns_false():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None
    eval_result = _make_eval_result()

    # Act
    result = repo.add_result(run_id=1, result=eval_result)

    # Assert
    assert result is False


@pytest.mark.unit
def test_update_run_summary_happy_path():
    # Arrange
    repo, cursor = make_repo()
    summary = MagicMock()
    summary.total_files = 10
    summary.successful = 9
    summary.failed = 1
    summary.success_rate = 0.9
    summary.avg_processing_time_ms = 300.0
    summary.avg_field_completeness = 0.95
    summary.avg_consistency_rate = 0.98

    # Act
    result = repo.update_run_summary(run_id=1, summary=summary)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_get_all_runs_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    items, total = repo.get_all_runs()

    # Assert
    assert items == []
    assert total == 0
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_evaluations_repository.py -v --tb=short`
Expected: 7 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_evaluations_repository.py
git commit -m "test: add unit tests for EvaluationsRepository"
```

---

### Task 16: GroundTruth repository tests

**Files:**
- Create: `backend/tests/unit/test_ground_truth_repository.py`

- [ ] **Step 1: Write tests**

`GroundTruthRepository` is an ABC. `GroundTruthEntry.created_at` and `updated_at` are required `datetime.datetime` — test rows must include real datetime values.

```python
import pytest
import datetime
from unittest.mock import MagicMock
from src.data import GroundTruthEntry, TransactionModel
from src.repositories.ground_truth import GroundTruthRepository


class ConcreteGroundTruth(GroundTruthRepository):
    pass


def make_repo(fetchone_return=None, fetchall_return=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteGroundTruth.__new__(ConcreteGroundTruth)
    repo.conn = conn
    return repo, cursor


_NOW = datetime.datetime(2026, 1, 15, 12, 0)
_GT_ROW = (
    1, "receipt.jpg", "receipts/receipt.jpg",
    {"vendor": "Lidl", "title": "PARAGON", "products": [], "total": 99.99, "date": "2026-01-15"},
    _NOW, _NOW,
)


@pytest.mark.unit
def test_create_happy_path():
    # Arrange
    repo, cursor = make_repo(fetchone_return=(1,))
    gt = TransactionModel(vendor="Lidl", title="PARAGON", products=[], total=99.99, date="2026-01-15")

    # Act
    result = repo.create("receipt.jpg", "receipts/receipt.jpg", gt)

    # Assert
    assert result == 1
    repo.conn.commit.assert_called_once()
    sqls = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("INSERT" in s and "evaluation_ground_truth" in s for s in sqls)


@pytest.mark.unit
def test_create_no_conn_returns_minus_one():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None
    gt = TransactionModel(vendor="Lidl", title="PARAGON", products=[], total=99.99, date="2026-01-15")

    # Act
    result = repo.create("receipt.jpg", "key", gt)

    # Assert
    assert result == -1


@pytest.mark.unit
def test_get_by_filename_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=_GT_ROW)

    # Act
    result = repo.get_by_filename("receipt.jpg")

    # Assert
    assert isinstance(result, GroundTruthEntry)
    assert result.id == 1
    assert result.filename == "receipt.jpg"
    assert result.ground_truth.vendor == "Lidl"


@pytest.mark.unit
def test_get_by_filename_not_found():
    # Arrange
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    result = repo.get_by_filename("missing.jpg")

    # Assert
    assert result is None


@pytest.mark.unit
def test_delete_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1

    # Act
    result = repo.delete(entry_id=1)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_delete_not_found():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 0

    # Act
    result = repo.delete(entry_id=999)

    # Assert
    assert result is False


@pytest.mark.unit
def test_get_all_no_conn_returns_empty():
    # Arrange
    repo, _ = make_repo()
    repo.conn = None

    # Act
    entries, total = repo.get_all()

    # Assert
    assert entries == []
    assert total == 0


@pytest.mark.unit
def test_update_happy_path():
    # Arrange
    repo, cursor = make_repo()
    cursor.rowcount = 1
    gt = TransactionModel(vendor="Lidl", title="PARAGON", products=[], total=99.99, date="2026-01-15")

    # Act
    result = repo.update(entry_id=1, ground_truth=gt)

    # Assert
    assert result is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_get_by_ids_empty_list_returns_empty():
    # Arrange
    repo, _ = make_repo()

    # Act
    result = repo.get_by_ids([])

    # Assert
    assert result == []
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/unit/test_ground_truth_repository.py -v --tb=short`
Expected: 9 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_ground_truth_repository.py
git commit -m "test: add unit tests for GroundTruthRepository"
```

---

### Task 17: Verify full coverage improvement

- [ ] **Step 1: Run full unit test suite with coverage**

Run: `cd backend && python -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all tests pass, coverage total significantly higher than the prior 81% (services-only), `src/repositories/` lines now appear in coverage report

- [ ] **Step 2: Note baseline for future sessions**

The remaining gaps after this plan (to be addressed in future sessions):
- `src/tasks/` — Celery tasks (requires mocking Celery infrastructure)
- `src/app.py`, `src/main.py` — FastAPI routes (integration tests)
- Weak services: `evaluation.py` 62.6%, `bank_categorization.py` 61.9%, `ground_truth.py` 64.3%
- `test_coverage_boost.py` — rewrite as quality tests
