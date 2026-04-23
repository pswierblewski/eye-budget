# Quickstart: Fix PaddleOCR Serialization Error

**Feature**: 007-fix-paddle-pickling  
**Date**: 2026-04-01

## What was broken

`POST /receipts/{id}/localize` returned HTTP 500 with `cannot pickle 'CopyableWeakMethod' object`. PaddleOCR ≥ 2.10 changed its result objects to contain internal weak references that Python's `pickle` cannot serialize — this broke the cross-process data transfer in `ProcessPoolExecutor`.

## What changed

One file: `backend/src/services/text_localization.py`

- Added `_to_serializable(result)` — a module-level function that converts PaddleOCR result objects to plain Python lists before they leave the subprocess.
- Modified `_ocr_worker` to call `_to_serializable(ocr.ocr(image_path))` instead of returning the raw result.

No database migrations. No API contract changes. No frontend changes.

## How to apply the stash and verify

```bash
# 1. Make sure you are on the feature branch
git checkout 007-fix-paddle-pickling

# 2. Apply the stashed implementation
git stash pop

# 3. Run existing tests (must stay green)
cd backend && python -m pytest tests/unit/test_services_image.py -v

# 4. After adding new tests (tasks.md step 2), run the full suite
python -m pytest -v
```

## How to verify on the server (after CI/CD deploy)

```bash
# Replace 4419 with any receipt ID that has a stored image
curl -X POST http://192.168.1.184:8001/receipts/4419/localize
# Expected: HTTP 200 with {"image_width":..., "image_height":..., "product_regions":{...}}
# Previously: HTTP 500 {"detail":"cannot pickle 'CopyableWeakMethod' object"}
```

## Test coverage added

New class `TestToSerializable` in `backend/tests/unit/test_services_image.py`:

| Test | Scenario |
|------|----------|
| `test_none_result_returns_empty` | `_to_serializable(None)` → `[]` |
| `test_new_dict_format` | PaddleOCR 2.10+ dict page → correct legacy-shaped output |
| `test_legacy_list_format` | Legacy `[polygon, [text, score]]` page → passed through correctly |
| `test_falsy_page_skipped` | `None` page in result → skipped, rest returned |
| `test_empty_result_returns_empty` | Empty list input → `[]` |
