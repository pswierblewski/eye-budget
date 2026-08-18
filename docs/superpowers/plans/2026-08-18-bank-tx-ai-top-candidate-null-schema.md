# Bank tx `ai_top_candidate: null` — Zod schema fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the transient `QueryState` error on `/bank-transactions` after CSV import by accepting `ai_top_candidate: null` in the frontend Zod schema, matching the backend API contract.

**Architecture:** One-line schema change in `BankTransactionListItemSchema` (`nullable().optional()`). Regression tests parse a paginated API-shaped payload with `null`, object, and missing field. Frontend PATCH version bump only — backend unchanged.

**Tech Stack:** Next.js 14, TypeScript 5, Zod v3, Vitest (node environment).

**Spec:** `docs/superpowers/specs/2026-08-18-bank-tx-ai-top-candidate-null-schema-design.md` (Approved)

## Global Constraints

- **Scope:** frontend only — no backend changes.
- **Schema field:** `ai_top_candidate: CategoryCandidateSchema.nullable().optional()` in `BankTransactionListItemSchema`.
- **Version bump:** frontend PATCH `1.8.2` → `1.8.3` in `package.json` and `package-lock.json` (root `"version"` and `packages[""].version`).
- **UI copy:** Polish only — no UI string changes in this fix.
- **Out of scope:** `QueryState` / `invalidateQueries` timing / Pusher handler changes.

---

## File map

| File | Responsibility |
|------|----------------|
| `frontend/lib/bankTransactionListSchema.test.ts` | Vitest regression: paginated list parses with `ai_top_candidate: null`, object, absent |
| `frontend/lib/types.ts` | `BankTransactionListItemSchema.ai_top_candidate` accepts `null` |
| `frontend/package.json` | `"version": "1.8.3"` |
| `frontend/package-lock.json` | matching `"version"` at root and `packages[""]` |

---

### Task 1: Branch

**Files:**
- (git only)

- [ ] **Step 1: Create fix branch**

Run:

```bash
cd /Users/pawelswierblewski/private/eye-budget && git checkout -b fix/bank-tx-ai-top-candidate-null-schema
```

Expected: new branch from current `master`.

---

### Task 2: Failing schema tests (TDD)

**Files:**
- Create: `frontend/lib/bankTransactionListSchema.test.ts`

**Interfaces:**
- Consumes: `BankTransactionListItemSchema`, `paginatedSchema` from `frontend/lib/types.ts`
- Produces: three passing tests that currently **fail** because schema rejects `null`

- [ ] **Step 1: Write the failing tests**

Create `frontend/lib/bankTransactionListSchema.test.ts`:

```ts
/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import {
  BankTransactionListItemSchema,
  paginatedSchema,
} from "./types";

const listSchema = paginatedSchema(BankTransactionListItemSchema);

const baseItem = {
  id: 1,
  reference_number: "REF-001",
  booking_date: "2026-08-18",
  counterparty: null,
  description: null,
  amount: -42.5,
  currency: "PLN",
  operation_type: null,
  category_id: null,
  category_name: null,
};

describe("BankTransactionListItemSchema (paginated)", () => {
  it("parses ai_top_candidate: null (post-import, pre-categorization)", () => {
    const payload = {
      items: [{ ...baseItem, ai_top_candidate: null }],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items).toHaveLength(1);
    expect(result.items[0].ai_top_candidate).toBeNull();
  });

  it("parses ai_top_candidate object", () => {
    const payload = {
      items: [
        {
          ...baseItem,
          ai_top_candidate: {
            category_id: 2,
            category_name: "Jedzenie",
            category_score: 0.87,
          },
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items[0].ai_top_candidate).toEqual({
      category_id: 2,
      category_name: "Jedzenie",
      category_score: 0.87,
    });
  });

  it("parses missing ai_top_candidate field", () => {
    const payload = {
      items: [baseItem],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items[0].ai_top_candidate).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npm run test:run -- lib/bankTransactionListSchema.test.ts
```

Expected: **FAIL** on `parses ai_top_candidate: null` with Zod error `Expected object, received null`.

- [ ] **Step 3: Commit failing test**

```bash
cd /Users/pawelswierblewski/private/eye-budget && git add frontend/lib/bankTransactionListSchema.test.ts && git commit -m "$(cat <<'EOF'
test(frontend): add bank tx list schema regression for null ai_top_candidate

EOF
)"
```

---

### Task 3: Schema fix

**Files:**
- Modify: `frontend/lib/types.ts:327`

**Interfaces:**
- Consumes: failing tests from Task 2
- Produces: `BankTransactionListItemSchema` where `ai_top_candidate` type is `CategoryCandidate | null | undefined`

- [ ] **Step 1: Update schema**

In `frontend/lib/types.ts`, change line 327 from:

```ts
  ai_top_candidate: CategoryCandidateSchema.optional(),
```

to:

```ts
  ai_top_candidate: CategoryCandidateSchema.nullable().optional(),
```

- [ ] **Step 2: Run tests to verify pass**

Run:

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npm run test:run -- lib/bankTransactionListSchema.test.ts
```

Expected: **3 passed**.

Also run full frontend unit suite:

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npm run test:run
```

Expected: all tests pass (including existing `bankTxCategoryListUi.test.ts`).

- [ ] **Step 3: Typecheck**

Run:

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npx tsc --noEmit
```

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/pawelswierblewski/private/eye-budget && git add frontend/lib/types.ts && git commit -m "$(cat <<'EOF'
fix(frontend): accept null ai_top_candidate in bank transaction list schema

Align Zod with backend/Pydantic contract so CSV import refetch during
background categorization no longer fails apiFetch validation.
EOF
)"
```

---

### Task 4: Frontend version bump (PATCH)

**Files:**
- Modify: `frontend/package.json` — `"version": "1.8.3"`
- Modify: `frontend/package-lock.json` — `"version": "1.8.3"` at line ~3 (root) and ~9 (`packages[""].version`)

- [ ] **Step 1: Bump version**

Update both files from `1.8.2` to `1.8.3`.

- [ ] **Step 2: Commit**

```bash
cd /Users/pawelswierblewski/private/eye-budget && git add frontend/package.json frontend/package-lock.json && git commit -m "$(cat <<'EOF'
chore(frontend): bump version to 1.8.3
EOF
)"
```

---

### Task 5: Manual verification

**Files:** none

- [ ] **Step 1: Start app** (if not already running)

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npm run dev
```

- [ ] **Step 2: Reproduce fixed scenario**

1. Open `/bank-transactions`.
2. Import CSV with new transactions (triggers background categorization).
3. While progress shows „Kategoryzacja… X/Y”, confirm **no** red `QueryState` panel.
4. Confirm AI category proposals appear incrementally; list stays usable throughout.

- [ ] **Step 3: Lint**

```bash
cd /Users/pawelswierblewski/private/eye-budget/frontend && npm run lint
```

Expected: no new errors.

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| `nullable().optional()` on `ai_top_candidate` | Task 3 |
| Test: null / object / missing field | Task 2 |
| PATCH `1.8.2` → `1.8.3` | Task 4 |
| No backend / UI / QueryState changes | Global Constraints |
| Manual import CSV verification | Task 5 |

No placeholders. All code blocks are complete.
