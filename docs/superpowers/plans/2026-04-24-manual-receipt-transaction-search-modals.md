# Manual receipt ↔ transaction search modals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Spec (source of truth):** [docs/superpowers/specs/2026-04-24-manual-receipt-transaction-search-modals-design.md](../specs/2026-04-24-manual-receipt-transaction-search-modals-design.md)  
> **Suggested branch:** `feature/manual-receipt-tx-link-search` (fork from up-to-date `master`)

**Goal:** Add two modals — search **receipts** to link from a bank/cash transaction, and search **unified bank+cash transactions** to link from a receipt — with one search field, amount prefill, gray-out for already-linked rows (variant B), reusing existing `linkBankToReceipt` / `linkCashToReceipt` APIs.

**Architecture:** Extend `GET /receipts` list DTO with `receipt_transaction_id` and `has_transaction_link` via scalar subqueries in `ReceiptsScansRepository.get_all`. Extend `GET /transactions` with `exclude_receipt` and `abs_amount` (tolerance band) so the receipt→transaction modal uses one paginated query, bank+cash only, matching `ABS(amount)` to receipt total like link heuristics. New React modals mirror `LinkOperationsModal` layout; wire into six UI surfaces (bank/cash list expand + detail, receipts list expand + receipt detail page).

**Tech stack:** Backend: FastAPI, Pydantic v2, PostgreSQL, existing repositories. Frontend: Next.js 14, React Query, Zod (`lib/types.ts`), `lib/api.ts`, thin `app/api/**/route.ts` proxies.

---

## File map

### Backend — modify

| File | Change |
|------|--------|
| `backend/src/data.py` | `ReceiptScanListItem`: add `receipt_transaction_id: int \| None = None`, `has_transaction_link: bool = False`. |
| `backend/src/repositories/receipts_scans.py` | In `get_all` main `SELECT`, add two scalar expressions (see Task 1); map into `ReceiptScanListItem`. |
| `backend/src/repositories/unified_transactions.py` | `get_list`: add params `exclude_receipt: bool = False`, `abs_amount: float \| None = None`. If `exclude_receipt`, append `source_type <> 'receipt'` (use same string as inner union). If `abs_amount` set, append `ABS(amount::double precision) BETWEEN %s AND %s` with `(abs_amount - 0.01, abs_amount + 0.01)` (PLN cents); document that 0.01 matches existing float money usage. |
| `backend/src/app.py` | `get_unified_transactions`: pass through new kwargs to repository. |
| `backend/src/main.py` | `list_unified_transactions`: `exclude_receipt: bool = Query(False)`, `abs_amount: float \| None = Query(None)`. Forward to `my_app.get_unified_transactions`. |
| `backend/src/version.py` | Bump **MINOR** (e.g. `1.6.0` → `1.7.0`). |
| `backend/tests/unit/test_version.py` | Assert string matches new `VERSION`. |

### Backend — tests (new or extend)

| File | Role |
|------|------|
| `backend/tests/unit/test_receipts_scans_repository.py` | If missing, add tests; else extend: list returns `receipt_transaction_id` / `has_transaction_link` for fixture data. Follow `test_bank_receipt_links_repository.py` DB patterns. |
| `backend/tests/unit/test_unified_transactions_repository.py` | Tests: `exclude_receipt=True` returns no `source_type=receipt`; `abs_amount` filters by absolute value. |

### Frontend — new

| File | Role |
|------|------|
| `frontend/components/LinkReceiptSearchModal.tsx` | Modal: controls `search` string; `listReceipts({ search, total_min, total_max, limit: 40, sort_by: "date", sort_dir: "desc" })` with `total_min`/`total_max` = `abs(anchorAmount)`; prefill input with formatted amount; rows show vendor, date, total, badge; **Powiąż** only if `receipt_transaction_id` and not `has_transaction_link`; gray + „Już powiązane” if `has_transaction_link`; if no `receipt_transaction_id`, show muted text „Paragon wymaga potwierdzenia” (no primary CTA). On success: `linkBankToReceipt` or `linkCashToReceipt` per `anchorType`. |
| `frontend/components/LinkTransactionSearchModal.tsx` | Modal: `listUnifiedTransactions({ search, exclude_receipt: true, abs_amount: receiptTotalAbs, limit: 40, sort_by: "date", sort_dir: "desc" })`. Prefill input with formatted amount. Row state: `!has_receipt` → **Powiąż**; `has_receipt && receipt_scan_id === currentScanId` → „Aktualne powiązanie”; else „Już powiązane” + disabled. Mutation: `linkBankToReceipt(bankTxId, receiptTransactionId)` or `linkCashToReceipt` for cash. |

