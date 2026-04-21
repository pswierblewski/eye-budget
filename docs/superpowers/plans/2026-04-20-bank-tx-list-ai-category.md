# Bank transaction list — AI top category + Pusher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On `/bank-transactions`, show the LLM top category proposal and a „Zapisz kategorię” button in the collapsed row when rules allow; update the row in realtime via Pusher when background categorization saves candidates.

**Architecture:** Extend `GET /bank-transactions` list items with optional `ai_top_candidate` derived from `category_candidates` (max `category_score`). After each successful `update_candidates` in the Celery task, emit `categorization.transaction_updated` on channel `bank-transactions`. Frontend subscribes once per page mount, merges events into React Query cache, and reuses a small pure-TS module for visibility rules covered by Vitest.

**Tech Stack:** Backend: Python 3, Pydantic, pytest, Celery, Pusher. Frontend: Next.js 14, React 18, TanStack Query, Vitest, jsdom, React Testing Library, Zod.

**Spec:** `docs/superpowers/specs/2026-04-20-bank-tx-list-ai-category-design.md` (Approved)

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/src/bank_category_top.py` | Pure: `top_category_candidate_from_stored_json(value) -> dict \| None` — parses DB JSON (str/bytes/list/None), returns `{"category_id", "category_name", "category_score"}` or `None` |
| `backend/src/data.py` | `BankTransactionListItem`: add optional `ai_top_candidate: CategoryCandidate \| None = None` |
| `backend/src/repositories/bank_transactions.py` | `get_list` SELECT includes `bt.category_candidates`; map index shift; fill `ai_top_candidate` via helper |
| `backend/src/tasks/categorize_bank_transactions.py` | After successful `update_candidates`, `pusher.trigger(..., "categorization.transaction_updated", payload)` |
| `backend/tests/unit/test_bank_category_top.py` | Unit tests for helper (empty, malformed, single, tie-break by first after sort) |
| `backend/tests/unit/tasks/test_categorize_bank_transactions.py` | Assert `categorization.transaction_updated` fired with expected payload when categorization updates candidates |
| `frontend/vitest.config.ts` | Vitest + React plugin, `jsdom`, alias `@` -> `.` |
| `frontend/vitest.setup.ts` | `import "@testing-library/jest-dom/vitest"` |
| `frontend/package.json` | `test` / `test:run` scripts; devDependencies: `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` |
| `frontend/lib/types.ts` | Extend `BankTransactionListItemSchema` with optional `ai_top_candidate: CategoryCandidateSchema.optional()` |
| `frontend/lib/bankTxCategoryListUi.ts` | `shouldShowAiCategoryProposal(tx: BankTransactionListItem): boolean` — encodes spec visibility table |
| `frontend/lib/bankTxCategoryListUi.test.ts` | Vitest tests for `shouldShowAiCategoryProposal` |
| `frontend/app/bank-transactions/page.tsx` | Category column UI; Pusher bind; `setQueryData` merge; save mutation `stopPropagation` on button |

---

### Task 1: Branch

**Files:**
- (git only)

- [ ] **Step 1: Create feature branch**

Run:

```bash
cd /home/pawel/eye-budget && git checkout -b feature/bank-tx-list-ai-category
```

Expected: branch created from current `master` (or your default).

- [ ] **Step 2: Commit**

No file changes yet; optional empty commit skipped — proceed to Task 2.

---

### Task 2: Backend — `top_category_candidate_from_stored_json`

**Files:**
- Create: `backend/src/bank_category_top.py`
- Create: `backend/tests/unit/test_bank_category_top.py`

- [ ] **Step 1: Add implementation**

Create `backend/src/bank_category_top.py`:

```python
"""Derive top LLM category candidate from bank_transactions.category_candidates JSON."""
from __future__ import annotations

import json
from typing import Any


def top_category_candidate_from_stored_json(value: Any) -> dict[str, Any] | None:
    """
    Parse stored JSON and return the candidate with highest category_score.
    Returns a dict with keys category_id (int), category_name (str), category_score (float), or None.
    """
    if value is None:
        return None
    data = value
    if isinstance(value, (bytes, str)):
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, list) or len(data) == 0:
        return None
    best: dict[str, Any] | None = None
    best_score: float | None = None
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            cid = int(item["category_id"])
            name = str(item.get("category_name", ""))
            score = float(item.get("category_score", 0.0))
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or best_score is None or score > best_score:
            best = {"category_id": cid, "category_name": name, "category_score": score}
            best_score = score
    return best
