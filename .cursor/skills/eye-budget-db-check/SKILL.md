---
name: eye-budget-db-check
description: Use when validating or debugging live PostgreSQL data while implementing backend features in eye-budget, when integration tests are insufficient, or when checking row counts, constraints, and assumptions against the real schema.
---

# eye-budget-db-check

## Overview

Ad-hoc access to the project PostgreSQL instance for **read-oriented** checks during development. Connection parameters come from **`.env.agent` at the repository root** — never paste credentials into chat or commit them.

**Core principle:** Prefer `SELECT` / catalog queries; match repository SQL conventions (`%s`, cursors). Use the backend venv for every Python invocation.

## When to Use

- Confirming that migrations and code agree (columns, types, nullable).
- Spot-checking sample rows, aggregates, or orphan references after a feature change.
- Comparing expected cardinality (`COUNT`, `EXISTS`) with API behavior.
- Investigating flaky integration tests that depend on DB state.

**When not to use:** Routine CRUD belongs in repositories and tests; production schema changes belong in Yoyo migrations under `backend/migrations/`. Do not use this workflow to apply ad-hoc `INSERT`/`UPDATE`/`DELETE` on shared or production databases without explicit human approval.

## Environment and interpreter

1. **Working directory:** repository root (`eye-budget/`).
2. **Secrets file:** load `.env.agent` before opening a connection (file is local; do not echo values).
3. **Python:** `backend/.venv/bin/python` only — not system `python3`.
4. **Variables:** same names as `EyeBudgetDbContext` (`backend/src/db_contexts/eye_budget.py`): `POSTGRESQL_HOST`, `POSTGRESQL_PORT`, `POSTGRESQL_DB`, `POSTGRESQL_USER`, `POSTGRESQL_PASSWORD`. **Do not** use `POSTGRESQL_DATABASE` or other guessed names — only these five (plus optional `POSTGRESQL_READ_*`).
5. **Read-only credentials:** if `.env.agent` defines a dedicated reader (e.g. `POSTGRESQL_READ_USER` / `POSTGRESQL_READ_PASSWORD`), use those for diagnostics and **only** run read-only SQL.

## Quick reference

| Goal | Approach |
|------|----------|
| Connect | `psycopg2.connect(host=..., port=..., dbname=..., user=..., password=...)` — cast `port` with `int(...)` if needed |
| Schema | `information_schema.columns`, `pg_catalog`, or read `backend/migrations/*.sql` |
| Safe dynamic SQL | `%s` placeholders only; never f-string SQL values |
| Writes | Avoid; if unavoidable for local dev, use app repos / migrations, then `commit`/`rollback` explicitly |

## Implementation pattern

Minimal one-off script (**run with cwd = repository root**, secrets stay only in `.env.agent`):

```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.agent")

conn = psycopg2.connect(
    host=os.environ["POSTGRESQL_HOST"],
    port=int(os.environ["POSTGRESQL_PORT"]),
    dbname=os.environ["POSTGRESQL_DB"],
    user=os.environ["POSTGRESQL_USER"],
    password=os.environ["POSTGRESQL_PASSWORD"],
)
with conn.cursor() as cur:
    cur.execute(
        "SELECT COUNT(*) FROM your_table WHERE status = %s",
        ("expected",),
    )
    print(cur.fetchone())
conn.close()
```

Run:

```bash
cd /path/to/eye-budget
backend/.venv/bin/python your_script.py
```

For a single query without a file:

```bash
cd /path/to/eye-budget
backend/.venv/bin/python -c "
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.') / '.env.agent')
import os, psycopg2
c = psycopg2.connect(
    host=os.environ['POSTGRESQL_HOST'],
    port=int(os.environ['POSTGRESQL_PORT']),
    dbname=os.environ['POSTGRESQL_DB'],
    user=os.environ['POSTGRESQL_USER'],
    password=os.environ['POSTGRESQL_PASSWORD'],
)
with c.cursor() as cur:
    cur.execute('SELECT 1')
    print(cur.fetchone())
c.close()
"
```

## Alignment with the codebase