### Frontend — modify

| File | Change |
|------|--------|
| `frontend/lib/types.ts` | Extend `ReceiptScanListItemSchema` with `receipt_transaction_id` (nullable), `has_transaction_link` (boolean, default false in parse). |
| `frontend/lib/api.ts` | `listReceipts`: response already covered by Zod if schema updated. `listUnifiedTransactions`: add optional `exclude_receipt?: boolean`, `abs_amount?: number` to query builder. |
| `frontend/app/bank-transactions/page.tsx` | Next to existing „Znajdź pasujące paragony” / candidates block: button „Wyszukaj paragon…” opening `LinkReceiptSearchModal` with `anchorType="bank"`, `id`, `amount`. |
| `frontend/app/bank-transactions/[id]/page.tsx` | Same CTA + modal in detail layout. |
| `frontend/app/cash-transactions/page.tsx` | Same for cash (`linkCashToReceipt`). |
| `frontend/app/cash-transactions/[id]/page.tsx` | Same. |
| `frontend/app/receipts/page.tsx` | `ExpandedReceiptRow`: add CTA „Wyszukaj transakcję…” opening `LinkTransactionSearchModal` with `scanId={row.id}`, `receiptTransactionId` from `row.receipt_transaction_id` (required for link — if null, button disabled or copy „Potwierdź paragon najpierw”). |
| `frontend/app/receipts/[id]/page.tsx` | CTA + modal when `scan.transaction` exists (same props as expand). |
| `frontend/package.json` & `frontend/package-lock.json` | Bump **MINOR** version (root and `packages[""].version` in lockfile if present). |

---

## Task 1: Backend — `ReceiptScanListItem` + repository SQL

**Files:**
- Modify: `backend/src/data.py` — `ReceiptScanListItem` fields
- Modify: `backend/src/repositories/receipts_scans.py` — `get_all` SELECT + row mapping
- Test: `backend/tests/unit/test_receipts_scans_repository.py` (create if absent with minimal fixture)

- [ ] **Step 1.1:** In `data.py`, add to `ReceiptScanListItem`:

```python
receipt_transaction_id: int | None = None
has_transaction_link: bool = False
```

- [ ] **Step 1.2:** In `receipts_scans.py` `get_all`, extend the `SELECT` list (before `COUNT(*) OVER`) with two expressions (adjust only the SELECT list; keep existing `FROM`/`JOIN` unless you must fix column count — add same expressions to the inner select if the query structure requires it).

Use this pattern (aliases for clarity):

```sql
(SELECT rt_sub.id FROM receipt_transactions rt_sub WHERE rt_sub.scan_id = rs.id ORDER BY rt_sub.id ASC LIMIT 1) AS receipt_transaction_id,
EXISTS (
  SELECT 1 FROM receipt_transactions rt_h
  WHERE rt_h.scan_id = rs.id
    AND (
      EXISTS (SELECT 1 FROM receipt_bank_links rbl WHERE rbl.receipt_transaction_id = rt_h.id)
      OR EXISTS (SELECT 1 FROM receipt_cash_links rcl WHERE rcl.receipt_transaction_id = rt_h.id)
    )
) AS has_transaction_link
```

If the current `SELECT` does not use table alias `rs` for `receipts_scans`, replace `rs` with the actual alias used in that query (read the file).

- [ ] **Step 1.3:** Map the two new columns in the Python row→`ReceiptScanListItem` constructor (shift indices if column order changed).

- [ ] **Step 1.4:** Run unit tests for repository:

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_receipts_scans_repository.py -v --tb=short
```

If no tests exist, add one test that mocks/fakes DB per existing patterns in the repo, or one integration-style test if that is the established style for this repository.

- [ ] **Step 1.5:** Commit:

```bash
git add backend/src/data.py backend/src/repositories/receipts_scans.py backend/tests/unit/test_receipts_scans_repository.py
git commit -m "feat(api): extend receipt list with receipt_transaction_id and has_transaction_link"
```

---

## Task 2: Backend — unified list `exclude_receipt` + `abs_amount`

**Files:**
- Modify: `backend/src/repositories/unified_transactions.py` — `get_list` signature + `conditions`
- Modify: `backend/src/app.py` — `get_unified_transactions`
- Modify: `backend/src/main.py` — `list_unified_transactions` query params
- Test: `backend/tests/unit/test_unified_transactions_repository.py`

- [ ] **Step 2.1:** Add parameters to `get_list`:

```python
exclude_receipt: bool = False,
abs_amount: float | None = None,
```

After existing `direction` handling, add:

```python
if exclude_receipt:
    conditions.append("source_type <> 'receipt'")
