# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-04-16

## Co to jest
Aplikacja do zarządzania budżetem domowym z OCR paragonów i automatyczną kategoryzacją transakcji.
Stack: Next.js 14 (frontend) + FastAPI + Celery (backend) + PostgreSQL + MinIO.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix UI, TanStack Query
- Backend: FastAPI, Pydantic, psycopg2 (raw SQL — brak ORM), Yoyo migrations, Celery + Redis
- Storage: MinIO (S3-compatible), PostgreSQL
- AI: OpenAI tool calls via Pydantic schemas
- Real-time: Pusher/Soketi

## Struktura
- `frontend/app/` — strony + proxy API route handlers
- `frontend/components/ui/` — design-system primitives (sprawdź przed tworzeniem nowych)
- `backend/src/main.py` — wszystkie FastAPI routes (jeden plik)
- `backend/src/services/` — logika biznesowa, LLM calls
- `backend/src/repositories/` — dostęp do danych (raw SQL)
- `backend/migrations/` — pliki SQL (Yoyo)
- `docker-compose.yml` — Redis, Soketi, backend, celery-worker

## Jak pracować
- Frontend: `cd frontend && npm run dev` → http://localhost:3000
- Backend: `cd backend && uvicorn src.main:app --port 8000 --reload`
- Migracje: `cd backend && yoyo apply`
- UI copy w języku polskim

## Kluczowe decyzje
- Raw SQL (psycopg2) zamiast ORM — celowy wybór
- Server Actions w Next.js zamiast osobnych API routes dla prostszych operacji
- Każda zmiana API: backend endpoint → proxy route (`app/api/`) → `lib/api.ts` → `lib/types.ts`

## Poza zakresem
- Nie czytaj ani nie modyfikuj `.env` i `backend/yoyo.ini` (prawdziwe credentials)
- Nie twórz nowych katalogów top-level bez konsultacji
- Nie dodawaj UI primitives bez sprawdzenia `frontend/components/ui/index.ts`