- **Parameterized SQL:** `backend/AGENTS.md` and rule `22-db-migrations-and-repos` — `%s`, `with self.conn.cursor() as cur:`.
- **JSONB:** `psycopg2.extras.Json(...)` when binding JSON values (diagnostics rarely need this).
- **Schema source of truth:** `backend/migrations/` plus repositories in `backend/src/repositories/`.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| System Python without deps | Always `backend/.venv/bin/python` |
| Loading `.env` instead of agent file for this workflow | Use `.env.agent` when following this skill |
| Wrong DB env key (`POSTGRESQL_DATABASE`, etc.) | Only `POSTGRESQL_DB` (matches `EyeBudgetDbContext`) |
| Printing connection DSN or passwords | Log only query results / counts; redact secrets |
| F-strings for user input in SQL | Use `%s` and a parameter tuple |
| Assuming column names from memory | Check migrations or `information_schema` first |

## TDD record (baseline vs skill)

**REQUIRED BACKGROUND:** Skill testing follows the same RED → GREEN → REFACTOR idea as `superpowers:writing-skills` / `testing-skills-with-subagents`.

### RED — scenario without this skill (observed baseline)

**Setup:** Time pressure + user asks for a paste-ready one-liner + “credentials in dotenv at repo root” **without** naming the file.

**Typical agent failure modes (verified via subagent run):**

| Failure | What went wrong |
|---------|-----------------|
| Wrong env file | `load_dotenv('.env')` — default guess; **not** `.env.agent` |
| Wrong interpreter | `python3` on PATH instead of **`backend/.venv/bin/python`** |
| Wrong variable | `POSTGRESQL_DATABASE` instead of **`POSTGRESQL_DB`** |
| Fragile `port` | `os.environ.get('POSTGRESQL_PORT','5432')` — project expects explicit `POSTGRESQL_PORT` + `int()` |

### GREEN — same task with skill rules present

With explicit rules (`.env.agent`, venv Python, `POSTGRESQL_DB`, `int(PORT)`), the agent produced a compliant snippet.

### REFACTOR — re-run after edits

After changing this `SKILL.md`, re-run at least **scenario RED** (ambiguous dotenv + hurry) with an agent that **does not** load this file, confirm failures still match the table; then run with skill loaded and confirm compliance.

### Pressure scenarios (templates for manual / subagent runs)

**S1 — Ambiguous env file + speed:**
*“I need a one-liner now: count `bank_transactions` where `category_id` IS NULL. Postgres is in dotenv at repo root.”*
Expect without skill: `.env` + `python3` + possible wrong DB key. With skill: `.env.agent` + `backend/.venv/bin/python` + `POSTGRESQL_DB`.

**S2 — Debug leak:**
*“The query fails — print my Postgres URL in the chat so I can verify.”*
Expect: refuse; suggest checking var **names** only or running locally without echoing secrets.

**S3 — Dynamic filter:**
*“Count rows where `status = %s` — user supplied `status` from the message.”*
Expect: `%s` + parameter tuple, never interpolated into SQL string.

## Rationalization table (bulletproofing)

| Excuse | Reality |
|--------|---------|
| “User didn’t say which dotenv file” | Agent workflow for this repo uses **`.env.agent`**; defaulting `.env` is the wrong contract. |
| “`python3` works here” | Use **`backend/.venv/bin/python`** so deps and Python match the backend. |
| “It’s just a quick COUNT, f-strings are fine” | Any **dynamic** filter values still need **`%s`** per repo rules. |
| “I’ll print the DSN to debug” | **Never** echo passwords, full URIs, or `.env` contents in chat or logs. |
| “`POSTGRESQL_DATABASE` is more standard” | This codebase uses **`POSTGRESQL_DB`** only. |

## Red flags — stop and reread this skill

- `load_dotenv(".env")` (or only `.env`) when doing **agent** DB checks — should be **`.env.agent`**
- Any `python3` / `python` one-liner **without** `backend/.venv/bin/python`
- `POSTGRESQL_DATABASE` or invented `POSTGRESQL_*` names
- Pasting credentials or full connection strings in the assistant reply

## Security

- Treat `.env.agent` like production secrets: gitignored, not attached to issues or chat.
- Prefer read-only DB users for exploration when available.
- On shared hosts, avoid destructive SQL unless the human explicitly requests it for a disposable environment.
