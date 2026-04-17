# Implementation Plan: Fix PaddleOCR Serialization Error

**Branch**: `007-fix-paddle-pickling` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/007-fix-paddle-pickling/spec.md`

## Summary

`POST /receipts/{id}/localize` returns HTTP 500 because PaddleOCR ≥ 2.10 result objects contain `CopyableWeakMethod` references that cannot be pickled across the `ProcessPoolExecutor` process boundary. The fix adds a `_to_serializable()` function that converts the raw PaddleOCR result to plain Python structures (`list`, `str`, `int`, `float`) inside the subprocess worker before the data crosses the process boundary. New unit tests cover all four conversion paths (new dict format, legacy list format, `None` result, empty/`None` pages).

## Technical Context

**Language/Version**: Python 3.11.7  
**Primary Dependencies**: PaddleOCR ≥ 2.10, concurrent.futures.ProcessPoolExecutor, pytest ≥ 8.0, pytest-mock ≥ 3.14  
**Storage**: N/A (no schema changes)  
**Testing**: pytest; new tests in `backend/tests/unit/test_services_image.py`  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web service (FastAPI backend)  
**Performance Goals**: No change — conversion is O(n) on OCR lines; negligible overhead  
**Constraints**: Must not break existing `_parse_result` logic or BrokenProcessPool retry behaviour  
**Scale/Scope**: One file changed (`text_localization.py`), one test file extended

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ PASS | `_to_serializable` has single responsibility; fits in one sentence: "Convert PaddleOCR result to picklable Python structures." No hardcoded values. No dead code. |
| II. Testing Standards | ✅ PASS | New unit tests REQUIRED and planned for all four conversion paths. No new integration test needed — endpoint contract and pipeline are unchanged; existing integration tests continue to mock `text_localization_service`. |
| III. UX Consistency | ✅ N/A | No user-facing changes. |
| IV. Performance | ✅ PASS | Conversion is O(n); runs inside the subprocess (not on the main thread). No new DB queries. |
| V. Frontend Architecture | ✅ N/A | No frontend changes. |
| VI. Backend Conventions | ✅ PASS | No new routes, no new Pydantic models, no migration. `_to_serializable` is a private module-level function — consistent with existing `_ocr_worker` and `_get_executor` pattern. |

*Post-design re-check*: No design changes introduced violations. Constitution check remains PASS.

## Project Structure

### Documentation (this feature)

```text
specs/007-fix-paddle-pickling/
├── plan.md              ✅ this file
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Phase 1 output
├── quickstart.md        ✅ Phase 1 output
├── contracts/           ✅ Phase 1 output
│   └── localize.md
└── tasks.md             (Phase 2 — tasks.md)
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── services/
│       └── text_localization.py   ← only file changed
└── tests/
    └── unit/
        └── test_services_image.py ← new tests added here (TestToSerializable class)
```

**Structure Decision**: Single-file backend patch. No new files in `src/`. Tests extend an existing test file under the existing `TestTextLocalizationService` convention. No frontend, no migrations, no new routes.
