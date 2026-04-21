# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-04-21

## Co to jest
Aplikacja do budżetu domowego: OCR paragonów (PaddleOCR + OpenAI), transakcje bankowe/gotówkowe, kategoryzacja i przegląd danych.
Dla agenta: zwięzły opis repo; szczegóły frontend/backend w `frontend/AGENTS.md` i `backend/AGENTS.md`.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix, TanStack Query, Zod, recharts, Pusher/Soketi; testy: **Vitest**, React Testing Library, jsdom (`npm run test` / `test:run`)
- Backend: FastAPI, Pydantic v2, psycopg2 (SQL bez ORM), Yoyo, Celery + Redis, MinIO, PaddleOCR / OpenAI
- Infra: PostgreSQL, MinIO, Redis, Soketi; `docker-compose.yml` — Redis, Soketi, backend, worker (bez serwisu Next w tym pliku)
- Wersje produktu: **frontend** `frontend/package.json` (+ spójny root w `frontend/package-lock.json`); **backend** `backend/src/version.py`; opis kontraktu: `specs/006-semantic-versioning/`

## Struktura
- `frontend/app/` — strony + proxy `app/api/*/route.ts`
- `frontend/components/ui/` — primitives (`index.ts` przed nowym UI)
- `backend/src/` — `main.py` (route’y), `data.py` (Pydantic), `services/`, `repositories/`, `tasks/`, `version.py`
- `backend/migrations/` — Yoyo SQL
- `specs/` (feature: spec, plan, tasks), `docs/` — notatki poza specs

## Jak pracować
- Frontend: `cd frontend && npm install && npm run dev` → :3000; `npm run lint`; testy: `npm run test:run`
- Backend: venv (np. `backend/.venv311`), `pip install -r requirements.txt` (+ test deps); `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` (README bywa 8080 — zgodnie z `.env` / `BACKEND_URL`)
- Docker: `docker compose up` — backend na hoście **:8001** (8001→8000 w kontenerze)
- DB: `cd backend && yoyo apply`; testy: `.venv/bin/python -m pytest` (`tests/unit/`, `tests/integration/`), coverage: `.coveragerc` → `source = src`
- UI: copy po polsku

## Kluczowe decyzje
- SQL przez psycopg2 z parametrami `%s` — bez ORM
- HTTP: klient → `lib/api.ts` → proxy Next → FastAPI; `App()` na request w `main.py` + `dispose()` w `finally`
- Zmiana endpointu: `main.py` + `data.py` + `app/api/.../route.ts` + `lib/api.ts` + `lib/types.ts`
- **Wersjonowanie przy każdym ukończonym feature:** podnieś **semver** we **wszystkich** miejscach naraz: `frontend/package.json`, **oba** pola wersji root pakietu w `frontend/package-lock.json`, `backend/src/version.py`, asercja w `backend/tests/unit/test_version.py`. Zwykle **minor** (np. 1.2.0 → 1.3.0) dla nowej funkcji użytkowej, **patch** dla samych poprawek bez nowej funkcji.

## Gotchas i ograniczenia
- Nie czytaj ani nie zmieniaj `.env`, `backend/.env` ani `backend/yoyo.ini` (sekrety)
- Różne porty backendu (8000 / 8080 / 8001 przy Dockerze) — sprawdź przed debugowaniem CORS/proxy
- Nowe UI primitives tylko po konsultacji z `components/ui/index.ts`; nowe katalogi top-level — po uzgodnieniu
