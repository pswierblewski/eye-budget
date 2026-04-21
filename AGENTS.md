# eye-budget — instrukcje dla agenta

Przed rozpoczęciem pracy przeczytaj: `context.md`

## Poziom kontekstu
- [x] Poziom 1 — context.md (czytaj w całości)
- [ ] Poziom 2 — context.md + pliki szczegółowe (linki w context.md)
- [ ] Poziom 3 — wiki/index.md (czytaj index, potem relevantne strony)

## Wersjonowanie (obowiązkowo przy feature)
Po zakończeniu implementacji **nowego feature** (merge-ready): zaktualizuj wersję **frontend + backend** razem — patrz `context.md` → *Kluczowe decyzje* (pliki: `package.json`, `package-lock.json`, `version.py`, `test_version.py`). Szczegóły procesu: `specs/006-semantic-versioning/`.

## Gdzie co leży (bez duplikowania treści)
- **`context.md`** — krótki obraz repo, porty, struktura, granice (PL).
- **`docs/superpowers/`** — zatwierdzone speci (`specs/`) i plany implementacji (`plans/`).
- **`CLAUDE.md`** — stack, komendy, workflow `specs/`, skrót dla Claude Code.
- **`.cursor/rules/00-core.mdc`** — stałe reguły monorepo w Cursorze (kontrakt API, język UI, sekrety).
- **`frontend/AGENTS.md`** / **`backend/AGENTS.md`** — konwencje i „TL;DR” dla danej aplikacji.