```

- [ ] **Step 2: Add tests**

Create `backend/tests/unit/test_bank_category_top.py`:

```python
import pytest

from src.bank_category_top import top_category_candidate_from_stored_json


@pytest.mark.unit
class TestTopCategoryCandidateFromStoredJson:
    def test_none(self):
        assert top_category_candidate_from_stored_json(None) is None

    def test_empty_list(self):
        assert top_category_candidate_from_stored_json([]) is None

    def test_invalid_json_string(self):
        assert top_category_candidate_from_stored_json("{") is None

    def test_picks_highest_score(self):
        raw = [
            {"category_id": 1, "category_name": "A", "category_score": 0.5},
            {"category_id": 2, "category_name": "B", "category_score": 0.9},
        ]
        assert top_category_candidate_from_stored_json(raw) == {
            "category_id": 2,
            "category_name": "B",
            "category_score": 0.9,
        }

    def test_json_bytes(self):
        b = b'[{"category_id":3,"category_name":"X","category_score":0.1}]'
        assert top_category_candidate_from_stored_json(b) == {
            "category_id": 3,
            "category_name": "X",
            "category_score": 0.1,
        }

    def test_skips_malformed_entries(self):
        raw = [
            {"bad": 1},
            {"category_id": 5, "category_name": "Ok", "category_score": 0.2},
        ]
        assert top_category_candidate_from_stored_json(raw) == {
            "category_id": 5,
            "category_name": "Ok",
            "category_score": 0.2,
        }
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_bank_category_top.py -v
```

Expected: all passed.

- [ ] **Step 4: Commit**

```bash
git add backend/src/bank_category_top.py backend/tests/unit/test_bank_category_top.py
git commit -m "feat(backend): derive top bank category candidate from stored JSON"
```

---

### Task 3: Backend — list model and repository

**Files:**
- Modify: `backend/src/data.py` (class `BankTransactionListItem`)
- Modify: `backend/src/repositories/bank_transactions.py` (`get_list` SQL + row mapping)

- [ ] **Step 1: Extend Pydantic model**

In `backend/src/data.py`, locate `class BankTransactionListItem` (around line 349). Add after `split_count`:

```python
    ai_top_candidate: CategoryCandidate | None = None
```

(`CategoryCandidate` is already defined in the same file.)

- [ ] **Step 2: Extend SQL SELECT**

In `backend/src/repositories/bank_transactions.py`, inside `get_list`, in the main `SELECT` list, add **`bt.category_candidates`** immediately **before** `COUNT(*) OVER () AS total_count` (after the `split_count` subquery closing paren).

- [ ] **Step 3: Fix row indices**

- Import: `from ..bank_category_top import top_category_candidate_from_stored_json`
- Replace `total = int(rows[0][15])` with `total = int(rows[0][16])` (new column at index 15).
- In the comprehension, add local: `raw_top = top_category_candidate_from_stored_json(r[15])`
- Build `CategoryCandidate` when `raw_top` is not None: `CategoryCandidate(**raw_top)` — or pass `None` for `ai_top_candidate`.

Example constructor kwargs addition:

```python
                ai_top_candidate=(
                    CategoryCandidate(**raw_top) if raw_top else None
                ),
```

Add `CategoryCandidate` to imports from `..data` in this file if not already imported.

- [ ] **Step 4: Run delegation / smoke**

Run:

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_delegation.py -k bank_transactions -v --tb=short
```

Fix any broken mocks that assume old `get_list` signature (unlikely). If full suite is fast:

```bash
pytest tests/unit/ -q --tb=line
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/data.py backend/src/repositories/bank_transactions.py
git commit -m "feat(backend): expose ai_top_candidate on bank transaction list items"
```

---

### Task 4: Backend — Pusher `categorization.transaction_updated`

**Files:**
- Modify: `backend/src/tasks/categorize_bank_transactions.py`
- Modify: `backend/tests/unit/tasks/test_categorize_bank_transactions.py`

- [ ] **Step 1: Trigger after `update_candidates`**

In `backend/src/tasks/categorize_bank_transactions.py`:

- Import `top_category_candidate_from_stored_json` from `..bank_category_top`.

Inside `_process_one`, **after** the block that calls `update_candidates` successfully (inside the `if tx is not None` path, after the DB update with candidates), call:

```python
        top = top_category_candidate_from_stored_json(candidates)
        pusher.trigger(
            "bank-transactions",
            "categorization.transaction_updated",
            {"bank_transaction_id": tx_id, "ai_top_candidate": top},
        )
```

