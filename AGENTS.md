# eye-budget — instrukcje dla agenta

Przed rozpoczęciem pracy przeczytaj: `context.md`

## Poziom kontekstu
- [x] Poziom 1 — context.md (czytaj w całości)
- [ ] Poziom 2 — context.md + pliki szczegółowe (linki w context.md)
- [ ] Poziom 3 — wiki/index.md (czytaj index, potem relevantne strony)

## Wersjonowanie (obowiązkowo przy ukończeniu zmian)
Po zakończeniu implementacji, zanim uznać PR za merge-ready: **podbij semver tylko po tej stronie monorepo, którą zmieniłeś** (frontend i backend wersjonują się **niezależnie**). Szczegóły plików i reguły: `context.md` → *Kluczowe decyzje*, `.cursor/rules/00-core.mdc` → *Version bumps*, spec: `specs/006-semantic-versioning/`.

## Gdzie co leży (bez duplikowania treści)
- **`context.md`** — krótki obraz repo, porty, struktura, granice (PL); **Git:** SSH **`personal`** → GitHub (patrz *Gotchas*).
- **`docs/superpowers/`** — zatwierdzone speci (`specs/`) i plany implementacji (`plans/`).
- **`CLAUDE.md`** — stack, komendy, workflow `specs/`, skrót dla Claude Code.
- **`.cursor/rules/00-core.mdc`** — stałe reguły monorepo w Cursorze (kontrakt API, język UI, sekrety).
- **`frontend/AGENTS.md`** / **`backend/AGENTS.md`** — konwencje i „TL;DR” dla danej aplikacji.
- **`.cursor/skills/eye-budget-db-check/SKILL.md`** — diagnostyka i walidacja danych w PostgreSQL podczas implementacji (`.env.agent`, `backend/.venv`, read-only gdy dostępne); stosuj przy ad-hoc zapytaniach do żywej bazy.
- **`.cursor/skills/eye-budget-minio-check/SKILL.md`** — diagnostyka MinIO (bucket, listowanie kluczy, `secure`/endpoint) podczas implementacji; te same zasady: `.env.agent`, `backend/.venv`, preferuj konto read-only do odczytu.
