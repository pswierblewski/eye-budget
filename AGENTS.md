# eye-budget — AI Agent README

## Repo Map

```
eye-budget/                     # monorepo root (no monorepo tool — just two independent apps)
├── frontend/                   # Next.js 14, App Router, npm, TypeScript strict
│   ├── app/                    # page routes + thin API proxy route handlers
│   ├── components/             # feature-level React components
│   │   └── ui/                 # design-system primitives (Button, Input, Modal, …)
│   └── lib/                    # api.ts · types.ts · proxy.ts · utils.ts · pusher.ts
├── backend/                    # FastAPI + Celery worker
│   ├── src/
│   │   ├── main.py             # all FastAPI routes (single file, no routers)
│   │   ├── app.py              # App orchestration class — wires services + repositories
│   │   ├── data.py             # all Pydantic request/response models
│   │   ├── repositories/       # data access — raw SQL via psycopg2
│   │   ├── services/           # business logic, LLM calls (OpenAI), MinIO, Pusher
│   │   ├── tasks/              # Celery background tasks
│   │   └── db_contexts/        # PostgreSQL connection management
│   └── migrations/             # Yoyo SQL migration files
├── docker-compose.yml          # Redis · Soketi · backend · celery-worker
├── .env                        # local secrets — NEVER read or modify
├── .env.example                # safe template — use this as reference
└── README.md
```

## Key Technologies

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript strict, Tailwind CSS, Radix UI |
| State / data | @tanstack/react-query, Zod |
| Real-time | Pusher/Soketi via `lib/pusher.ts` |
| Backend | FastAPI, Pydantic, uvicorn |
| Database | PostgreSQL · psycopg2 (raw SQL, no ORM) |
| Migrations | Yoyo (`yoyo apply`) |
| Background jobs | Celery + Redis |
| Storage | MinIO (S3-compatible) |
| AI | OpenAI (tool calls via Pydantic schemas) |

## Dev Commands

```bash
# Frontend
cd frontend && npm run dev          # http://localhost:3000
cd frontend && npm run build
cd frontend && npm run lint

# Backend (from repo root, with .env loaded)
cd backend && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
cd backend && celery -A src.celery_app worker --loglevel=info

# Migrations (from backend/)
cd backend && yoyo apply            # requires yoyo.ini with DB credentials

# Full stack
docker compose up                   # Redis + Soketi + backend + celery-worker
```

## Environment

- **Root `.env`** — DB, OpenAI, MinIO, Redis, Soketi credentials. **Never modify or read** in AI sessions.
- **`.env.example`** — safe template; use this to understand what variables exist.
- **`frontend/.env.local`** — `NEXT_PUBLIC_*` Pusher vars and `BACKEND_URL` (defaults to `http://localhost:8080`).
- Backend reads env vars directly via `os.environ` / `python-dotenv`.

## Request Flow

```
Browser → Next.js page ("use client")
       → useQuery/useMutation → lib/api.ts
       → fetch /api/... (Next.js API route handler)
       → lib/proxy.ts (proxyGet / proxyPost / …)
       → FastAPI backend (port 8080 in docker, 8000 direct)
       → App() → service → repository → PostgreSQL
```

## Ground Rules for AI

1. **Never read or modify `.env`** or `backend/yoyo.ini` (contains real DB credentials).
2. **Never create top-level directories** without discussing with the user first.
3. **Keep frontend and backend strictly separated** — no Python patterns in TypeScript files.
4. **Every API change must touch both sides:** backend endpoint → frontend proxy route (`app/api/`) → `lib/api.ts` → `lib/types.ts`.
5. **Run migrations before adding columns.** Migration files live in `backend/migrations/`, named `YYYYMMDD_XX_description.sql`.
6. **No new UI primitives** until you have checked `frontend/components/ui/index.ts` — the component likely already exists.
7. **UI copy is in Polish** — the app targets Polish users.
