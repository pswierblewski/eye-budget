# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-04-17

## Co to jest
Aplikacja do budżetu domowego: OCR paragonów (PaddleOCR + OpenAI), transakcje bankowe/gotówkowe, kategoryzacja i przegląd danych.
Dla agenta: zwięzły opis repo; szczegóły frontend/backend w `frontend/AGENTS.md` i `backend/AGENTS.md`.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix, TanStack Query, Zod, recharts, Pusher/Soketi
- Backend: FastAPI, Pydantic v2, psycopg2 (SQL bez ORM), Yoyo, Celery + Redis, MinIO, PaddleOCR / OpenAI
- Infra: PostgreSQL, MinIO, Redis, Soketi; `docker-compose.yml` — Redis, Soketi, backend, worker (bez serwisu Next w tym pliku)

## Struktura
- `frontend/app/` — strony + proxy `app/api/*/route.ts`
- `frontend/components/ui/` — primitives (`index.ts` przed nowym UI)
- `backend/src/` — `main.py` (route’y), `data.py` (Pydantic), `services/`, `repositories/`, `tasks/`
- `backend/migrations/` — Yoyo SQL
- `specs/` (feature: spec, plan, tasks), `docs/` — notatki poza specs

## Jak pracować
- Frontend: `cd frontend && npm install && npm run dev` → :3000; `npm run lint`
- Backend: venv, `pip install -r requirements.txt`, `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` (README bywa 8080 — zgodnie z `.env` / `BACKEND_URL`)
- Docker: `docker compose up` — backend na hoście **:8001** (8001→8000 w kontenerze)
- DB: `cd backend && yoyo apply`; testy: `python -m pytest` (`tests/unit/`, `tests/integration/`), coverage: `.coveragerc` → `source = src`
- UI: copy po polsku

## Kluczowe decyzje
- SQL przez psycopg2 z parametrami `%s` — bez ORM
- HTTP: klient → `lib/api.ts` → proxy Next → FastAPI; `App()` na request w `main.py` + `dispose()` w `finally`
- Zmiana endpointu: `main.py` + `data.py` + `app/api/.../route.ts` + `lib/api.ts` + `lib/types.ts`
- Ostatnio: rozbudowa testów jednostkowych repozytoriów i dostosowanie coverage pod `src/`

## Gotchas i ograniczenia
- Nie czytaj ani nie zmieniaj `.env`, `backend/.env` ani `backend/yoyo.ini` (sekrety)
- Różne porty backendu (8000 / 8080 / 8001 przy Dockerze) — sprawdź przed debugowaniem CORS/proxy
- `frontend/package.json` nie definiuje `npm test` — nie zakładaj skryptu testów po stronie Next bez sprawdzenia
- Nowe UI primitives tylko po konsultacji z `components/ui/index.ts`; nowe katalogi top-level — po uzgodnieniu
