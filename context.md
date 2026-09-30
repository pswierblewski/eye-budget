# eye-budget — kontekst dla agenta

> Ostatnia aktualizacja: 2026-09-30

## Co to jest
Aplikacja do budżetu domowego: OCR paragonów (PaddleOCR + OpenAI), transakcje bankowe i gotówkowe, kategoryzacja, **grupy rozliczeń** (powiązane operacje) — listy, szczegół grupy, powiązania z transakcjami w UI.
Dla agenta: skrót całości; szczegóły: `frontend/AGENTS.md`, `backend/AGENTS.md`.

## Stack / Technologie
- Frontend: Next.js 14, App Router, TypeScript strict, Tailwind, Radix, TanStack Query, Zod, recharts, Pusher/Soketi; testy: **Vitest**; błędy API: **`QueryState`**, **`lib/query-error.ts`** (copy PL)
- Backend: FastAPI, Pydantic v2, psycopg2 (SQL bez ORM), Yoyo, Celery, Redis, MinIO, PaddleOCR / OpenAI
- Infra: PostgreSQL, MinIO, Redis, Soketi; `docker compose` — m.in. Redis, Soketi, backend, worker (Postgres/MinIO często zewnętrzne — `README.md`)
- Wersje **niezależne** (SemVer 2.0.0 osobno dla FE i BE): `frontend/package.json` + `frontend/package-lock.json` (root i `packages[""]`), `backend/src/version.py` + asercja w `tests/unit/test_version.py`; spec: `docs/superpowers/specs/006-semantic-versioning/`. **Stan na 2026-09-30: FE 1.10.0, BE 1.11.0** — sprawdź w plikach przed release.

## Struktura
- `frontend/app/` — strony (m.in. `settlement-groups/`, `receipts/`) + `app/api/*/route.ts` (proxy do backendu)
- `frontend/components/`, `components/ui/`, `QueryState.tsx` + `lib/query-error.ts`
- `backend/src/` — `main.py`, `data.py`, `repositories/` (m.in. unified, bank, cash — listy z opcjonalnym `settlement_group_title`), `services/` (m.in. **`receipt_ocr_validation.py`**), `tasks/`, `version.py`
- `backend/migrations/` — Yoyo SQL
- `docs/superpowers/` (speci `specs/`, plany `plans/`), `.cursor/skills/` (m.in. DB, MinIO)

## Jak pracować
- Frontend: `cd frontend && npm install && npm run dev` → :3000; `npm run lint`; testy: `npm run test:run`; **UI po polsku**
- Backend: `backend/.venv`, `pip install -r requirements.txt`; `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` (README/docker — inne porty, patrz niżej)
- Docker: `docker compose up` — backend na hoście często **:8001**; Postgres/MinIO zgodnie z `.env` / `README.md`
- Migracje: `cd backend && yoyo apply …`; testy: `python -m pytest` z `backend/` (unit + integracja, coverage: `.coveragerc`)
- CI: migracje Yoyo stosowane przed startem backendu w workflow
- **Domyślna gałąź Git:** `master` (nie `main`)

## Kluczowe decyzje
- SQL przez psycopg2 z `%s` — bez ORM
- HTTP: `lib/api.ts` → proxy Next → FastAPI; `App()` per request w `main.py` + `dispose()` w `finally`
- Zmiana endpointu: `main.py` + `data.py` + `app/api/.../route.ts` + `lib/api.ts` + `lib/types.ts`
- Lista bankowa: `ai_top_candidate`; po Celery Pusher `categorization.transaction_updated` / `bank-transactions`. LLM: wpływ vs wydatek — osobne prompty; pensje z kontrahenta przed LLM (`bank_inflow_salary_rules`)
- **Auto-potwierdzanie paragonów:** `ProductResolver` (dokładne → `pg_trgm`/`rapidfuzz` → LLM z listy) + `category_history` (dominująca kategoria) → `CategoriesService` tylko dla reszty → `receipt_auto_confirm.evaluate` (suma, pewność). `confirmation_source` `manual|auto`, powody w `auto_confirm_reasons`; flaga `RECEIPT_AUTO_CONFIRM_ENABLED` (domyślnie off); zaległe: `POST /receipts/rescore?dry_run=`. Ground truth tylko z ręcznych potwierdzeń.
- **OCR paragonów (prod):** po odpowiedzi LLM → **`validate_ocr_payload`** (`services/receipt_ocr_validation.py`); przy błędzie semantycznym **`status=failed`**, `message` (PL), surowy dict w **`ocr_raw`**, **bez** zapisu do `result` i bez łańcucha vendor/products/categories. Sukces → `result` + dalszy pipeline jak wcześniej. Szczegóły API: `ReceiptScanDetail.message`, `ReceiptScanDetail.ocr_raw`; UI na `/receipts/[id]` dla `failed`.
- **Lista zunifikowana (`GET /transactions`):** paragony tylko `to_confirm`/`done`; cast daty z JSON używa **`NULLIF(TRIM(result->>'date'), '')`** (legacy puste stringi nie psują całej listy).
- **Wersjonowanie (SemVer, merge-ready):** po zmianach w `frontend/` lub `backend/` podbij tylko wersję **tej** strony. **MAJOR** — naruszenie kompatybilności w danej warstwie. **MINOR** — nowa wstecz zgodna funkcjonalność. **PATCH** — poprawki błędów bez nowej możliwości użytkowej. Zob. `.cursor/rules/00-core.mdc` → *Version bumps*.

## Ostatnio wdrożone (skrót)
- **PR #39 (2026-09-30):** bramka walidacji OCR, kolumna `ocr_raw`, migracje `20260930_01` (naprawa pustych dat w JSON) i `20260930_02` (`ocr_raw`), Pusher `receipt.progress` z polem `error` przy failu pliku.

## Gotchas i ograniczenia
- **Sekrety:** nie commituj `.env`, **`.env.agent`**, lokalnych `backend/.env`. Diagnostyka DB/MinIO: skills + `.env.agent` — bez wklejania tajemnic do czatu
- **Git / GitHub:** `origin` często `git@personal:…` (w `~/.ssh/config` host **`personal`** → `github.com`). Alternatywnie: **`gh`** (token HTTPS) lub `git@github.com`. Deploy CI: self-hosted runner → serwer w LAN (`deploy.yml`, secret **`MODEL`** itd.)
- Różne porty backendu (8000 / 8080 / 8001) — potwierdź przed debugowaniem CORS i proxy
- Nowe widoki: błędy API przez **`QueryState`** / **`QueryErrorNotice`** / **`MutationErrorNotice`** — nie zostawiaj pustego UI przy błędzie; status biznesowy **`failed`** paragonu to nie błąd HTTP — komunikat w `message` / UI
- **Stare paragony** z błędnym `result` (sprzed bramki) **nie** dostają retroaktywnie `failed` — opcjonalnie migracja danych / „Ponów przetwarzenie”; bramka działa przy kolejnym OCR
- Nowe prymitywy UI — przez `components/ui` i `index.ts`; katalogi top-level — po uzgodnieniu
- Model LLM główny: env **`MODEL`** (OCR, kategorie bankowe itd.); symulacja budżetu nadal **`gpt-4o-mini`** w kodzie
