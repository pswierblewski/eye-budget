# eye-budget Backend — AI Agent README

## TL;DR — Highest-Priority Rules

1. **All routes live in `src/main.py`** — do not create separate router files.
2. **`App()` is instantiated per request** in a `try/finally` block; always call `my_app.dispose()`.
3. **All Pydantic models live in `src/data.py`** — never define models inline in handlers.
4. **Every route must declare `response_model=`** — do not return raw dicts.
5. **SQL is raw parameterized** (`%s` placeholders via psycopg2) — no ORM, no f-strings for values.
6. **`conn.commit()` on success, `conn.rollback()` in `except`** — never skip either.
7. **Migrations: one concern per file**, `IF NOT EXISTS` guards, `depends:` header.
8. **Services use constructor injection** — no globals, no `App()` inside a service.
9. **Background tasks (Celery) follow the same `App()`/`dispose()` pattern** and push Pusher events.
10. **No hardcoded credentials** — always read from `os.environ`.

Full rules: `.cursor/rules/backend/` (20–22 series).

## Stack

| | |
|---|---|
| Framework | FastAPI |
| Language | Python 3.x |
| Validation | Pydantic v2 |
| Database | PostgreSQL via psycopg2 (raw SQL, no ORM) |
| Migrations | Yoyo (`yoyo apply`) |
| Background jobs | Celery + Redis |
| Storage | MinIO (S3-compatible) |
| AI / LLM | OpenAI (tool/function calls using Pydantic schemas) |
| Real-time | Pusher / Soketi |

## Directory Layout

```
backend/
├── src/
│   ├── main.py             # All FastAPI routes in a single file (no APIRouter)
│   ├── app.py              # App class — instantiated per request, wires all deps
│   ├── data.py             # All Pydantic request/response models
│   ├── celery_app.py       # Celery + Redis configuration
│   ├── db_contexts/
│   │   └── eye_budget.py   # EyeBudgetDbContext — psycopg2 connection
│   ├── repositories/       # Data access — one file per domain, raw SQL
│   ├── services/           # Business logic, LLM calls, MinIO, Pusher
│   └── tasks/              # Celery background tasks
└── migrations/             # Yoyo SQL migration files (YYYYMMDD_XX_description.sql)
```

## Run

```bash
# API server (from repo root)
cd backend && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker
cd backend && celery -A src.celery_app worker --loglevel=info --concurrency=2

# Apply DB migrations
cd backend && yoyo apply    # requires yoyo.ini with valid DB credentials
```

## Request Lifecycle

```
HTTP request
  └─ route handler in src/main.py
       └─ my_app = App()
            ├─ EyeBudgetDbContext (psycopg2 connection)
            ├─ Repositories (injected with db_context)
            └─ Services (injected with repositories / other services)
       └─ try:
            my_app.<method>(...)
          finally:
            my_app.dispose()  # closes DB, releases resources
```

## Layering

| Layer | Location | Responsibility |
|---|---|---|
| HTTP | `src/main.py` | Route definitions, request parsing, `HTTPException` |
| Orchestration | `src/app.py` | `App` class — wires and exposes high-level methods |
| Service | `src/services/` | Business logic, LLM, external APIs |
| Repository | `src/repositories/` | SQL queries, DB reads/writes |
| DB context | `src/db_contexts/` | Connection creation and disposal |

## Environment Variables

See `.env.example` at the repo root for the full list.
Key vars: `POSTGRESQL_*`, `OPENAI_API_KEY`, `MINIO_*`, `REDIS_URL`, `SOKETI_*`.

## Canonical References

- `backend/src/main.py` — all route definitions, per-request App lifecycle, HTTPException patterns
- `backend/src/data.py` — all Pydantic models, naming conventions, `PaginatedResponse`
- `backend/src/app.py` — App wiring: repositories, services, dispose
- `backend/src/repositories/receipts_scans.py` — dynamic filters, JSONB, commit/rollback
- `backend/src/repositories/products.py` — simple CRUD, `ON CONFLICT`
- `backend/src/services/categories.py` — service with `build()` preloading
- `backend/src/services/ocr.py` — OpenAI tool-call pattern
- `backend/src/tasks/process_receipts.py` — Celery task with App + Pusher
- `backend/src/db_contexts/eye_budget.py` — connection creation and disposal
- `backend/migrations/20241010_01_receipts_scans.sql` — migration structure and DDL guards
- `MIGRATIONS.md` — migration workflow documentation
