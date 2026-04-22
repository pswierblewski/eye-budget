# Service Layer Coverage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ~20 unit tests to bring `evaluation.py`, `bank_categorization.py`, and `ground_truth.py` from ~62–64% coverage to ~92–95% each.

**Architecture:** All tests are appended to two existing files. No new files are created. Tests follow the AAA pattern and match the style already present in each file. Existing code is never modified — only test files change.

**Tech Stack:** Python 3.11, pytest, unittest.mock (MagicMock / AsyncMock / patch)

---

## File Map

| File | Change |
|---|---|
| `backend/tests/unit/test_services_domain.py` | Add 2 new classes + 3 methods to existing class |
| `backend/tests/unit/test_services_llm.py` | Add 1 helper method + 8 methods to existing class |

---

## Task 1: EvaluationService — sync run tests

**Covers:** lines 38–84 (`run_evaluation`), 70–76 (progress callback), 56–58 (empty entries branch)

**Files:**
- Modify: `backend/tests/unit/test_services_domain.py`

- [ ] **Step 1: Add `patch` to imports**

Open `backend/tests/unit/test_services_domain.py`. The first import line is:
```python
from unittest.mock import MagicMock, AsyncMock
```
Change it to:
```python
from unittest.mock import MagicMock, AsyncMock, patch
```
Also add `EvaluationMetrics`, `EvaluationResult` to the `src.data` import block:
```python
from src.data import (
    CreateFinancialGoalRequest,
    EvaluationMetrics,
    EvaluationResult,
    GroundTruthEntry,
    ProductItem,
    TransactionModel,
    UpdateFinancialGoalRequest,
)
```

- [ ] **Step 2: Append `TestEvaluationServiceSync` class at the end of the file**

```python
@pytest.mark.unit
class TestEvaluationServiceSync:
    def _make_service(self):
        mock_eval_repo = MagicMock()
        mock_gt_repo = MagicMock()
        mock_minio = MagicMock()
        mock_preprocessing = MagicMock()
        mock_ocr = MagicMock()
        svc = EvaluationService(
            evaluations_repository=mock_eval_repo,
            ground_truth_repository=mock_gt_repo,
            minio_service=mock_minio,
            preprocessing_service=mock_preprocessing,
            ocr_service=mock_ocr,
        )
        return svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr

    def _make_entry(self, id: int = 1, filename: str = "receipt.jpg") -> GroundTruthEntry:
        return GroundTruthEntry(
            id=id,
            filename=filename,
            minio_object_key="gt/receipt.jpg",
            ground_truth=_make_transaction(vendor="Lidl", total=10.0),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )

    def test_run_evaluation_empty_entries(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, _, _, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_all.return_value = ([], 0)

        # Act
        result = svc.run_evaluation()

        # Assert
        assert result.total_files == 0
        mock_eval_repo.add_result.assert_not_called()

    def test_run_evaluation_happy_path(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 42
        mock_gt_repo.get_all.return_value = ([self._make_entry()], 1)
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.run_evaluation()

        # Assert
        assert result.total_files == 1
        assert result.successful == 1
        mock_eval_repo.add_result.assert_called_once()
        mock_eval_repo.update_run_summary.assert_called_once()

    def test_run_evaluation_with_progress_callback(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_all.return_value = ([self._make_entry()], 1)
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }
        progress_calls = []

        # Act
        with patch("os.path.exists", return_value=False):
            svc.run_evaluation(on_progress=lambda **kw: progress_calls.append(kw))

        # Assert
        assert len(progress_calls) == 1
        assert progress_calls[0]["index"] == 1
        assert progress_calls[0]["filename"] == "receipt.jpg"

    def test_run_evaluation_with_entry_ids(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_by_ids.return_value = [self._make_entry(id=5)]
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.run_evaluation(entry_ids=[5])

        # Assert
        mock_gt_repo.get_by_ids.assert_called_once_with([5])
        mock_gt_repo.get_all.assert_not_called()
        assert result.total_files == 1

    def test_evaluate_entry_happy_path(self):
        # Arrange
        svc, _, _, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc._evaluate_ground_truth_entry(self._make_entry())

        # Assert
        assert result.success is True
        assert result.filename == "receipt.jpg"
        assert result.metrics is not None

    def test_evaluate_entry_ocr_raises_returns_failure(self):
        # Arrange
        svc, _, _, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_minio.get_temp_file.return_value = "/tmp/bad.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/bad.jpg"
        mock_ocr.process_image.side_effect = Exception("OCR failed")

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc._evaluate_ground_truth_entry(self._make_entry(filename="bad.jpg"))

        # Assert
        assert result.success is False
        assert "OCR failed" in result.error_message
```