if abs_amount is not None:
    eps = 0.01
    conditions.append("ABS(amount::double precision) BETWEEN %s AND %s")
    params.extend([abs_amount - eps, abs_amount + eps])
```

Verify the outer query’s column name is `amount` (it is in the current `SELECT` of the unified view).

- [ ] **Step 2.2:** Thread parameters through `app.py` and `main.py` with FastAPI `Query` defaults as in the file map.

- [ ] **Step 2.3:** Add tests that (1) with `exclude_receipt=True`, no row has `source_type == "receipt"`; (2) with `abs_amount=100.0`, all returned rows satisfy `abs(amount) ≈ 100` within tolerance.

- [ ] **Step 2.4:** Run:

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_unified_transactions_repository.py -v --tb=short
```

- [ ] **Step 2.5:** Commit:

```bash
git commit -am "feat(api): add exclude_receipt and abs_amount to unified transactions list"
```

---

## Task 3: Version bump (backend)

**Files:**
- Modify: `backend/src/version.py`
- Modify: `backend/tests/unit/test_version.py`

- [ ] **Step 3.1:** Set `VERSION = "1.7.0"` (or next MINOR after current `master`).

- [ ] **Step 3.2:** Update `test_version_constant_value` expected string to match.

- [ ] **Step 3.3:** Run `pytest backend/tests/unit/test_version.py -v`

- [ ] **Step 3.4:** Commit:

```bash
git commit -am "chore: bump backend version to 1.7.0"
```

---

## Task 4: Frontend — types + API client

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 4.1:** Extend Zod schema for `ReceiptScanListItem` with:

```ts
receipt_transaction_id: z.number().nullable().optional(),
has_transaction_link: z.boolean().optional().default(false),
```

- [ ] **Step 4.2:** In `listUnifiedTransactions`, append to `URLSearchParams` when defined:

```ts
if (params.exclude_receipt) qs.set("exclude_receipt", "true");
if (params.abs_amount != null) qs.set("abs_amount", String(params.abs_amount));
```

- [ ] **Step 4.3:** Run `cd frontend && npm run test:run` (or `lint` if tests for this area do not exist yet).

- [ ] **Step 4.4:** Commit:

```bash
git commit -am "feat(frontend): types and API for receipt list fields and unified filters"
```

---

## Task 5: `LinkReceiptSearchModal` component

**Files:**
- Create: `frontend/components/LinkReceiptSearchModal.tsx`
- Reference: `frontend/components/LinkOperationsModal.tsx`, `frontend/lib/api.ts` (`listReceipts`, `linkBankToReceipt`, `linkCashToReceipt`)

- [ ] **Step 5.1:** Implement props:

```ts
type Props = {
  open: boolean;
  onClose: () => void;
  anchorType: "bank" | "cash";
  transactionId: number;
  /** Signed amount as on the transaction row; use abs() for total_* filters */
  amount: number;
  onLinked: () => void;
};
```

- [ ] **Step 5.2:** State: `search` string, initialized to `Math.abs(amount).toFixed(2)` (or locale-consistent formatting used elsewhere, e.g. `formatAmountForSearch` helper). On `open`, reset `search` to that prefill.

- [ ] **Step 5.3:** `useQuery` when `open`: `listReceipts({ search: search || undefined, total_min, total_max: Math.abs(amount), limit: 40, sort_by: "date", sort_dir: "desc" })` — set both `total_min` and `total_max` to `Math.abs(amount)` for exact OR window per product choice (spec: exact |amount| for prefill; keep both equal).

- [ ] **Step 5.4:** Row actions per spec B; `linkBankToReceipt(transactionId, receipt_transaction_id!)` or cash variant. Invalidate queries: same keys as existing link flows in `bank-transactions/page.tsx` (copy `queryClient.invalidateQueries` from existing `linkMutation`).

- [ ] **Step 5.5:** Commit:

```bash
git add frontend/components/LinkReceiptSearchModal.tsx
git commit -m "feat(frontend): LinkReceiptSearchModal for manual receipt linking"
```

---

## Task 6: `LinkTransactionSearchModal` component

**Files:**
- Create: `frontend/components/LinkTransactionSearchModal.tsx`

- [ ] **Step 6.1:** Props:

