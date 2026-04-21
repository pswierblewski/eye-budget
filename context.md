# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-04-21

## Co to jest
Aplikacja do budżetu domowego: OCR paragonów (PaddleOCR + OpenAI), transakcje bankowe/gotówkowe, kategoryzacja i przegląd danych.
Dla agenta: zwięzły opis repo; szczegóły frontend/backend w `frontend/AGENTS.md` i `backend/AGENTS.md`.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix, TanStack Query, Zod, recharts, Pusher/Soketi; testy: **Vitest**, React Testing Library, jsdom (`npm run test` / `test:run`)
- Backend: FastAPI, Pydantic v2, psycopg2 (SQL bez ORM), Yoyo, Celery + Redis, MinIO, PaddleOCR / OpenAI
- Infra: PostgreSQL, MinIO, Redis, Soketi; `docker-compose.yml` — Redis, Soketi, backend, worker (bez serwisu Next w tym pliku)
- Wersje produktu (**niezależne**): **frontend** — `frontend/package.json` oraz pole `version` root pakietu w `frontend/package-lock.json` (klucz główny i `packages[""]`); **backend** — `backend/src/version.py` + asercja w `backend/tests/unit/test_version.py`. Kontrakt i UI: `specs/006-semantic-versioning/`

## Struktura
- `frontend/app/` — strony + proxy `app/api/*/route.ts`
- `frontend/components/ui/` — primitives (`index.ts` przed nowym UI)
- `backend/src/` — `main.py` (route’y), `data.py` (Pydantic), `services/`, `repositories/`, `tasks/`, `version.py`, `bank_category_top.py`, `bank_inflow_salary_rules.py` (reguły pensji przed LLM)
- `backend/migrations/` — Yoyo SQL
- `specs/` oraz `docs/superpowers/` (`specs/` + `plans/`) — opisy funkcji i zatwierdzone plany (superpowers)

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
- Lista transakcji bankowych: `ai_top_candidate`; po zapisie kandydatów Celery → Pusher **`categorization.transaction_updated`** / **`bank-transactions`** (React Query). LLM: **wpływ** (`amount > 0`) vs **wydatek** — osobny prompt i lista kategorii; pensje z kontrahenta **przed** LLM (`bank_inflow_salary_rules`). **Ponów kategoryzację** — także wiersze z już zapisanymi kandydatami, bez zapisanej kategorii użytkownika i bez paragonu (jak widoczność „Zapisz kategorię”).
- **Wersjonowanie przy ukończeniu pracy (merge-ready):** podbij **tylko** te składowe, których kod faktycznie dotknąłeś. **Tylko backend** → `backend/src/version.py` + `backend/tests/unit/test_version.py`. **Tylko frontend** → `frontend/package.json` + zgodne pola `version` w `frontend/package-lock.json` (root i `packages[""]`). **Zmiany w obu** → osobny bump każdej strony (numery mogą się różnić). Semver: zwykle **minor** przy nowej funkcji użytkowej, **patch** przy samych poprawkach — **osobno** dla FE i BE. Zob. też `.cursor/rules/00-core.mdc` → *Version bumps*.

## Gotchas i ograniczenia
- Nie czytaj ani nie zmieniaj `.env`, `backend/.env` ani `backend/yoyo.ini` (sekrety)
- **Git / GitHub:** `origin` to **`git@personal:…`** — w `~/.ssh/config` host **`personal`** → `github.com` + właściwy `IdentityFile`. Test: `ssh -T git@personal`. Samo `git@github.com` bez tego aliasu często nie ma klucza (np. w sandboxie agenta).
- Różne porty backendu (8000 / 8080 / 8001 przy Dockerze) — sprawdź przed debugowaniem CORS/proxy
- Nowe UI primitives tylko po konsultacji z `components/ui/index.ts`; nowe katalogi top-level — po uzgodnieniu
