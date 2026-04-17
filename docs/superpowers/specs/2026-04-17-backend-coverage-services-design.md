# Design: Backend Code Coverage — Service Unit Tests

**Date:** 2026-04-17
**Scope:** `src/services/evaluation.py`, `src/services/bank_categorization.py`, `src/services/ground_truth.py`
**Goal:** Fill the uncovered lines in the three weakest service files by adding tests to the existing test files

---

## 1. Current State

| File | Coverage | Missing lines |
|---|---|---|
| `services/evaluation.py` | 62.6% | 38–84, 104, 145–148, 184–187, 195–236, 335–349, 378–389 |
| `services/bank_categorization.py` | 61.9% | 215–227, 238–271, 277–303 |
| `services/ground_truth.py` | 64.3% | 41–82, 104 |

Existing tests live in:
- `tests/unit/test_services_domain.py` — covers `EvaluationService.calculate_metrics`, async run, `GroundTruthService` CRUD
- `tests/unit/test_services_llm.py` — covers `BankCategorizationService.assign_candidates` (sync + async)

---

## 2. What Each Gap Is

### `evaluation.py`

| Lines | Method | What's uncovered |
|---|---|---|
| 38–84 | `run_evaluation()` | Entire sync orchestration method |
| 104 | `run_evaluation_async()` | `entry_ids is not None` branch |
| 145–148 | `run_evaluation_async()` | `on_progress` callback block |
| 184–187 | `_evaluate_ground_truth_entry_async()` | Exception path |
| 195–236 | `_evaluate_ground_truth_entry()` | Entire sync helper (happy path + error) |
| 335–349 | `_calculate_summary()` | Branch when `results_with_gt` is non-empty |
| 378–389 | `_calculate_summary()` | Branch when no successful results |

### `bank_categorization.py`

| Lines | Method | What's uncovered |
|---|---|---|
| 215–227 | `_build_context_section()` | Body when `parts` is non-empty (receipt or bank context found) |
| 238–271 | `_get_receipt_context()` | DB query, rows returned, empty result, DB error |
| 277–303 | `_get_bank_context()` | DB query, rows returned, empty result, DB error |

Note: existing `_make_service()` sets `mock_db.conn = None`, which causes `_build_context_section` to return `""` immediately — the DB paths are never reached.

### `ground_truth.py`

| Lines | Method | What's uncovered |
|---|---|---|
| 41–82 | `create()` | Full body: duplicate check, MinIO upload, OCR, DB store, temp cleanup |
| 104 | `update()` | `if not success: return None` branch |

---

## 3. Test Strategy

### Target files (additions only, no new test files)

- **`test_services_domain.py`** — new test classes `TestEvaluationServiceSync` and `TestEvaluationServiceSummary`; additions to `TestGroundTruthServiceExtended`
- **`test_services_llm.py`** — additions to `TestBankCategorizationServiceExtended`

### Mocking approach

**EvaluationService sync tests** — same `_make_service()` factory already used in `TestEvaluationServiceAsync`. For `_evaluate_ground_truth_entry()` mock the temp file path so `os.path.exists` works cleanly:

```python
mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
mock_ocr.process_image.return_value = {
    "vendor": "Lidl", "title": "PARAGON FISKALNY",
    "products": [], "total": 10.0, "date": "2024-01-01",
}
```

Use `unittest.mock.patch("os.path.exists", return_value=False)` to suppress the temp-file cleanup `os.remove` call (file doesn't exist in test env).

**BankCategorizationService context tests** — create a variant factory with a real (mocked) `conn`:

```python
def _make_service_with_conn(self):
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.conn = mock_conn
    svc = BankCategorizationService(db_context=mock_db, client=MagicMock(), async_client=MagicMock())
    svc.categories_table = "cat_id | cat_name"
    return svc, mock_cursor
```

**GroundTruthService.create()** — extend existing `TestGroundTruthServiceExtended._make_service()`. Access `mock_minio` and `mock_ocr` from the service attributes since they are injected.

---

## 4. Tests to Add

### `test_services_domain.py` — `TestEvaluationServiceSync` (new class, ~7 tests)

| Test | Covers |
|---|---|
| `test_run_evaluation_empty_entries` | Lines 56–58: empty ground truth → `_create_empty_summary` returned |
| `test_run_evaluation_happy_path` | Lines 38–84: full sync loop, `add_result` called, summary returned |
| `test_run_evaluation_with_progress_callback` | Lines 70–76: `on_progress` called once per entry |
| `test_evaluate_entry_happy_path` | Lines 195–225: sync helper success path |
| `test_evaluate_entry_ocr_raises` | Lines 225–232: exception → `EvaluationResult(success=False)` |

### `test_services_domain.py` — `TestEvaluationServiceSummary` (new class, ~3 tests)

| Test | Covers |
|---|---|
| `test_calculate_summary_with_ground_truth_metrics` | Lines 335–349: `results_with_gt` non-empty, avg accuracies computed |
| `test_calculate_summary_no_successful_results` | Lines 378–389: all failed → zero averages, `None` gt metrics |
| `test_run_evaluation_async_with_entry_ids` | Line 104: `entry_ids` passed → `get_by_ids` called instead of `get_all` |

### `test_services_domain.py` — additions to `TestGroundTruthServiceExtended` (~3 tests)

| Test | Covers |
|---|---|
| `test_create_raises_on_duplicate_filename` | Lines 41–42: `get_by_filename` returns entry → `ValueError` raised |
| `test_create_happy_path` | Lines 44–78: uploads to MinIO, runs OCR, stores in DB, returns response |
| `test_update_returns_none_when_update_fails` | Line 104: `repo.update` returns `False` → `None` returned |

### `test_services_llm.py` — additions to `TestBankCategorizationServiceExtended` (~7 tests)

| Test | Covers |
|---|---|
| `test_build_context_section_no_conn_returns_empty` | Line 212: already covered by existing tests; confirms guard |
| `test_build_context_section_with_receipt_context` | Lines 215–227: receipt rows present → section built and returned |
| `test_build_context_section_with_bank_context_only` | Lines 215–227: only bank rows → section built |
| `test_get_receipt_context_returns_formatted_lines` | Lines 238–270: cursor returns rows → formatted string |
| `test_get_receipt_context_empty_result` | Line 269: no rows → empty string |
| `test_get_receipt_context_db_error_returns_empty` | Lines 264–266: cursor raises → empty string returned |
| `test_get_bank_context_returns_formatted_lines` | Lines 280–295: cursor returns rows → formatted string |
| `test_get_bank_context_empty_result` | Line 296: no rows → empty string |
| `test_get_bank_context_db_error_returns_empty` | Lines 293–295: cursor raises → empty string |

---

## 5. Code Style

- `@pytest.mark.unit` on every test class
- AAA comment structure: `# Arrange`, `# Act`, `# Assert`
- One assertion focus per test

---

## 6. Expected Coverage Outcome

| File | Before | After (est.) |
|---|---|---|
| `services/evaluation.py` | 62.6% | ~92% |
| `services/bank_categorization.py` | 61.9% | ~95% |
| `services/ground_truth.py` | 64.3% | ~95% |
| **Overall `src/`** | **75.2%** | **~79–80%** |

---

## 7. Out of Scope

- `src/tasks/` (Celery task orchestration)
- `src/main.py`, `src/app.py` (route layer)
- Async entry_ids path with on_progress in `run_evaluation_async` (lines 145–148 — covered by adding `on_progress` test)
- `_evaluate_ground_truth_entry_async` error path (lines 184–187) — covered by `test_evaluate_entry_ocr_raises` equivalent for async (low ROI given async path already tested by happy-path test)
