# Receipt Save-Review & Auto-Confirm Waivers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users persist OCR/category edits on `to_confirm` receipts without confirming, re-run the auto-confirm gate automatically after save, and accept individual blocking reasons per scan via „Akceptuj”.

**Architecture:** Add `category_selections` and `auto_confirm_waivers` JSONB on `receipts_scans`. Extend pure `evaluate()` with a waiver set. New `App.save_review()` persists overrides like confirm (minus transaction), recategorizes, dry-runs the gate. `App.add_auto_confirm_waiver()` appends waivers idempotently. Existing `try_auto_confirm_receipt` loads waivers and uses `category_selections` when force-confirming. Frontend: „Zapisz poprawki”, panel reasons with „Akceptuj”, hydrate `selections` from `category_selections`.

**Tech Stack:** Python 3.11 / FastAPI / Pydantic v2 / psycopg2 / Yoyo; Next.js 14 / TypeScript / Zod / TanStack Query / Vitest.

**Spec:** `docs/superpowers/specs/2026-10-01-receipt-save-review-waivers-design.md`

## Global Constraints

- All user-facing strings in Polish (UI copy and `reason.message`).
- Backend: parameterized SQL; Pydantic in `backend/src/data.py`; routes in `backend/src/main.py` with `response_model=`.
- Every new/changed endpoint: `main.py`, `data.py`, `frontend/app/api/.../route.ts`, `frontend/lib/api.ts`, `frontend/lib/types.ts`.
- Frontend: UI from `frontend/components/ui/index.ts`; errors via `MutationErrorNotice` / `QueryErrorNotice`.
- Tests: `@pytest.mark.unit` / `@pytest.mark.integration`, AAA comments; App unit tests via `make_app()` from `tests/unit/conftest.py`.
- Never read/modify `.env`, `backend/yoyo.ini`.
- Versions at end: **MINOR** — backend `1.11.1 → 1.12.0`, frontend `1.10.1 → 1.11.0` (independent).

## Commands

- Backend unit: `cd backend && ../venv/bin/python -m pytest tests/unit -m unit -q --no-cov`
- Backend file: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_auto_confirm.py -q --no-cov`
- Backend integration: `cd backend && ../venv/bin/python -m pytest tests/integration/test_save_review_routes.py -q --no-cov`
- Frontend: `cd frontend && npm run test:run && npm run lint`

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/migrations/20261001_01_receipts-scans-save-review.sql` | create | `category_selections`, `auto_confirm_waivers` JSONB |
| `backend/tests/integration/test_save_review_migrations.py` | create | Column presence |
| `backend/src/services/receipt_auto_confirm.py` | modify | `evaluate(..., waivers=)` + `waiver_key()` helper |
| `backend/tests/unit/test_receipt_auto_confirm.py` | modify | Waiver tests |
| `backend/src/data.py` | modify | Models + `ReceiptScanDetail` fields |
| `backend/src/repositories/receipts_scans.py` | modify | Read/write new columns, clear on reopen |
| `backend/tests/unit/test_receipts_scans_save_review.py` | create | Repo unit tests |
| `backend/src/app.py` | modify | `save_review`, `add_auto_confirm_waiver`, waiver-aware dry-run / confirm |
| `backend/tests/unit/test_app_save_review.py` | create | App save + waiver |
| `backend/tests/unit/test_app_rescore.py` | modify | `try_auto_confirm` with waivers if needed |
| `backend/src/main.py` | modify | Two POST routes |
| `backend/tests/integration/test_save_review_routes.py` | create | HTTP tests |
| `frontend/lib/types.ts` | modify | Zod + detail fields |
| `frontend/lib/api.ts` | modify | `saveReceiptReview`, `addAutoConfirmWaiver` |
| `frontend/app/api/receipts/[id]/save-review/route.ts` | create | Proxy |
| `frontend/app/api/receipts/[id]/auto-confirm-waiver/route.ts` | create | Proxy |
| `frontend/components/AutoConfirmReasonsPanel.tsx` | modify | „Akceptuj”, waived styling |
| `frontend/components/AutoConfirmReasonsPanel.test.tsx` | modify | Button + waived |
| `frontend/app/receipts/[id]/page.tsx` | modify | Zapisz poprawki, load selections, waiver handler |
| `backend/src/version.py`, `frontend/package.json`, `frontend/package-lock.json` | modify | Semver MINOR |

---

