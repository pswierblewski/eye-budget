# Research: Fix PaddleOCR Serialization Error

**Feature**: 007-fix-paddle-pickling  
**Date**: 2026-04-01

## Root Cause Analysis

### Decision: Add `_to_serializable()` inside the subprocess worker

**Rationale**: `ProcessPoolExecutor.submit()` serializes the return value with `pickle` to send it from the worker subprocess back to the main process. PaddleOCR ≥ 2.10 changed its result type — instead of plain lists it returns objects that hold `CopyableWeakMethod` references (internal weak-reference wrappers). Python's `pickle` cannot serialize `weakref.WeakMethod` instances, so the cross-process transfer raises `cannot pickle 'CopyableWeakMethod' object`.

The fix must happen *inside* the subprocess (`_ocr_worker`) — converting the result before it crosses the process boundary. Converting after `future.result()` (in the main process) never works because the exception is raised during unpickling, before the caller receives any data.

**Alternatives considered**:

| Alternative | Why rejected |
|-------------|-------------|
| Convert result in `detect()` after `future.result()` | Fails — pickle error is raised during deserialization, before `detect()` receives the object |
| Downgrade PaddleOCR to < 2.10 | Undesirable — new models (PP-OCRv5) require ≥ 2.10; regression in OCR accuracy |
| Switch from `ProcessPoolExecutor` to `ThreadPoolExecutor` | PaddleOCR (PaddlePaddle) is not thread-safe when loaded alongside Celery fork workers; current spawn-based isolation was introduced specifically to prevent SIGSEGV (see feature-receipt-text-localization-overlay history) |
| Use `multiprocessing.Pipe` / `Queue` with explicit serialization | More complex, harder to maintain; `ProcessPoolExecutor` with pre-serialization achieves the same result with less code |

## Result Format Research

### PaddleOCR ≥ 2.10 (new dict format)

`ocr.ocr(path)` returns a list of page objects. Each page object is dict-like with:
- `rec_texts`: list of `str`
- `rec_scores`: list of `float`
- `rec_polys` (preferred) or `dt_polys`: list of polygon arrays (ndarray or list)

### PaddleOCR < 2.10 (legacy list format)

Each page is a list of `[polygon, [text, score]]` items, where polygon is a list of 4 `[x, y]` points.

### Conversion strategy

`_to_serializable()` normalises both formats into the legacy shape — `[[polygon, [text, score]], ...]` per page — which is already handled correctly by the existing `_parse_result()` method. No changes needed to `_parse_result()`.

## Test Strategy Research

### Existing test coverage

`TestTextLocalizationService` in `backend/tests/unit/test_services_image.py` already covers:
- `detect()` with mocked executor (legacy format canned result)
- `detect()` BrokenProcessPool retry
- `detect_async()` delegation
- `_parse_result()` for None, empty, new dict format, legacy format, plain string text_info, bad item skipped

### Gap

`_to_serializable()` is a new module-level function with no test coverage. Tests must be added.

### Test approach

Import `_to_serializable` directly and test it as a pure function — no subprocess, no mocking needed. Cover:
1. `None` input → `[]`
2. New dict format (PaddleOCR 2.10+) → correct legacy-shaped output
3. Legacy list format → passed through correctly
4. Page with `None` or falsy entry → skipped gracefully
5. End-to-end: `_ocr_worker` mock verifies result goes through `_to_serializable` before return (tested via executor mock in `detect()` — existing pattern suffices)

## CI/CD

The existing GitHub Actions pipeline runs `python -m pytest` in the backend container. No changes to the pipeline are needed — the new tests will be picked up automatically.
