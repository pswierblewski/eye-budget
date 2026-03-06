# eye-budget Backend — AI Agent README

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

## Key Rules (summary — full rules in .cursor/rules/)

- All routes live in `src/main.py`. Do not create separate router files.
- `App()` is instantiated **per request** in a `try/finally` block.
- All Pydantic models live in `src/data.py`.
- SQL is raw parameterized (`%s` placeholders) — no ORM.
- Migrations: one file per concern, `IF NOT EXISTS` guards, `depends:` header.
- Background tasks return `TaskResponse(task_id=task.id)` with HTTP 202.

## Environment Variables

See `.env.example` at the repo root for the full list.
Key vars: `POSTGRESQL_*`, `OPENAI_API_KEY`, `MINIO_*`, `REDIS_URL`, `SOKETI_*`.