### Task 1: Migration + integration test

**Files:**
- Create: `backend/migrations/20261001_01_receipts-scans-save-review.sql`
- Create: `backend/tests/integration/test_save_review_migrations.py`

**Interfaces:**
- Produces: columns `receipts_scans.category_selections JSONB NULL`, `receipts_scans.auto_confirm_waivers JSONB NULL`.

- [ ] **Step 1: Write migration**

```sql
-- depends: 20260930_05_prompt-analytics-auto-confirm-reverted

ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS category_selections JSONB,
    ADD COLUMN IF NOT EXISTS auto_confirm_waivers JSONB;
```

- [ ] **Step 2: Write failing integration test**

```python
# backend/tests/integration/test_save_review_migrations.py
import pytest
import psycopg2


def _connect(pg):
    return psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )


@pytest.mark.integration
def test_receipts_scans_has_save_review_columns(migrated_db):
    conn = _connect(migrated_db)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'receipts_scans' "
            "AND column_name IN ('category_selections', 'auto_confirm_waivers')"
        )
        columns = {row[0] for row in cur.fetchall()}
    conn.close()
    assert columns == {"category_selections", "auto_confirm_waivers"}
```

- [ ] **Step 3: Run test**

Run: `cd backend && ../venv/bin/python -m pytest tests/integration/test_save_review_migrations.py -q --no-cov`  
Expected: PASS (after migration applied via `migrated_db` fixture).

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/20261001_01_receipts-scans-save-review.sql backend/tests/integration/test_save_review_migrations.py
git commit -m "feat(db): category_selections and auto_confirm_waivers on receipts_scans"
```

---

### Task 2: Waiver-aware `evaluate()`

**Files:**
- Modify: `backend/src/services/receipt_auto_confirm.py`
- Modify: `backend/tests/unit/test_receipt_auto_confirm.py`

**Interfaces:**
- Produces:
  - `def waiver_key(code: str, product_name: str | None = None) -> tuple[str, str | None]:`
  - `def evaluate(..., waivers: frozenset[tuple[str, str | None]] | None = None) -> AutoConfirmDecision`
  - Matching: `sum_mismatch` / `evaluation_error` / `confirm_failed` → key `(code, None)`; `low_confidence` / `no_category` → `(code, raw_product_name)`.

- [ ] **Step 1: Write failing tests**

```python
# Add to backend/tests/unit/test_receipt_auto_confirm.py
from src.services.receipt_auto_confirm import evaluate, waiver_key, AutoConfirmSettings, ProductResolution, SOURCE_AI

@pytest.mark.unit
def test_waiver_low_confidence_per_product_unblocks():
    tx = _tx()  # existing helper in file
    resolutions = [ProductResolution("RĘKAWICZKI", 1, "Rękawiczki", 5, "Inne", SOURCE_AI, 0.85, 0)]
    waivers = frozenset({waiver_key("low_confidence", "RĘKAWICZKI")})
    decision = evaluate(tx, resolutions, False, SETTINGS, waivers=waivers)
    assert decision.ok is True
    assert all(not r.blocking for r in decision.reasons)


@pytest.mark.unit
def test_waiver_sum_mismatch_global():
    tx = _tx_mismatch()  # products sum != total — add helper or inline
    resolutions = [_resolution_for(tx)]
    waivers = frozenset({waiver_key("sum_mismatch")})
    decision = evaluate(tx, resolutions, False, SETTINGS, waivers=waivers)
    assert decision.ok is True
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_auto_confirm.py::test_waiver_low_confidence_per_product_unblocks -q --no-cov`

- [ ] **Step 3: Implement**

In `receipt_auto_confirm.py`, after each `reasons.append(...)`, if `waivers` contains matching key, set `blocking=False` on that reason (or rebuild reason with blocking false). Recompute `ok = not any(r.blocking for r in reasons)`.

```python
def waiver_key(code: str, product_name: str | None = None) -> tuple[str, str | None]:
    if code in ("low_confidence", "no_category"):
        return (code, product_name)
    return (code, None)


def _is_waived(code: str, product_name: str | None, waivers: frozenset[tuple[str, str | None]] | None) -> bool:
    if not waivers:
        return False
    return waiver_key(code, product_name) in waivers
```

Apply in loops when appending reasons (pass `name` for product-scoped codes).

- [ ] **Step 4: Run full unit file — PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/receipt_auto_confirm.py backend/tests/unit/test_receipt_auto_confirm.py
git commit -m "feat: auto-confirm evaluate respects per-scan waivers"
```