- [ ] **Step 3: Run the new tests**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_services_domain.py::TestEvaluationServiceSync -v
```

Expected: all 6 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_services_domain.py
git commit -m "test: add EvaluationService sync run tests"
```

---

## Task 2: EvaluationService — summary tests

**Covers:** lines 335–349 (`_calculate_summary` with ground truth metrics), 378–389 (no successful results branch)

**Files:**
- Modify: `backend/tests/unit/test_services_domain.py`

- [ ] **Step 1: Append `TestEvaluationServiceSummary` class at the end of the file**

```python
@pytest.mark.unit
class TestEvaluationServiceSummary:
    def _make_service(self) -> EvaluationService:
        return EvaluationService(
            evaluations_repository=MagicMock(),
            ground_truth_repository=MagicMock(),
            minio_service=MagicMock(),
            preprocessing_service=MagicMock(),
            ocr_service=MagicMock(),
        )

    def _make_successful_result(
        self,
        vendor_correct: bool = True,
        date_correct: bool = True,
        total_accuracy: float = 1.0,
        products_accuracy: float = 1.0,
    ) -> EvaluationResult:
        metrics = EvaluationMetrics(
            processing_time_ms=100,
            fields_extracted=5,
            field_completeness=1.0,
            product_count=0,
            has_vendor=True,
            has_date=True,
            has_total=True,
            products_sum=0.0,
            extracted_total=0.0,
            total_difference=0.0,
            is_consistent=True,
            vendor_correct=vendor_correct,
            date_correct=date_correct,
            total_correct=True,
            total_accuracy=total_accuracy,
            product_count_correct=True,
            products_accuracy=products_accuracy,
        )
        return EvaluationResult(
            filename="receipt.jpg",
            success=True,
            metrics=metrics,
            transaction=_make_transaction(),
        )

    def test_calculate_summary_with_ground_truth_metrics(self):
        # Arrange
        svc = self._make_service()
        results = [self._make_successful_result(vendor_correct=True, total_accuracy=0.95)]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.avg_vendor_accuracy == 1.0
        assert summary.avg_date_accuracy == 1.0
        assert summary.avg_total_accuracy == 0.95
        assert summary.avg_products_accuracy == 1.0
        assert summary.successful == 1
        assert summary.failed == 0

    def test_calculate_summary_vendor_incorrect(self):
        # Arrange
        svc = self._make_service()
        results = [self._make_successful_result(vendor_correct=False, total_accuracy=1.0)]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.avg_vendor_accuracy == 0.0

    def test_calculate_summary_no_successful_results(self):
        # Arrange
        svc = self._make_service()
        results = [
            EvaluationResult(filename="bad.jpg", success=False, error_message="OCR failed")
        ]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.successful == 0
        assert summary.failed == 1
        assert summary.avg_vendor_accuracy is None
        assert summary.avg_date_accuracy is None
        assert summary.avg_field_completeness == 0.0
        assert summary.avg_consistency_rate == 0.0
```

- [ ] **Step 2: Run the new tests**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_services_domain.py::TestEvaluationServiceSummary -v
```

Expected: all 3 tests PASS.

> **Note:** If `EvaluationMetrics` or `EvaluationResult` raise a `ValidationError`, check `src/data.py` for required fields and adjust the `_make_successful_result` helper accordingly.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_services_domain.py
git commit -m "test: add EvaluationService _calculate_summary tests"
```

---

## Task 3: GroundTruthService — `create()` and `update()` gap

**Covers:** lines 41–82 (`create()` body), line 104 (`update()` returns None when repo.update returns False)

