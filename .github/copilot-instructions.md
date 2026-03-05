# Project Guidelines — eye-budget

Personal budget management app that processes Polish fiscal receipts via OCR (OpenAI), imports bank transactions (Pekao SA CSV), and provides a unified transaction view.

## Architecture

- **Backend**: Python 3.11 / FastAPI (`backend/src/main.py` routes, `backend/src/app.py` service locator + business logic)
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, React Query v5
- **Task queue**: Celery + Redis for OCR processing and bank categorization
- **Database**: PostgreSQL — raw SQL via psycopg2, no ORM. Migrations with yoyo (`backend/migrations/`)
- **Storage**: MinIO for receipt images
- **WebSockets**: Soketi (Pusher-compatible) for real-time task progress — no polling

Data flow: Frontend → Next.js API proxy routes (`frontend/app/api/*/route.ts` via `frontend/lib/proxy.ts`) → FastAPI backend → PostgreSQL/MinIO. Long tasks run as Celery workers pushing progress via Soketi.

- **Receipt category inheritance**: Bank/cash transactions linked to a receipt inherit categories computed on-the-fly via SQL subqueries — no separate DB column. `receipt_transaction_items.transaction_id` (not `receipt_transaction_id`) is the FK to `receipt_transactions`.

## Code Style

### Backend (Python)
- Repositories in `backend/src/repositories/` — one file per table, raw SQL with `%s` parameter binding. No ORM.
- All classes inherit `ABC` as a base marker (not for abstract methods) — follow existing pattern.
- `App` class (`backend/src/app.py`) wires all repos/services and contains business methods. Each endpoint creates `App()`, calls a method, then `dispose()`.
- Data models in `backend/src/data.py` — Pydantic v2 `BaseModel` subclasses with `Field(...)` descriptions, `StrEnum` for statuses.
- OpenAI structured output uses function calling with `model_json_schema()` from Pydantic models.
- **Category full path**: Category display names use `CONCAT_WS(' / ', cg.name, parent.name, cat.name)` via LEFT JOINs on `category_groups` and `categories` (self-join for parent). This pattern is used in all receipt category subqueries.
- **`ReceiptCategory` model**: Shared Pydantic model (`data.py`) for `{id, name, product_count}` used by `BankTransactionDetail`, `CashTransactionDetail`, and `UnifiedTransaction`. The `name` field carries the full path string.

### Frontend (TypeScript)
- Every API entity has a Zod schema + inferred type in `frontend/lib/types.ts`. Types are never manually written — always `z.infer<typeof Schema>`.
- API client (`frontend/lib/api.ts`) uses a generic `apiFetch<T>` that validates responses with Zod at runtime.
- All pages are `"use client"` with React Query for data fetching. Layout is a server component.
- UI text is in **Polish** (`Transakcje`, `Paragony`, `Szczegóły`, etc.).
- UI components: Radix primitives, Tailwind utilities inline, `clsx`/`tailwind-merge` for conditional classes.

## Build & Test

```bash
# Full stack (Docker)
docker compose up --build

# Backend (local)
cd backend && pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
celery -A src.celery_app worker --loglevel=info  # separate terminal

# Frontend (local)
cd frontend && npm install
npm run dev     # dev server :3000
npm run build   # production build
npm run lint    # ESLint

# Database migrations
yoyo apply --database postgresql://<user>:<pass>@<host>/<db> ./migrations
```

No test framework configured — only standalone scripts (`backend/test_products_simple.py`, `backend/test_vendors_simple.py`).

## Project Conventions

- **App-per-request**: Each FastAPI endpoint instantiates a fresh `App()` (opens DB connection) and calls `dispose()` in a `finally` block. Follow this pattern for new endpoints.
- **Frontend proxy pattern**: Next.js API routes (`frontend/app/api/`) are pure pass-throughs to keep `BACKEND_URL` server-side. Add matching proxy routes for new backend endpoints.
- **Monolithic route file**: All backend endpoints live in `backend/src/main.py`. All business logic in `backend/src/app.py`.
- **Status workflows**: Receipts follow `pending → processing → to_confirm → done/failed`. Bank/cash transactions: `to_confirm → done`.
- **JSONB** for OCR results and category candidates; `TEXT[]` with GIN indexes for tags; `NUMERIC(12,2)` for monetary amounts.
- **Scrollable layout**: `<main>` in `layout.tsx` uses `overflow-y-auto` (not `overflow-hidden`). New pages with tables must not add `overflow-hidden` at the page root — let the main container handle scrolling.
- **Receipt-linked category rule**: Never allow manual category edits on transactions that have a receipt link — enforce in `app.py` (passes `category_id=None` to `confirm()`) and in the frontend (replaces `CategoryDropdown` with a read-only pills list + link to the receipt page).

## Category System

- If a bank/cash transaction is linked to a receipt, `category_id` on the transaction is preserved in DB but ignored in UI — categories are derived from `receipt_transaction_items` via the link table (`receipt_bank_links` / `receipt_cash_links`).
- When a receipt link is removed, the original `category_id` is automatically restored (it was never cleared).
- `confirm()` in bank/cash repos accepts `Optional[int]` — if `None`, only sets `status='done'` without touching `category_id`.
- The unified list (`unified_transactions.py`) returns `receipt_categories` as `json_agg` for use in expanded rows; the list-column uses a separate scalar subquery for the top category only.
- List view shows top category + `+N` badge; expanded row shows full pills list (one per line, ordered by product count desc); detail page shows full pills too.

## Environment Variables

Required in `.env`: `OPENAI_API_KEY`, `MODEL`, `POSTGRESQL_*` (HOST/PORT/DB/USER/PASSWORD), `MINIO_*` (ENDPOINT/ACCESS_KEY/SECRET_KEY/BUCKET), `REDIS_URL`, `SOKETI_*`/`NEXT_PUBLIC_PUSHER_*`. See `docker-compose.yml` for service wiring.
