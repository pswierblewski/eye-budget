# Tasks: Fix PaddleOCR Serialization Error

**Input**: Design documents from `/specs/007-fix-paddle-pickling/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Required — spec FR-005 mandates unit tests; Constitution Principle II requires them before merge.

**Organization**: Two user stories. US1 is the core fix (implementation + tests). US2 is deployment and end-to-end verification. US2 depends on US1 completing but requires no additional code changes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm starting state before any changes.

- [x] T001 Confirm branch `007-fix-paddle-pickling` is active and `git stash list` shows stash entry "fix: paddle ocr to_serializable" containing `backend/src/services/text_localization.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify clean baseline before writing tests or applying the fix.

**⚠️ CRITICAL**: Must complete before US1 work begins.

- [x] T002 Run baseline test suite `cd backend && python -m pytest -v` and confirm zero failures (stash not yet applied — current `text_localization.py` is unmodified master)

**Checkpoint**: Clean baseline confirmed — US1 implementation can now begin.

---

## Phase 3: User Story 1 — Endpoint returns bounding boxes (Priority: P1) 🎯 MVP

**Goal**: `POST /receipts/{id}/localize` returns HTTP 200 with polygon data instead of HTTP 500.

**Independent Test**: `curl -X POST http://<SERVER_IP>:8001/receipts/4419/localize` returns HTTP 200 with a `product_regions` object containing polygon arrays.

### Tests for User Story 1 (TDD — write BEFORE applying stash)

> **NOTE: Write these tests FIRST and confirm they FAIL before applying the implementation**

- [x] T003 [US1] Add class `TestToSerializable` to `backend/tests/unit/test_services_image.py` with the following five test methods (import `_to_serializable` from `src.services.text_localization`):
  - `test_none_result_returns_empty` — `_to_serializable(None)` returns `[]`
  - `test_empty_result_returns_empty` — `_to_serializable([])` returns `[]`
  - `test_new_dict_format` — page with `rec_texts`/`rec_polys`/`rec_scores` keys → correct `[[polygon, [text, score]]]` output
  - `test_legacy_list_format` — page in legacy `[polygon, [text, score]]` shape → passed through correctly
  - `test_falsy_page_skipped` — result containing a `None` page → that page skipped, empty list returned

- [x] T004 [US1] Run `cd backend && python -m pytest tests/unit/test_services_image.py::TestToSerializable -v` and confirm all 5 tests FAIL with `ImportError` (function does not exist yet on this branch)

### Implementation for User Story 1

- [x] T005 [US1] Apply the stashed implementation: `git stash pop` — this adds `_to_serializable()` to `backend/src/services/text_localization.py` and changes `_ocr_worker` to call `_to_serializable(ocr.ocr(image_path))`

- [x] T006 [US1] Run `cd backend && python -m pytest tests/unit/test_services_image.py::TestToSerializable -v` — confirm all 5 new tests PASS

- [x] T007 [US1] Run full backend test suite `cd backend && python -m pytest -v` — confirm zero regressions across all existing tests

- [x] T008 [US1] Commit: stage `backend/src/services/text_localization.py` and `backend/tests/unit/test_services_image.py`, message: `fix(ocr): convert PaddleOCR result to picklable structures in subprocess worker`

**Checkpoint**: US1 complete. `_to_serializable` implemented and covered by 5 unit tests. Full suite green.

---

## Phase 4: User Story 2 — Bounding boxes visible in UI (Priority: P2)

**Goal**: After deployment, bounding-box overlays appear on receipt images in the frontend. No code changes needed — this phase is deployment and end-to-end verification.

**Independent Test**: Open receipt 4419 in the app, trigger localization, confirm polygon overlays appear on the receipt image.

### Deployment for User Story 2

- [ ] T009 [US2] Push branch and open PR to `master`: `git push -u origin 007-fix-paddle-pickling` then `gh pr create --title "fix(ocr): convert PaddleOCR result to picklable structures" --base master`

- [ ] T010 [US2] Monitor GitHub Actions CI/CD run (`gh run watch` or `gh run list`) — confirm all checks pass (backend pytest, frontend lint + build)

- [ ] T011 [US2] After PR merge and automatic deploy, SSH to homeserver and verify: `curl -s -X POST http://localhost:8001/receipts/4419/localize | python3 -c "import sys,json; r=json.load(sys.stdin); print('OK' if 'product_regions' in r else 'FAIL', r.get('detail',''))"` — expected output: `OK`

- [ ] T012 [US2] Open `http://<SERVER_IP>:3000` in browser, navigate to receipt 4419, trigger localization, confirm bounding-box polygon overlays are rendered on the receipt image

**Checkpoint**: Both user stories verified in production. Feature complete.

---

## Phase 5: Polish

- [ ] T013 [P] Verify `CLAUDE.md` Recent Changes section reflects the fix (update if CI/CD did not auto-update it)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS US2
- **US2 (Phase 4)**: Depends on US1 (T008 commit + T009 PR merge)
- **Polish (Phase 5)**: Depends on US2 complete

### User Story Dependencies

- **US1 (P1)**: Depends only on clean baseline (Phase 2). Fully independent.
- **US2 (P2)**: Depends on US1 being merged and deployed. No new code changes.

### Within US1

```
T003 (write tests) → T004 (confirm FAIL) → T005 (apply stash) → T006 (confirm PASS) → T007 (full suite) → T008 (commit)
```

### Parallel Opportunities

- T001 and T002 can overlap (T002 can run while checking stash)
- T003 and T007 touch different concerns but T007 must run after T006

---

## Parallel Example: User Story 1

```bash
# T003 and reviewing the stash diff can happen simultaneously:
Task: "Review git stash show -p to understand exact change"
Task: "Write TestToSerializable class in test_services_image.py"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1: Setup — confirm branch and stash
2. Phase 2: Baseline — clean suite
3. Phase 3: Write tests → confirm FAIL → apply stash → confirm PASS → commit
4. **STOP and VALIDATE**: Full suite green, stash applied, commit ready
5. Open PR → merge

### Full Delivery

1. Complete MVP (US1)
2. CI/CD deploys automatically on merge to master
3. Verify US2 end-to-end on production

---

## Notes

- [P] tasks = different files, no blocking dependencies
- The stash (`git stash pop`) is a one-time operation — do NOT run it before T004 TDD verification
- T004 is a deliberate TDD gate: tests must FAIL before implementation is applied
- US2 requires no code changes — it is purely deployment verification
- If `git stash pop` results in a conflict, the stash was from `006-semantic-versioning` (which was ahead of master); resolve by keeping the stash version of `text_localization.py`
