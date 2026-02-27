# Plan: Monorepo + Next.js Frontend

**Architecture:** Reorganize to `backend/` + `frontend/` monorepo. Add two new DB tables for confirmed transactions. Expose 7 new FastAPI endpoints. Build a Next.js 14 App Router frontend that calls the backend exclusively through **Next.js API routes** (server-side proxy using `BACKEND_URL` env var — no CORS needed).

One pre-existing bug discovered: `set_status()` in `src/repositories/receipts_scans.py` writes to a `message` column that doesn't exist in the DB schema. The new migration will add it.

---

## Phase 1 — Monorepo restructure

1. Move `src/`, `migrations/`, `input/`, `preprocessed/`, `sqlite/`, `evaluate/`, `example_*.py`, `test_*.py`, `misc/`, `Dockerfile`, `requirements.txt`, `yoyo.ini`, `yoyo.ini.example`, `.env` into a new `backend/` subdirectory. Dockerfile `COPY` directives are unchanged because build context stays at `backend/`.
2. Move `README.md`, `GROUND_TRUTH_GUIDE.md`, `IMPLEMENTATION_SUMMARY.md`, `MIGRATIONS.md`, `PRODUCTS_INTEGRATION_GUIDE.md`, `README_NORMALIZATION.md`, `VENDORS_INTEGRATION_GUIDE.md` to `backend/` (or keep at root — they're docs, not code). Update `.gitignore` to cover `frontend/node_modules`, `frontend/.next`, `backend/input/`, `backend/preprocessed/`, `backend/sqlite/`.

## Phase 2 — Database migration

3. Create `backend/migrations/20260226_01_new_tables.sql`:
   - `ALTER TABLE receipts_scans ADD COLUMN IF NOT EXISTS message TEXT` — fixes `set_status()` bug
   - `ALTER TABLE receipts_scans ADD COLUMN IF NOT EXISTS minio_object_key VARCHAR`
   - `ALTER TABLE receipts_scans DROP COLUMN IF EXISTS category`
   - `CREATE TABLE receipt_transactions` (as specified below)
   - `CREATE TABLE receipt_transaction_items` (as specified below)

```sql
ALTER TABLE receipts_scans
  ADD COLUMN IF NOT EXISTS message TEXT,
  ADD COLUMN IF NOT EXISTS minio_object_key VARCHAR,
  DROP COLUMN IF EXISTS category;

CREATE TABLE receipt_transactions (
    id              SERIAL PRIMARY KEY,
    scan_id         INTEGER NOT NULL REFERENCES receipts_scans(id),
    vendor_id       INTEGER REFERENCES vendors(id),
    raw_vendor_name VARCHAR NOT NULL,
    date            DATE NOT NULL,
    total           NUMERIC(10,2) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE receipt_transaction_items (
    id               SERIAL PRIMARY KEY,
    transaction_id   INTEGER NOT NULL REFERENCES receipt_transactions(id) ON DELETE CASCADE,
    product_id       INTEGER REFERENCES products(id),
    raw_product_name VARCHAR NOT NULL,
    category_id      INTEGER NOT NULL REFERENCES categories(id),
    quantity         NUMERIC(10,3) NOT NULL,
    unit_price       NUMERIC(10,2),
    price            NUMERIC(10,2) NOT NULL
);
```

## Phase 3 — MinIO upload in pipeline

4. Add `set_minio_key(filename: str, key: str)` to `ReceiptsScansRepository` in `backend/src/repositories/receipts_scans.py`.
5. In `_run_production()` in `backend/src/app.py`, after `preprocessing_service.preprocess_image()`: read preprocessed bytes, call `minio_service.upload_image()` with key `receipts/{scan_id}_{basename}` (get `scan_id` via existing `get_scan_id_by_filename()`), then call `receipts_scans_repository.set_minio_key(file, object_key)`.

## Phase 4 — New Pydantic models

6. Add to `backend/src/data.py`:

```python
class ReceiptScanListItem(BaseModel):
    id: int
    filename: str
    status: str
    vendor: str | None        # from result JSONB
    date: str | None
    total: float | None

class ReceiptTransactionItem(BaseModel):
    id: int
    product_id: int | None
    raw_product_name: str
    category_id: int
    quantity: float
    unit_price: float | None
    price: float

class ReceiptTransaction(BaseModel):
    id: int
    vendor_id: int | None
    raw_vendor_name: str
    date: str
    total: float
    items: list[ReceiptTransactionItem]

class ReceiptScanDetail(BaseModel):
    id: int
    filename: str
    status: str
    result: TransactionModel | None
    categories_candidates: dict | None
    minio_object_key: str | None
    transaction: ReceiptTransaction | None   # populated once confirmed

class CategoryItem(BaseModel):
    id: int
    name: str
    parent_name: str | None
    group_name: str | None

class ConfirmReceiptRequest(BaseModel):
    product_categories: dict[str, int]  # {raw_product_name: category_id}

class EvaluationRunListItem(BaseModel):
    id: int
    run_timestamp: datetime.datetime
    model_used: str
    total_files: int
    successful: int
    failed: int
    success_rate: float | None
    avg_field_completeness: float | None

class EvaluationRunDetail(EvaluationRunListItem):
    results: list[EvaluationResult]
```

## Phase 5 — Repository changes

7. **`ReceiptsScansRepository`** — add three methods:
   - `get_all() -> list[ReceiptScanListItem]`: `SELECT id, filename, status, result->>'vendor', result->>'date', result->>'total' FROM receipts_scans ORDER BY id DESC`
   - `get_by_id(scan_id: int) -> ReceiptScanDetail | None`: full row + LEFT JOIN to `receipt_transactions`/`receipt_transaction_items`
   - `set_minio_key(filename: str, key: str)`: UPDATE by filename

8. **New `backend/src/repositories/transactions.py`** — `TransactionsRepository` with:
   - `create_transaction(scan_id, vendor_id, raw_vendor_name, date, total) -> int`
   - `create_transaction_item(transaction_id, product_id, raw_product_name, category_id, quantity, unit_price, price)`
   - `get_by_scan_id(scan_id: int) -> ReceiptTransaction | None`
   - Vendor lookup helper: `SELECT vendor FROM vendors_alternative_names WHERE name = %s`
   - Product lookup helper: `SELECT product FROM products_alternative_names WHERE name = %s`

9. **`EvaluationsRepository`** — add:
   - `get_all_runs() -> list[EvaluationRunListItem]`
   - `get_run_with_results(run_id) -> EvaluationRunDetail | None`

10. **`CategoriesRepository`** — add:
    - `get_all_expense_categories() -> list[CategoryItem]`: join `categories` + self-join for `parent_name` + `category_groups` WHERE `c_type = 'expense'`

## Phase 6 — New API endpoints

11. Add to `backend/src/main.py` — wire `TransactionsRepository` in `App.__init__()`:

```
GET  /receipts                  → list[ReceiptScanListItem]
GET  /receipts/{id}             → ReceiptScanDetail
GET  /receipts/{id}/image       → StreamingResponse  (proxy MinIO bytes, media_type="image/png")
POST /receipts/{id}/confirm     → ConfirmReceiptRequest body → ReceiptScanDetail
GET  /categories                → list[CategoryItem]  (direct CategoriesRepository, not service)
GET  /evaluations               → list[EvaluationRunListItem]
GET  /evaluations/{id}          → EvaluationRunDetail
```

Confirm flow for `POST /receipts/{id}/confirm`:
1. Load scan's `result` JSONB → raw vendor name, date, total, product list
2. Look up `vendor_id` via `vendors_alternative_names WHERE name = raw_vendor_name`
3. Insert into `receipt_transactions`
4. For each product: look up `product_id` via `products_alternative_names`, insert into `receipt_transaction_items`
5. `receipts_scans.status = 'done'`

## Phase 7 — Frontend scaffold

12. Bootstrap: `npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir`. Install `shadcn/ui` (init), `@tanstack/react-query`, `zod`.
13. `frontend/app/layout.tsx` — fixed sidebar (`#f6f9fc` bg, `#635bff` accent) linking to `/`, `/receipts`, `/ground-truth`, `/evaluations`. Add `QueryClientProvider` wrapper. Inter font.
14. `frontend/.env.local`: `BACKEND_URL=http://localhost:8000` (server-side only).

## Phase 8 — Next.js API route proxy layer

15. Create `frontend/app/api/` routes that proxy to `BACKEND_URL` via server-side `fetch()`:
    - `app/api/receipts/route.ts` (GET)
    - `app/api/receipts/[id]/route.ts` (GET)
    - `app/api/receipts/[id]/image/route.ts` (GET → stream bytes back)
    - `app/api/receipts/[id]/confirm/route.ts` (POST)
    - `app/api/categories/route.ts` (GET)
    - `app/api/evaluations/route.ts` (GET)
    - `app/api/evaluations/[id]/route.ts` (GET)
    - `app/api/ground-truth/route.ts` (GET, POST)
    - `app/api/ground-truth/[id]/route.ts` (GET, PUT)

## Phase 9 — Frontend lib

16. `frontend/lib/types.ts` — Zod schemas mirroring Pydantic models:
    `ReceiptScanListItemSchema`, `ReceiptScanDetailSchema`, `ReceiptTransactionSchema`, `ReceiptTransactionItemSchema`, `CategoryItemSchema`, `EvaluationRunListItemSchema`, `EvaluationRunDetailSchema`, `GroundTruthEntrySchema`

17. `frontend/lib/api.ts` — typed async functions calling `/api/...` routes, parsing with Zod:
    `listReceipts()`, `getReceipt(id)`, `confirmReceipt(id, body)`, `listCategories()`, `listEvaluations()`, `getEvaluation(id)`, `listGroundTruth()`, `getGroundTruth(id)`, `updateGroundTruth(id, body)`

## Phase 10 — Shared components

18. `frontend/components/StatusBadge.tsx` — color-coded pill for `pending/processing/to_confirm/done/failed`
19. `frontend/components/StatCard.tsx` — card with label + big number
20. `frontend/components/DataTable.tsx` — generic table with column config
21. `frontend/components/ReceiptImageViewer.tsx` — `<img src="/api/receipts/{id}/image">` with loading skeleton
22. `frontend/components/ProductCategoryRow.tsx` — product name + `<Select>` pre-seeded with `category_candidates` sorted by score, with full category search fallback

## Phase 11 — Pages

23. `app/page.tsx` — Dashboard: 4 `StatCard`s (total / to_confirm / done / failed), recent receipts table, "Process receipts" button (`POST /api/receipts/process`), "Run evaluation" button
24. `app/receipts/page.tsx` — filterable `DataTable` by status with link to review page
25. `app/receipts/[id]/page.tsx` — two-column: `ReceiptImageViewer` (left) + vendor/date/total header + `ProductCategoryRow` list + "Confirm" button (calls `confirmReceipt()`); TanStack Query for data + optimistic update
26. `app/ground-truth/page.tsx` — table + file `<input>` upload → `POST /api/ground-truth`
27. `app/ground-truth/[id]/page.tsx` — editable transaction form → `PUT /api/ground-truth/{id}`
28. `app/evaluations/page.tsx` — runs table + "Run evaluation" button
29. `app/evaluations/[id]/page.tsx` — per-file results `DataTable` with field completeness and consistency metrics

---

## Decisions

- **Next.js API routes as proxy**: avoids CORS config, keeps `BACKEND_URL` server-side only, single place to add auth later
- **No docker-compose**: services run manually per existing workflow
- **`message TEXT` column added in migration**: fixes pre-existing silent bug in `set_status()` rather than patching the SQL
- **`set_minio_key()` keyed by filename**: consistent with how `_run_production()` iterates (has filename, not ID); `get_scan_id_by_filename()` already exists if scan_id is needed for the MinIO object key

## Verification

- Backend: `cd backend && uvicorn src.main:app --reload`, verify new endpoints at `/docs`
- Migration: `cd backend && yoyo apply`, confirm new columns and tables exist
- Frontend: `cd frontend && npm run dev`, verify `http://localhost:3000` pages render and proxy calls succeed