**Files:**
- Modify: `backend/tests/unit/test_services_domain.py` — add 3 methods to `TestGroundTruthServiceExtended`

- [ ] **Step 1: Append 3 methods inside `TestGroundTruthServiceExtended`**

The class ends at the bottom of the file after `test_create_from_confirmed_receipt_failure_path`. Add inside it:

```python
    def test_create_happy_path(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = None
        mock_gt_repo.create.return_value = 7
        mock_gt_repo.get_by_id.return_value = self._make_entry(id=7, filename="new.jpg")
        svc.minio_service.get_temp_file.return_value = "/tmp/new.jpg"
        svc.preprocessing_service.preprocess_image.return_value = "/tmp/new.jpg"
        svc.ocr_service.process_image.return_value = {
            "vendor": "Biedronka", "title": "PARAGON FISKALNY",
            "products": [], "total": 0.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.create("new.jpg", b"fake image data")

        # Assert
        svc.minio_service.upload_image.assert_called_once_with(b"fake image data", pytest.approx)
        mock_gt_repo.create.assert_called_once()
        assert result.id == 7
        assert result.filename == "new.jpg"

    def test_create_raises_on_duplicate_filename(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = self._make_entry()

        # Act / Assert
        with pytest.raises(ValueError, match="already exists"):
            svc.create("receipt.jpg", b"data")

    def test_update_returns_none_when_update_fails(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = self._make_entry()
        mock_gt_repo.update.return_value = False

        # Act
        result = svc.update(1, _make_transaction())

        # Assert
        assert result is None
```

> **Note on `upload_image` assertion:** The `object_key` argument is a generated string containing a UUID prefix. Use `mock_gt_repo.create.assert_called_once()` to confirm the call happened without asserting the exact key value. Remove `pytest.approx` from the `upload_image` assert and replace with:
> ```python
> assert svc.minio_service.upload_image.call_count == 1
> upload_args = svc.minio_service.upload_image.call_args[0]
> assert upload_args[0] == b"fake image data"
> assert "new.jpg" in upload_args[1]
> ```

- [ ] **Step 2: Run the new tests**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_services_domain.py::TestGroundTruthServiceExtended::test_create_happy_path tests/unit/test_services_domain.py::TestGroundTruthServiceExtended::test_create_raises_on_duplicate_filename tests/unit/test_services_domain.py::TestGroundTruthServiceExtended::test_update_returns_none_when_update_fails -v
```

Expected: all 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_services_domain.py
git commit -m "test: add GroundTruthService.create() and update() gap tests"
```

---

## Task 4: BankCategorizationService — context method tests

**Covers:** lines 215–227 (`_build_context_section`), 238–271 (`_get_receipt_context`), 277–303 (`_get_bank_context`)

**Files:**
- Modify: `backend/tests/unit/test_services_llm.py` — add helper + 8 methods to `TestBankCategorizationServiceExtended`

- [ ] **Step 1: Add `_make_service_with_conn` helper inside `TestBankCategorizationServiceExtended`**

Inside the class (after the existing `test_assign_candidates_async_raises_when_no_tool_call` method), add:

```python
    def _make_service_with_conn(self):
        """Variant with a real mocked conn so DB-path methods are reachable."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.conn = mock_conn
        svc = BankCategorizationService(
            db_context=mock_db,
            client=MagicMock(),
            async_client=MagicMock(),
        )
        svc.categories_table = "cat_id | cat_name"
        return svc, mock_cursor
```

- [ ] **Step 2: Add `_get_receipt_context` tests**

```python
    def test_get_receipt_context_returns_formatted_lines(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.fetchall.return_value = [("Spożywcze", 5), ("Napoje", 3)]

        # Act
        result = svc._get_receipt_context("ALDI")

        # Assert
        assert "Spożywcze (5x)" in result
        assert "Napoje (3x)" in result

    def test_get_receipt_context_empty_rows_returns_empty_string(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.fetchall.return_value = []

        # Act
        result = svc._get_receipt_context("UNKNOWN")

        # Assert
        assert result == ""

    def test_get_receipt_context_db_error_returns_empty_string(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.execute.side_effect = Exception("connection error")

        # Act
        result = svc._get_receipt_context("ALDI")

        # Assert
        assert result == ""
```