---

### Task 3: Repository + Pydantic models

**Files:**
- Modify: `backend/src/data.py`
- Modify: `backend/src/repositories/receipts_scans.py`
- Create: `backend/tests/unit/test_receipts_scans_save_review.py`

**Interfaces:**
- Produces:
  - `AutoConfirmWaiverItem(code: str, product_name: str | None = None)`
  - `AutoConfirmWaiverRequest(code: str, product_name: str | None = None)`
  - `SaveReviewResponse(receipt: ReceiptScanDetail, auto_confirm: SingleAutoConfirmResult)`
  - `ReceiptScanDetail.category_selections: dict[str, int] | None`, `auto_confirm_waivers: list[AutoConfirmWaiverItem] | None`
  - `ReceiptsScansRepository.set_category_selections(scan_id, mapping) -> bool`
  - `ReceiptsScansRepository.append_auto_confirm_waiver(scan_id, item) -> bool` (idempotent)
  - `ReceiptsScansRepository.clear_save_review_fields(scan_id) -> bool`
  - `get_by_id` SELECT extended with columns 12–13; parse JSON

- [ ] **Step 1: Add Pydantic models** in `data.py` (after `SingleAutoConfirmResult`).

- [ ] **Step 2: Write repo unit tests** (mock cursor pattern from `test_receipts_scans_auto_confirm.py`):

```python
@pytest.mark.unit
def test_append_auto_confirm_waiver_idempotent():
    # second append same code+product_name does not duplicate JSON array
    ...
```

- [ ] **Step 3: Implement repository methods** — read/write JSONB with `psycopg2.extras.Json`; `append` reads array, appends if missing key, writes back.

- [ ] **Step 4: Extend `get_by_id` SQL** and `ReceiptScanDetail` construction.

- [ ] **Step 5: Run** `pytest tests/unit/test_receipts_scans_save_review.py -q --no-cov`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: persist category_selections and auto_confirm_waivers"
```

---

### Task 4: App — `save_review` and waiver + wire `evaluate` waivers

**Files:**
- Modify: `backend/src/app.py`
- Create: `backend/tests/unit/test_app_save_review.py`

**Interfaces:**
- Produces:
  - `def _waivers_frozen(detail: ReceiptScanDetail) -> frozenset[tuple[str, str | None]]`
  - `def _dry_run_gate(self, scan_id: int, transaction_model: TransactionModel) -> SingleAutoConfirmResult` — categorize + `evaluate(waivers=...)` + set reasons, no `_apply_auto_confirm`
  - `def save_review(self, scan_id: int, request: ConfirmReceiptRequest) -> SaveReviewResponse | None`
  - `def add_auto_confirm_waiver(self, scan_id: int, request: AutoConfirmWaiverRequest) -> SaveReviewResponse | None`

**`save_review` algorithm:**

1. Load detail; return `None` if not `to_confirm` or no `result`.
2. Extract OCR override logic from `confirm_receipt` (lines ~636–661) into shared helper `_apply_review_overrides(scan_id, detail, request) -> TransactionModel` **without** creating transaction — persists `result`, upserts normalized vendor/product names.
3. `set_category_selections(scan_id, request.product_categories)`.
4. Call `_dry_run_gate` with updated `TransactionModel`.
5. Return `SaveReviewResponse(receipt=get_receipt_by_id(scan_id), auto_confirm=...)`.

**Modify `_rescore_one_pending_scan` / `try_auto_confirm_receipt`:**

- Load waivers from detail; pass to `evaluate(..., waivers=_waivers_frozen(detail))`.
- When `dry_run=False` and confirming: if `detail.category_selections`, build `ConfirmReceiptRequest.product_categories` from that dict (merged with resolution normalized names) instead of only resolution category ids.

**`add_auto_confirm_waiver`:** validate `to_confirm`; `append_auto_confirm_waiver`; `_dry_run_gate`; return `SaveReviewResponse`.

**Reopen:** after `set_status_to_confirm`, call `clear_save_review_fields(scan_id)`.

**Manual confirm success:** optional `clear_save_review_fields` (same as clearing selections).

- [ ] **Step 1: Write failing App tests**

```python
# backend/tests/unit/test_app_save_review.py
@pytest.mark.unit
def test_save_review_persists_result_and_dry_runs_without_confirm():
    app = make_app(...)
    detail = ReceiptScanDetail(..., status="to_confirm", result=_tx())
    app.receipts_scans_repository.get_by_id.return_value = detail
    app._dry_run_gate = MagicMock(return_value=SingleAutoConfirmResult(dry_run=True, ok=True, confirmed=False, reasons=[]))
    out = app.save_review(1, ConfirmReceiptRequest(product_categories={"A": 1}, products=[...]))
    assert out is not None
    app.receipts_scans_repository.set_result_by_id.assert_called()
    app.receipts_scans_repository.set_category_selections.assert_called()
    app._apply_auto_confirm.assert_not_called()  # if exposed via mock on _rescore path
