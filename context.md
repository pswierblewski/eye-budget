# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-04-24

## Co to jest
Aplikacja do budżetu domowego: OCR paragonów (PaddleOCR + OpenAI), transakcje bankowe i gotówkowe, kategoryzacja, **grupy rozliczeń** (powiązane operacje) — listy, szczegół grupy, powiązania z transakcjami w UI.
Dla agenta: skrót całości; szczegóły: `frontend/AGENTS.md`, `backend/AGENTS.md`.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix, TanStack Query, Zod, recharts, Pusher/Soketi; testy: **Vitest**; błędy API: **`QueryState`**, **`lib/query-error.ts`** (copy PL)
- Backend: FastAPI, Pydantic v2, psycopg2 (SQL bez ORM), Yoyo, Celery, Redis, MinIO, PaddleOCR / OpenAI
- Infra: PostgreSQL, MinIO, Redis, Soketi; `docker compose` — m.in. Redis, Soketi, backend, worker (Postgres/MinIO często zewnętrzne — `README.md`)
- Wersje **niezależne** (SemVer 2.0.0 osobno dla FE i BE): `frontend/package.json` + `frontend/package-lock.json` (root i `packages[""]`), `backend/src/version.py` + asercja w `tests/unit/test_version.py`; spec: `docs/superpowers/specs/006-semantic-versioning/`. **Przykładowo w tej edycji: FE 1.5.1, BE 1.6.0** — ostatecznie sprawdź w plikach (wersje szybko rosną)

## Struktura
- `frontend/app/` — strony (m.in. `settlement-groups/`) + `app/api/*/route.ts` (proxy do backendu)
- `frontend/components/`, `components/ui/`, `QueryState.tsx` + `lib/query-error.ts`
- `backend/src/` — `main.py`, `data.py`, `repositories/` (m.in. unified, bank, cash — listy z opcjonalnym `settlement_group_title`), `services/`, `tasks/`, `version.py`
- `backend/migrations/` — Yoyo SQL
- `docs/superpowers/` (speci `specs/`, plany `plans/`), `.cursor/skills/` (m.in. DB, MinIO)

## Jak pracować
- Frontend: `cd frontend && npm install && npm run dev` → :3000; `npm run lint`; testy: `npm run test:run`; **UI po polsku**
- Backend: `backend/.venv`, `pip install -r requirements.txt`; `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` (README/docker — inne porty, patrz niżej)
- Docker: `docker compose up` — backend na hoście często **:8001**; Postgres/MinIO zgodnie z `.env` / `README.md`
- Migracje: `cd backend && yoyo apply …`; testy: `python -m pytest` z `backend/` (unit + integracja, coverage: `.coveragerc`)
- CI: migracje Yoyo stosowane przed startem backendu w workflow

## Kluczowe decyzje
- SQL przez psycopg2 z `%s` — bez ORM
- HTTP: `lib/api.ts` → proxy Next → FastAPI; `App()` per request w `main.py` + `dispose()` w `finally`
- Zmiana endpointu: `main.py` + `data.py` + `app/api/.../route.ts` + `lib/api.ts` + `lib/types.ts`
- Lista bankowa: `ai_top_candidate`; po Celery Pusher `categorization.transaction_updated` / `bank-transactions`. LLM: wpływ vs wydatek — osobne prompty; pensje z kontrahenta przed LLM (`bank_inflow_salary_rules`)
- **Wersjonowanie (SemVer, merge-ready):** po zmianach w `frontend/` lub `backend/` podbij tylko wersję **tej** strony. **MAJOR** — naruszenie kompatybilności w danej warstwie (np. usunięty publiczny endpoint, zmiana kontraktu wymagająca równoległej zmiany drugiej strony albo utraty danych użytkownika bez migracji). **MINOR** — nowa wstecz zgodna funkcjonalność (nowe API, nowy flow UI, nowe opcjonalne pole). **PATCH** — poprawki błędów, tylko testy, bezpieczny refactor, bez nowej możliwości użytkowej. Zob. `.cursor/rules/00-core.mdc` → *Version bumps*; PR obejmujący oba katalogi → zwykle dwa bumpy, jeśli obie strony realnie się zmieniły

## Gotchas i ograniczenia
- **Sekrety:** nie commituj `.env`, **`.env.agent`**, lokalnych `backend/.env`. Diagnostyka DB/MinIO: skills + `.env.agent` — bez wklejania tajemnic do czatu
- **Git / GitHub:** `origin` często `git@personal:…` (w `~/.ssh/config` host **`personal`** → `github.com`). Alternatywnie: **`gh`** (token HTTPS) lub `git@github.com` gdy skonfigurowany ten klucz. Środowisko agenta bywa **bez** Twojego SSH — `gh auth status` / HTTPS działają inaczej niż `git push` po SSH
- Różne porty backendu (8000 / 8080 / 8001) — potwierdź przed debugowaniem CORS i proxy
- Nowe widoki: błędy API przez **`QueryState`** / **`QueryErrorNotice`** / **`MutationErrorNotice`** — nie zostawiaj pustego UI przy błędzie
- Nowe prymitywy UI — przez `components/ui` i `index.ts`; katalogi top-level — po uzgodnieniu