Use the same `candidates` variable passed to `update_candidates` (the list from LLM). If categorization failed before `update_candidates`, do not emit this event.

If `tx is None`, keep existing behavior (only `categorization.progress`).

- [ ] **Step 2: Extend unit test**

In `backend/tests/unit/tasks/test_categorize_bank_transactions.py`, add a test that mocks a full happy path where `get_by_id` returns a transaction, `assign_candidates_async` returns a non-empty list, and `update_candidates` is called — then assert `triggers_with_event(mock_pusher, "bank-transactions", "categorization.transaction_updated")` has at least one call with payload containing `bank_transaction_id` and matching `ai_top_candidate`.

You will need to patch `asyncio.run` to run the coroutine or use the task’s `apply` with patched `_categorize_all` — follow the minimal pattern that already works in this file; if integration is too heavy, extract a tiny function `emit_transaction_updated(pusher, tx_id, candidates)` into `categorize_bank_transactions.py` and unit-test that function in `test_categorize_bank_transactions.py` with a **direct** call (preferred for speed).

Suggested extraction:

```python
def emit_categorization_transaction_updated(pusher, bank_transaction_id: int, candidates: list) -> None:
    top = top_category_candidate_from_stored_json(candidates)
    pusher.trigger(
        "bank-transactions",
        "categorization.transaction_updated",
        {"bank_transaction_id": bank_transaction_id, "ai_top_candidate": top},
    )
```

Test `emit_categorization_transaction_updated` with `MagicMock()` for pusher; call `_process_one` path still invokes this helper (one line).

- [ ] **Step 3: Run tests**

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/tasks/test_categorize_bank_transactions.py tests/unit/test_bank_category_top.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/tasks/categorize_bank_transactions.py backend/tests/unit/tasks/test_categorize_bank_transactions.py
git commit -m "feat(backend): Pusher event when bank tx categorization saves candidates"
```

---

### Task 5: Frontend — Vitest + RTL + jsdom

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Install dev dependencies**

Run:

```bash
cd /home/pawel/eye-budget/frontend && npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Add `vitest.config.ts`**

```typescript
import path from "path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 3: Add `vitest.setup.ts`**

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Add npm scripts** in `frontend/package.json` under `"scripts"`:

```json
    "test": "vitest",
    "test:run": "vitest run"
```

- [ ] **Step 5: Run Vitest (empty)**

```bash
cd /home/pawel/eye-budget/frontend && npm run test:run
```

Expected: passes with 0 tests or only upcoming tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/vitest.setup.ts
git commit -m "chore(frontend): add Vitest, jsdom, and React Testing Library"
```

---

### Task 6: Frontend — types and visibility helper + tests

**Files:**
- Modify: `frontend/lib/types.ts`
- Create: `frontend/lib/bankTxCategoryListUi.ts`
- Create: `frontend/lib/bankTxCategoryListUi.test.ts`

- [ ] **Step 1: Zod schema for list item**

In `frontend/lib/types.ts`, extend `BankTransactionListItemSchema` with:

```typescript
  ai_top_candidate: CategoryCandidateSchema.optional(),
```

(`CategoryCandidateSchema` already exists in the file.)

- [ ] **Step 2: Pure helper**

Create `frontend/lib/bankTxCategoryListUi.ts`:

```typescript
import type { BankTransactionListItem } from "@/lib/types";

/**
 * Whether the list row should show AI top proposal + save button (spec 2026-04-20).
 */
export function shouldShowAiCategoryProposal(tx: BankTransactionListItem): boolean {
  if (tx.category_id != null) return false;
  if (tx.receipt_category_name) return false;
  if (tx.split_category_name != null && (tx.split_count ?? 0) >= 2) return false;
  if (tx.category_name != null && tx.category_name !== "") return false;
  if (!tx.ai_top_candidate) return false;
  return true;
}
```

- [ ] **Step 3: Tests**