```

- [ ] **Step 2: Implement** — refactor shared override helper from `confirm_receipt` to avoid duplication.

- [ ] **Step 3: Test waiver endpoint logic** `add_auto_confirm_waiver` calls append + dry run.

- [ ] **Step 4: Test reopen clears fields** (mock `clear_save_review_fields`).

- [ ] **Step 5: Run** `pytest tests/unit/test_app_save_review.py tests/unit/test_app_rescore.py -q --no-cov`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: save-review and waiver flow on App"
```

---

### Task 5: HTTP routes + integration tests

**Files:**
- Modify: `backend/src/main.py`
- Create: `backend/tests/integration/test_save_review_routes.py`

**Interfaces:**
- Produces:
  - `POST /receipts/{scan_id}/save-review` → `SaveReviewResponse`
  - `POST /receipts/{scan_id}/auto-confirm-waiver` → `SaveReviewResponse`

- [ ] **Step 1: Add routes** (mirror `auto_confirm_receipt` / `confirm_receipt` App lifecycle with `dispose()`).

- [ ] **Step 2: Integration tests** with `patch("src.main.App")`:

```python
@pytest.mark.integration
def test_save_review_returns_receipt_and_auto_confirm(client):
    ...

@pytest.mark.integration
def test_waiver_not_found_when_not_pending(client):
    ...
```

- [ ] **Step 3: Run integration file**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: HTTP save-review and auto-confirm-waiver routes"
```

---

### Task 6: Frontend types, API, proxy routes

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/api/receipts/[id]/save-review/route.ts`
- Create: `frontend/app/api/receipts/[id]/auto-confirm-waiver/route.ts`
- Modify: `frontend/lib/receiptAutoConfirmSchema.test.ts`

**Interfaces:**
- Consumes: backend JSON shapes for `SaveReviewResponse`, `AutoConfirmWaiverRequest`, extended `ReceiptScanDetail`.

- [ ] **Step 1: Zod schemas**

```typescript
export const AutoConfirmWaiverItemSchema = z.object({
  code: z.string(),
  product_name: z.string().nullable().optional(),
});

export const SaveReviewResponseSchema = z.object({
  receipt: ReceiptScanDetailSchema,
  auto_confirm: SingleAutoConfirmResultSchema,
});
```

Add to `ReceiptScanDetailSchema`: `category_selections: z.record(z.string(), z.number()).nullable().optional()`, `auto_confirm_waivers: z.array(AutoConfirmWaiverItemSchema).nullable().optional()`.

Optional on `AutoConfirmReasonSchema`: `waived: z.boolean().optional()` if BE adds it; otherwise FE derives waived by matching `auto_confirm_waivers` to reason code + product substring.

- [ ] **Step 2: API functions**

```typescript
export async function saveReceiptReview(id: number, body: ConfirmReceiptRequest): Promise<SaveReviewResponse> { ... }

export async function addAutoConfirmWaiver(
  id: number,
  body: { code: string; product_name?: string | null }
): Promise<SaveReviewResponse> { ... }
```

- [ ] **Step 3: Proxy routes** — `proxyPost` like `auto-confirm/route.ts`.

- [ ] **Step 4: Extend Vitest schema test**

