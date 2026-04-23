# Research: Fix Ambiguous Column in Category Creation

**Feature**: 008-fix-category-id-ambiguity  
**Date**: 2026-04-01

## Summary

No unknowns were identified. The root cause, fix, and required test approach are fully deterministic from code inspection and server logs.

---

## Decision 1: Root cause

**Decision**: The bug is in `backend/src/repositories/categories.py`, method `create_category()`, in the duplicate-check query (lines 23–33). The `SELECT` clause uses bare `id` and `name` without a table alias, but the query performs a self-join (`categories c LEFT JOIN categories cp`), so PostgreSQL cannot determine which table's `id` is referenced.

**Rationale**: Server log confirms `column reference "id" is ambiguous`. The fix is to qualify both columns with the `c.` alias: `SELECT c.id, c.name, cp.name AS parent_name`.

**Alternatives considered**: None — there is exactly one failing query and one correct fix.

---

## Decision 2: Scope of change

**Decision**: Backend-only, single-file fix (`backend/src/repositories/categories.py`). No migration, no API contract change, no frontend change.

**Rationale**: The `CategoryItem` response shape returned by the method is unchanged. The endpoint signature is unchanged. The fix only corrects an unqualified column reference inside an existing SQL string.

**Alternatives considered**: Rewriting the duplicate-check as a separate helper — rejected as unnecessary complexity for a one-line fix.

---

## Decision 3: Test strategy

**Decision**: Add a unit test in `backend/tests/unit/` that mocks the DB cursor and verifies `create_category()` succeeds when the duplicate-check returns no row and the INSERT returns a new id. A second test covers the idempotent path (duplicate found → existing record returned). No integration test is required for this change because no new endpoint is added.

**Rationale**: Constitution §II requires unit tests for all new/changed repository code. The fix touches only the repository layer; the service and route layers are unaffected. The existing integration test suite already exercises the full stack; the unit test is sufficient to prevent regression of this specific bug.

**Alternatives considered**: Integration test against a live DB — valid but disproportionate for a one-line SQL fix; unit test with a mock cursor is faster and equally targeted.