```ts
type Props = {
  open: boolean;
  onClose: () => void;
  scanId: number;
  receiptTransactionId: number;
  receiptTotal: number; // positive total from paragon
  onLinked: () => void;
};
```

- [ ] **Step 6.2:** `useQuery`: `listUnifiedTransactions({ search, exclude_receipt: true, abs_amount: Math.abs(receiptTotal), limit: 40, sort_by: "date", sort_dir: "desc" })` with `enabled: open && receiptTransactionId > 0`.

- [ ] **Step 6.3:** Row UI: branch on `row.has_receipt` and `row.receipt_scan_id` vs `scanId` as in spec. **Powiąż** calls the correct link API: if `row.source_type === "bank"`, `linkBankToReceipt(row.id, receiptTransactionId)`; if cash, `linkCashToReceipt(row.id, receiptTransactionId)`.

- [ ] **Step 6.4:** Commit:

```bash
git add frontend/components/LinkTransactionSearchModal.tsx
git commit -m "feat(frontend): LinkTransactionSearchModal for manual transaction linking"
```

---

## Task 7: Wire modals into six UI surfaces

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx`, `frontend/app/bank-transactions/[id]/page.tsx`
- Modify: `frontend/app/cash-transactions/page.tsx`, `frontend/app/cash-transactions/[id]/page.tsx`
- Modify: `frontend/app/receipts/page.tsx` (`ExpandedReceiptRow` and/or parent for modal state)
- Modify: `frontend/app/receipts/[id]/page.tsx`

- [ ] **Step 7.1:** For each file, add `useState` for modal open, a secondary button (label e.g. „Wyszukaj paragon…” / „Wyszukaj transakcję…”), and render the modal with props from current row/detail.

- [ ] **Step 7.2:** Ensure `onLinked` closes modal and invalidates necessary React Query keys (mirror existing mutations in the same file).

- [ ] **Step 7.3:** For `ExpandedReceiptRow` when `receipt_transaction_id` is null: disable the transaction search button or show helper text; do not call link APIs without `receipt_transaction_id`.

- [ ] **Step 7.4:** Run `cd frontend && npm run lint` and `npm run build` (or project’s quality gate from `.cursor/rules/90-quality-gates.mdc` if stricter).

- [ ] **Step 7.5:** Commit:

```bash
git commit -am "feat(frontend): wire link search modals on bank, cash, and receipt pages"
```

---

## Task 8: Frontend version bump (MINOR)

**Files:**
- `frontend/package.json`, `frontend/package-lock.json`

- [ ] **Step 8.1:** Increment `"version"` MINOR (e.g. `1.5.1` → `1.6.0`), sync `package-lock.json` root and `packages[""].version` if the lockfile structure uses them.

- [ ] **Step 8.2:** Commit:

```bash
git commit -am "chore(frontend): bump version to 1.6.0"
```

---

## Task 9: Final verification

- [ ] **Step 9.1:** Backend: `cd backend && pytest tests/unit/ -q` (or full suite used in CI).

- [ ] **Step 9.2:** Frontend: `cd frontend && npm run test:run && npm run build`.

- [ ] **Step 9.3:** Manual smoke: open each modal, confirm prefill, gray rows, one successful link and one 409 path if testable.

- [ ] **Step 9.4:** Open PR from `feature/manual-receipt-tx-link-search` with reference to the spec and this plan.

---

## Self-review (plan vs spec)

| Spec requirement | Plan location |
|------------------|---------------|
| One search field, LinkOperationsModal-like | Tasks 5–6 |
| Amount prefill transaction→receipt | Task 5 `LinkReceiptSearchModal` |
| Amount prefill receipt→transactions | Task 6 |
| List B: gray + labels, no “change link” | Tasks 5–6 row rules |
| Extend `listReceipts` (approach 1) | Task 1 |
| Unified `has_receipt` / `receipt_scan_id` | Task 6 |
| `total_min`/`max` + `abs_amount` | Tasks 1–2, 5–6 |
| Reuse link mutations + invalidation | Tasks 5–7 |
| Tests + SemVer + branch | Tasks 1–3, 8–9, header |

**Placeholder check:** All tasks name concrete files and parameters; no TBD in critical path.

---

## Execution handoff

**Plan complete and saved to** `docs/superpowers/plans/2026-04-24-manual-receipt-transaction-search-modals.md`. **Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration. **REQUIRED SUB-SKILL:** superpowers:subagent-driven-development.

2. **Inline execution** — tasks in this session with checkpoints. **REQUIRED SUB-SKILL:** superpowers:executing-plans.

**Which approach?**