Create `frontend/lib/bankTxCategoryListUi.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { shouldShowAiCategoryProposal } from "./bankTxCategoryListUi";
import type { BankTransactionListItem } from "./types";

const base = (): BankTransactionListItem => ({
  id: 1,
  reference_number: "r",
  booking_date: "2026-04-20",
  counterparty: null,
  description: null,
  amount: -1,
  currency: "PLN",
  operation_type: null,
  category_id: null,
  category_name: null,
});

describe("shouldShowAiCategoryProposal", () => {
  it("false when receipt category present", () => {
    const tx = { ...base(), receipt_category_name: "Food", ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 } };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when split multi-category", () => {
    const tx = { ...base(), split_category_name: "A", split_count: 2, ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 } };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when user category name set", () => {
    const tx = { ...base(), category_name: "Assigned", ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 } };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when category_id set", () => {
    const tx = { ...base(), category_id: 9, category_name: null, ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 } };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when no ai_top_candidate", () => {
    expect(shouldShowAiCategoryProposal(base())).toBe(false);
  });

  it("true when unassigned and ai_top_candidate present", () => {
    const tx = { ...base(), ai_top_candidate: { category_id: 2, category_name: "Jedzenie", category_score: 0.87 } };
    expect(shouldShowAiCategoryProposal(tx)).toBe(true);
  });
});
```

- [ ] **Step 4: Run**

```bash
cd /home/pawel/eye-budget/frontend && npm run test:run && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/bankTxCategoryListUi.ts frontend/lib/bankTxCategoryListUi.test.ts
git commit -m "feat(frontend): bank list AI category visibility helper and types"
```

---

### Task 7: Frontend — list page UI + Pusher merge

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx`

- [ ] **Step 1: Import**

Add imports: `shouldShowAiCategoryProposal` from `@/lib/bankTxCategoryListUi`, `CategoryCandidate` type if needed.

- [ ] **Step 2: Category column**

In the `"Kategoria"` column `accessor`, **before** the final `return t.category_name ? ... : "Nie przypisano"` branch, add:

If `shouldShowAiCategoryProposal(t)` and `t.ai_top_candidate`:

- Render a `flex flex-wrap items-center gap-1.5` container with:
  - `span` className `text-xs text-gray-700 font-medium` — `t.ai_top_candidate.category_name`
  - optional `span` className `text-xs text-gray-400` — format score (e.g. same decimal style as elsewhere; spec allows e.g. `0,87` in UI — use `toLocaleString` pl-PL or simple fixed display)
  - `Button` `variant="secondary"` `size="sm"` — „Zapisz kategorię”, `onClick={(e) => { e.stopPropagation(); ... }}` calling existing `saveBankTransactionCategory` mutation pattern: you need a mutation per row or a shared handler — use `useMutation` with `mutationFn: ({ id, categoryId }) => saveBankTransactionCategory(id, categoryId)` in the page component and pass `tx.id` and `t.ai_top_candidate.category_id`. On success: `invalidateQueries` for `bank-transactions` as elsewhere.

If the page does not yet import `useMutation` at top level for category save from list, add it next to other mutations.

- [ ] **Step 3: Pusher subscription on mount**

In `BankTransactionsPage`, `useEffect` on mount:

- `const pusher = getPusher(); const channel = pusher.subscribe("bank-transactions");`
- `channel.bind("categorization.transaction_updated", handler)`
- handler: parse payload `{ bank_transaction_id: number, ai_top_candidate: ... }`, then `queryClient.setQueryData` for key `["bank-transactions", page, sortBy, sortDir]` (use the same key shape as `useQuery`) — map `old.items` to replace the item with matching `id` with `{ ...item, ai_top_candidate: payload.ai_top_candidate }` (normalize null).

Return cleanup: `channel.unbind("categorization.transaction_updated", handler)` and optionally `unsubscribe` if no other binds (coordinate with existing import/recategorize channel usage — **avoid double subscribe**: refactor to single channel ref that binds both progress events and `transaction_updated`, or share `channelRef` and add bind without second subscribe).

- [ ] **Step 4: Typecheck**

```bash
cd /home/pawel/eye-budget/frontend && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "feat(frontend): show AI top category on bank list with save and Pusher merge"
```

---

### Task 8: Quality gates and final verification

- [ ] **Step 1: Backend tests**

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/ -q --tb=line
```

- [ ] **Step 2: Frontend lint + tests + tsc**

```bash
cd /home/pawel/eye-budget/frontend && npm run lint && npm run test:run && npx tsc --noEmit
```

- [ ] **Step 3: Final commit** if any fixes were needed.

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| List shows top proposal when unassigned | Task 3, 7 |
| Button hidden for assigned / receipt / split multi | Task 6, 7 |
| No „AI:” prefix | Task 7 |
| Pusher per transaction after save | Task 4, 7 |
| Vitest + RTL + jsdom | Task 5, 6 |
| Backend unit tests | Task 2, 4 |
| Feature branch | Task 1 |

No TBD/TODO placeholders in steps above.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-20-bank-tx-list-ai-category.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks.  
2. **Inline execution** — run tasks in this session with checkpoints.

**Which approach do you want?**