- [ ] **Step 5: Run** `cd frontend && npm run test:run -- lib/receiptAutoConfirmSchema.test.ts`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(frontend): API contract for save-review and waivers"
```

---

### Task 7: UI — panel „Akceptuj” + „Zapisz poprawki”

**Files:**
- Modify: `frontend/components/AutoConfirmReasonsPanel.tsx`
- Modify: `frontend/components/AutoConfirmReasonsPanel.test.tsx`
- Modify: `frontend/app/receipts/[id]/page.tsx`

**Interfaces:**
- Consumes: `saveReceiptReview`, `addAutoConfirmWaiver`, `getSelection()` map for `product_categories` payload.

- [ ] **Step 1: Extend panel props**

```typescript
type Props = {
  reasons: AutoConfirmReason[];
  waivers?: AutoConfirmWaiverItem[];
  onAccept?: (payload: { code: string; product_name?: string | null }) => void;
  acceptPending?: boolean;
};
```

Render **„Akceptuj”** only when `reason.blocking && !isWaived(reason)`. Waived lines: muted + label „Zaakceptowano” (no second button).

Parse `product_name` for waiver API from reason message is fragile — **prefer** backend adding optional `product_name` on `AutoConfirmReasonItem` when code is product-scoped (Task 4 small addition: set field in `evaluate` reasons). If not added, pass `product_name` from panel context: parent passes `productNameByReasonIndex` or extend API reasons with `product_name` field in `to_dict()`.

**Recommended:** add optional `product_name: str | None` to `AutoConfirmReason` dataclass / `AutoConfirmReasonItem` for `low_confidence` and `no_category` only.

- [ ] **Step 2: Panel tests** — click „Akceptuj” calls `onAccept` with code.

- [ ] **Step 3: Page — hydrate selections**

```typescript
useEffect(() => {
  if (scan?.category_selections) {
    setSelections(scan.category_selections);
  }
}, [scan?.category_selections]);
```

- [ ] **Step 4: Build confirm payload helper** (shared by confirm + save):

```typescript
function buildReviewPayload(): ConfirmReceiptRequest {
  const resolved: Record<string, number> = {};
  for (const p of products) {
    const sel = getSelection(p.name);
    if (sel !== undefined) resolved[p.name] = sel;
  }
  return { product_categories: resolved, vendor: ..., products: ..., normalized_... };
}
```

- [ ] **Step 5: `saveReviewMutation`** — calls `saveReceiptReview`; onSuccess: set receipt, apply `auto_confirm` to `autoConfirmEligible`, invalidate `receipts`.

- [ ] **Step 6: `waiverMutation`** — `addAutoConfirmWaiver`; onSuccess same as save.

- [ ] **Step 7: Buttons** — „Zapisz poprawki” (`variant="secondary"`) above/beside „Potwierdź paragon”; wire `MutationErrorNotice`.

- [ ] **Step 8: Run** `npm run test:run && npm run lint`

- [ ] **Step 9: Commit**

```bash
git commit -m "feat(frontend): save-review UI and Akceptuj waivers"
```

---

### Task 8: `product_name` on reasons (if not done in Task 4)

**Files:**
- Modify: `backend/src/services/receipt_auto_confirm.py` (`AutoConfirmReason` + `to_dict`)
- Modify: `backend/src/data.py` (`AutoConfirmReasonItem.product_name` optional)
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Add field to reasons** for product-scoped codes.

- [ ] **Step 2: Update tests** that assert reason dict shape.

- [ ] **Step 3: Commit** `feat: product_name on auto-confirm reasons for waiver UI`

---

### Task 9: Version bump + docs touch

**Files:**
- Modify: `backend/src/version.py` → `1.12.0`
- Modify: `frontend/package.json` + `package-lock.json` → `1.11.0`
- Modify: `context.md` or `CLAUDE.md` Recent Changes (one line each)

- [ ] **Step 1: Bump versions**

- [ ] **Step 2: Run full backend unit suite** `pytest tests/unit -m unit -q --no-cov`

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: bump BE 1.12.0 / FE 1.11.0 for save-review waivers"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Migration columns | 1 |
| evaluate + waivers | 2 |
| save-review endpoint | 4, 5 |
| waiver endpoint + dry-run response | 4, 5 |
| category_selections persist + UI hydrate | 3, 7 |
| Reopen clears fields | 4 |
| try_auto_confirm uses waivers + selections on confirm | 4 |
| „Akceptuj” copy | 7 |
| Auto dry-run after save | 4, 7 |
| Polish UI | 7 |
| MINOR semver | 9 |

## Self-review notes

- `product_name` on reason objects avoids parsing Polish messages in FE (Task 8).
- Shared `_apply_review_overrides` prevents drift vs `confirm_receipt`.
- `SaveReviewResponse` always includes fresh `receipt` so FE single source after save/waiver.