- [ ] **Step 3: Add `_get_bank_context` tests**

```python
    def test_get_bank_context_returns_formatted_lines(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.fetchall.return_value = [
            ("ALDI SP. Z O.O.", "Zakupy spożywcze", 120.0, "Spożywcze")
        ]

        # Act
        result = svc._get_bank_context("ALDI")

        # Assert
        assert "ALDI SP. Z O.O." in result
        assert "Spożywcze" in result

    def test_get_bank_context_empty_rows_returns_empty_string(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.fetchall.return_value = []

        # Act
        result = svc._get_bank_context("UNKNOWN")

        # Assert
        assert result == ""

    def test_get_bank_context_db_error_returns_empty_string(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        mock_cursor.execute.side_effect = Exception("timeout")

        # Act
        result = svc._get_bank_context("ALDI")

        # Assert
        assert result == ""
```

- [ ] **Step 4: Add `_build_context_section` test**

```python
    def test_build_context_section_combines_receipt_and_bank_context(self):
        # Arrange
        svc, mock_cursor = self._make_service_with_conn()
        # First fetchall: receipt context rows; second: bank context rows
        mock_cursor.fetchall.side_effect = [
            [("Spożywcze", 3)],
            [("ALDI SP. Z O.O.", "Zakupy", 50.0, "Spożywcze")],
        ]

        # Act
        result = svc._build_context_section("ALDI SP. Z O.O. PLOCK")

        # Assert
        assert "Kontekst historyczny" in result
        assert "paragonów" in result
        assert "bankowe" in result

    def test_build_context_section_no_counterparty_returns_empty(self):
        # Arrange
        svc, _ = self._make_service_with_conn()

        # Act
        result = svc._build_context_section("")

        # Assert
        assert result == ""
```

- [ ] **Step 5: Run the new tests**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/test_services_llm.py::TestBankCategorizationServiceExtended -v
```

Expected: all tests PASS (including the 4 existing ones + the 8 new ones = 12 total).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/unit/test_services_llm.py
git commit -m "test: add BankCategorizationService context method tests"
```

---

## Task 5: Verify coverage improvement

- [ ] **Step 1: Run full unit test suite with coverage**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/ --cov=src --cov-report=term-missing -q 2>&1 | grep -E "^src/services/(evaluation|bank_categorization|ground_truth)"
```

Expected output (approximate):
```
src/services/bank_categorization.py    97     4  95.9%  ...
src/services/evaluation.py            174    12  93.1%  ...
src/services/ground_truth.py           56     3  94.6%  ...
```

- [ ] **Step 2: Check total coverage**

```bash
cd backend && ../venv/bin/python -m pytest tests/unit/ --cov=src --cov-report=term-missing -q 2>&1 | grep TOTAL
```

Expected: `TOTAL  ...  ~79–80%`

- [ ] **Step 3: Commit if not already committed per task**

All changes should already be committed per task above. Verify with:
```bash
git status
```
Expected: `nothing to commit, working tree clean`

---

## Self-Review

**Spec coverage check:**
- `run_evaluation()` sync → Task 1 ✓
- `_evaluate_ground_truth_entry()` sync → Task 1 ✓
- `on_progress` callback → Task 1 ✓
- `entry_ids` branch in sync run → Task 1 ✓
- `_calculate_summary` with ground truth metrics → Task 2 ✓
- `_calculate_summary` with no successful results → Task 2 ✓
- `GroundTruthService.create()` → Task 3 ✓
- `update()` returns None on failure → Task 3 ✓
- `_get_receipt_context` (rows / empty / error) → Task 4 ✓
- `_get_bank_context` (rows / empty / error) → Task 4 ✓
- `_build_context_section` (combined / empty counterparty) → Task 4 ✓

**Out-of-scope items not in this plan:**
- `_evaluate_ground_truth_entry_async` error path (lines 184–187) — async error path; the async happy-path test in `TestEvaluationServiceAsync` provides sufficient confidence
- `run_evaluation_async` on_progress branch (lines 145–148) — similar reasoning; low marginal value given existing async tests
