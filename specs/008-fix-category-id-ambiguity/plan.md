# Implementation Plan: Fix Ambiguous Column in Category Creation

**Branch**: `008-fix-category-id-ambiguity` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/008-fix-category-id-ambiguity/spec.md`

## Summary

The `POST /categories` endpoint returns HTTP 500 because the duplicate-check SQL query in `CategoriesRepository.create_category()` references the unqualified column `id` in a self-join, which PostgreSQL rejects as ambiguous. The fix qualifies `id` and `name` with the `c.` table alias. A unit test is added to prevent regression.

## Technical Context

**Language/Version**: Python 3.11.7  
**Primary Dependencies**: FastAPI, psycopg2-binary, pydantic v2, pytest ≥ 8.0, pytest-mock ≥ 3.14  
**Storage**: PostgreSQL (no schema changes)  
**Testing**: pytest (unit tests with mock cursor)  
**Target Platform**: Linux server (Docker)  
**Project Type**: web-service (backend only)  
**Performance Goals**: ≤ 200 ms p95 for synchronous endpoints (unchanged)  
**Constraints**: No migration, no API contract change, no frontend change  
**Scale/Scope**: Single repository method, single SQL query

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ Pass | Single-responsibility fix; no new abstractions; parameterized query preserved |
| II. Testing Standards | ✅ Pass | Unit test added for changed repository method |
| III. UX Consistency | ✅ N/A | No frontend change |
| IV. Performance | ✅ Pass | Fix removes a DB error path; no performance impact |
| V. Frontend Architecture | ✅ N/A | No frontend change |
| VI. Backend Conventions | ✅ Pass | Parameterized queries; commit/rollback pattern unchanged; `if not self.conn` guard preserved |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/008-fix-category-id-ambiguity/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (affected files only)

```text
backend/
├── src/
│   └── repositories/
│       └── categories.py        ← fix: qualify c.id, c.name in duplicate-check SELECT
└── tests/
    └── unit/
        └── test_categories_repository.py   ← new: unit tests for create_category()
```

## Implementation Steps

### Step 1 — Fix the SQL query

**File**: `backend/src/repositories/categories.py`, method `create_category()`, line 25.

Change:
```sql
SELECT id, name, cp.name AS parent_name
```
To:
```sql
SELECT c.id, c.name, cp.name AS parent_name
```

That is the complete code change. No other files require modification.

### Step 2 — Add unit tests

**File**: `backend/tests/unit/test_categories_repository.py` (new file)

Tests to cover:
1. **Happy path — new category**: cursor returns no existing row for the duplicate check; INSERT returns a new id; method returns a `CategoryItem` with correct fields.
2. **Idempotent path — duplicate exists**: cursor returns a row for the duplicate check; INSERT is never called; method returns the existing `CategoryItem`.
3. **With parent**: same as happy path but `parent_id` is set; parent name lookup is executed first.

Use `pytest-mock` (`mocker.MagicMock`) to mock `conn` and `cursor`. Follow the AAA comment structure (Arrange / Act / Assert) per project conventions.
