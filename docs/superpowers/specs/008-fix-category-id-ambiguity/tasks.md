# Tasks: Fix Ambiguous Column in Category Creation

**Input**: Design documents from `/specs/008-fix-category-id-ambiguity/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Organization**: Single user story — tasks ordered TDD-style (tests first, then fix).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

*No project initialization required — this is a single-file bug fix with no new dependencies or infrastructure.*

---

## Phase 2: Foundational (Blocking Prerequisites)

*No foundational work required — the fix is isolated to one repository method. Existing DB connection, App lifecycle, and service wiring are untouched.*

---

## Phase 3: User Story 1 — Create a New Category Successfully (Priority: P1) 🎯 MVP

**Goal**: `POST /categories` succeeds without a 500 error; duplicate detection and idempotent return work correctly.

**Independent Test**: Run `python -m pytest backend/tests/unit/test_categories_repository.py -v`; then send a `POST /categories` request and confirm HTTP 200/201 with a valid `CategoryItem` body.

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementation

- [x] T001 [US1] Write unit tests for `create_category()` (happy path, duplicate, with parent) in `backend/tests/unit/test_categories_repository.py` — use `pytest-mock` MagicMock for `conn`/`cursor`; follow AAA comment structure

### Implementation for User Story 1

- [x] T002 [US1] Fix the duplicate-check SQL query in `backend/src/repositories/categories.py` line 25: change `SELECT id, name` to `SELECT c.id, c.name`

**Checkpoint**: All three unit tests pass; `POST /categories` returns HTTP 200/201 on the server.

---

## Phase 4: Polish & Verification

**Purpose**: Confirm the fix is clean and nothing regressed.

- [x] T003 Run the full backend test suite (`cd backend && python -m pytest`) and confirm zero failures
- [x] T004 [P] Verify fix on server: check `docker logs eye-budget-backend-1` for absence of `is ambiguous` after a category creation attempt

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3**: No blocking prerequisites — can start immediately
- **Phase 4**: Depends on Phase 3 completion

### User Story Dependencies

- **User Story 1 (P1)**: Self-contained — no dependencies on other stories or infrastructure changes

### Within User Story 1

1. T001 (unit tests) — write first, confirm they **fail** before the fix
2. T002 (fix SQL) — apply fix, confirm T001 tests now **pass**
3. T003–T004 — final verification

---

## Parallel Example: User Story 1

```bash
# T001 and T002 are sequential (TDD order):
Task: "Write unit tests → confirm FAIL"
Task: "Apply SQL fix → confirm PASS"

# T003 and T004 can run in parallel once T002 is done:
Task: "Run full backend test suite"
Task: "Verify fix on server logs"
```

---

## Implementation Strategy

### MVP (this entire feature is MVP)

1. Write unit tests (T001) — they must fail first
2. Apply the one-line SQL fix (T002) — tests now pass
3. Run full suite (T003) — confirm no regression
4. Verify on server (T004)
5. **Done** — open PR to master

---

## Notes

- Total tasks: **4**
- Tasks per user story: US1 → 2 implementation tasks + 2 polish/verification tasks
- Parallel opportunities: T003 ‖ T004 (final verification phase)
- The entire change is **2 lines of code** — one SQL keyword qualification and a new test file
