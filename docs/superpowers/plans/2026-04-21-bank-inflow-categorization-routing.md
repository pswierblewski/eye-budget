# Bank inflow categorization — routing, salary rules, Wynagrodzenie parent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route bank transaction categorization by sign of `amount`: inflows (`> 0`) use a dedicated prompt and category list (`expense` ∪ `income`); apply deterministic salary matching (Pern → Pensja Ada, Software Engineering Paweł Świerblewski → Pensja Paweł) before any LLM call; add DB parent category **Wynagrodzenie** for the two salary leaves.

**Architecture:** Pure module resolves counterparty → salary rule key (case-insensitive, ASCII fold for diacritics). `CategoriesRepository` exposes prompt-specific category rows and resolves Pensja IDs by name at runtime. `BankCategorizationService.build()` loads two markdown tables + salary id map; `assign_candidates` / `assign_candidates_async` branch on `tx.amount`, short-circuit on deterministic match, otherwise call OpenAI with the correct system prompt and category table.

**Tech Stack:** Python 3, pytest, PostgreSQL (yoyo migrations), OpenAI client (unchanged tool schema).

**Spec:** `docs/superpowers/specs/2026-04-21-bank-inflow-categorization-routing-design.md` (Approved)

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/migrations/20260421_01_wynagrodzenie-category-parent.sql` | Idempotent: insert `Wynagrodzenie` (`income`, root); set `parent_id` on `Pensja Ada` / `Pensja Paweł` |
| `backend/src/bank_inflow_salary_rules.py` | Pure: normalize counterparty, `try_deterministic_inflow_salary_rule(counterparty) -> Literal["pensja_pawel", "pensja_ada"] \| None`; Paweł checked before Pern |
| `backend/tests/unit/test_bank_inflow_salary_rules.py` | Unit tests: casefold, ASCII `Swierblewski`, `PERN`, ordering |
| `backend/src/repositories/categories.py` | Add `get_categories_for_bank_expense_prompt`, `get_categories_for_bank_inflow_prompt`, `get_salary_category_ids_for_bank_rules()` → `dict` with keys `pensja_ada`, `pensja_pawel` mapping to `(id, name)` or raise/return empty if missing |
| `backend/src/services/bank_categorization.py` | Two markdown tables, two system prompts, user template with `direction` line; router + deterministic branch; shared `_call_llm_assign` to avoid duplication |
| `backend/tests/unit/test_services_llm.py` | Extend `TestBankCategorizationService` / Extended: `build()` loads two tables; inflow + Pern → no LLM, expected candidate; expense still calls LLM |
| `docs/superpowers/specs/2026-04-21-bank-inflow-categorization-routing-design.md` | Status **Approved** (already updated when plan was written) |

---

### Task 1: Branch

**Files:** (git only)

- [ ] **Step 1: Create feature branch**

Run:

```bash
cd /home/pawel/eye-budget && git checkout -b feature/bank-inflow-categorization-routing
```

Expected: branch created from `master` (or your default).

---

### Task 2: Pure salary rule helper

**Files:**
- Create: `backend/src/bank_inflow_salary_rules.py`
- Create: `backend/tests/unit/test_bank_inflow_salary_rules.py`

- [ ] **Step 1: Implement `backend/src/bank_inflow_salary_rules.py`**

```python
"""Deterministic inflow salary detection from bank counterparty (before LLM)."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

SalaryRule = Literal["pensja_pawel", "pensja_ada"]

# Normalized reference (ASCII) for "Software Engineering Paweł Świerblewski"
_REF_PAWEL_ASCII = "software engineering pawel swierblewski"
# Substring for Pern (case-insensitive via casefold on haystack)
_SUB_PERN = "pern"


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _to_ascii_lower(s: str) -> str:
    nkfd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nkfd if unicodedata.category(c) != "Mn")
    return stripped.lower()


def try_deterministic_inflow_salary_rule(counterparty: str | None) -> SalaryRule | None:
    """
    If counterparty matches employer rules, return which Pensja bucket applies.
    Order: longer / more specific (Paweł full name) before Pern substring.
    Matching is case-insensitive; diacritics tolerated via ASCII fold on haystack for Paweł.
    """
    if not counterparty:
        return None
    collapsed = _collapse_spaces(counterparty)
    haystack_cf = collapsed.casefold()
    haystack_ascii = _to_ascii_lower(collapsed)

    if _REF_PAWEL_ASCII in haystack_ascii:
        return "pensja_pawel"
    # Unicode reference as casefolded substring (ogonek letters in counterparty)
    ref_pawel_cf = "software engineering paweł świerblewski".casefold()
    if ref_pawel_cf in haystack_cf:
        return "pensja_pawel"

    if _SUB_PERN in haystack_ascii or _SUB_PERN in haystack_cf:
        return "pensja_ada"

    return None
```

- [ ] **Step 2: Add tests `backend/tests/unit/test_bank_inflow_salary_rules.py`**

```python
import pytest

from src.bank_inflow_salary_rules import try_deterministic_inflow_salary_rule


@pytest.mark.unit
class TestBankInflowSalaryRules:
    def test_pawel_case_insensitive(self):
        assert (
            try_deterministic_inflow_salary_rule(
                "SOFTWARE ENGINEERING PAWEŁ ŚWIERBLEWSKI"
            )
            == "pensja_pawel"
        )

    def test_pawel_ascii_swierblewski(self):
        assert (
            try_deterministic_inflow_salary_rule(
                "Software Engineering Pawel Swierblewski"
            )
            == "pensja_pawel"
        )

    def test_pern_case_insensitive(self):
        assert try_deterministic_inflow_salary_rule("PERN S.A.") == "pensja_ada"
        assert try_deterministic_inflow_salary_rule("pern sp z o o") == "pensja_ada"

    def test_pawel_before_pern_if_both_substrings_unlikely(self):
        # Document order: full Software Engineering name checked first
        assert (
            try_deterministic_inflow_salary_rule(
                "Software Engineering Paweł Świerblewski"
            )
            == "pensja_pawel"
        )

    def test_none_empty(self):
        assert try_deterministic_inflow_salary_rule(None) is None
        assert try_deterministic_inflow_salary_rule("") is None

    def test_no_match(self):
        assert try_deterministic_inflow_salary_rule("ZABKA SP Z O O") is None
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_bank_inflow_salary_rules.py -v
```

Expected: all **passed**.

- [ ] **Step 4: Commit**

```bash
git add backend/src/bank_inflow_salary_rules.py backend/tests/unit/test_bank_inflow_salary_rules.py
git commit -m "feat(bank): deterministic inflow salary counterparty rules (pure)"
```

---

### Task 3: SQL migration — Wynagrodzenie parent

**Files:**
- Create: `backend/migrations/20260421_01_wynagrodzenie-category-parent.sql`

- [ ] **Step 1: Add migration file**

```sql
-- depends: 20260413_01_bank-transaction-splits-unique

-- Parent income category for salary leaves (idempotent insert)
INSERT INTO categories (parent_id, name, c_type)
SELECT NULL, 'Wynagrodzenie', 'income'::category_type
WHERE NOT EXISTS (
    SELECT 1 FROM categories c
    WHERE c.name = 'Wynagrodzenie' AND c.parent_id IS NULL
);

-- Attach existing pensje under Wynagrodzenie (do not change category ids)
UPDATE categories child
SET parent_id = parent.id
FROM categories parent
WHERE parent.name = 'Wynagrodzenie'
  AND parent.parent_id IS NULL
  AND child.name IN ('Pensja Ada', 'Pensja Paweł')
  AND (child.parent_id IS DISTINCT FROM parent.id);
```

- [ ] **Step 2: Apply locally** (if you use yoyo; adjust command to project convention)

Run (example):

```bash
cd /home/pawel/eye-budget/backend && yoyo apply --batch
```

Expected: migration applies without error (or your tool reports already applied).

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/20260421_01_wynagrodzenie-category-parent.sql
git commit -m "db: Wynagrodzenie parent for Pensja Ada/Paweł"
```

---

### Task 4: CategoriesRepository — prompt rows + salary IDs

**Files:**
- Modify: `backend/src/repositories/categories.py`

- [ ] **Step 1: Add methods** (implement next to `get_categories`; reuse the same SELECT shape: `c.id`, `c.name`, `cp.name`)

Add:

1. `get_categories_for_bank_expense_prompt(self) -> list` — **identical query** to current `get_categories()` (`c_type = 'expense'`). Optionally implement by extracting private `_fetch_categories_rows(where_clause, params)` to avoid copy-paste; minimal change: call existing body or duplicate single query.

2. `get_categories_for_bank_inflow_prompt(self) -> list` — same columns, **`WHERE c.c_type IN ('expense', 'income')`**, stable order e.g. `ORDER BY c.c_type, cp.name NULLS FIRST, c.name`.

3. `get_salary_category_ids_for_bank_rules(self) -> dict[str, tuple[int, str]]` — query **`WHERE c.name IN ('Pensja Ada', 'Pensja Paweł')`** (names are unique względem logiki `insert_category`). Zwróć `{"pensja_ada": (id, name), "pensja_pawel": (id, name)}`.

   **Decyzja:** `BankCategorizationService.build()` po migracji **rzuca `ValueError`** z czytelnym komunikatem, jeśli brakuje któregokolwiek z dwóch wierszy — import CSV nie powinien milcząco wyłączać reguł pensji.

- [ ] **Step 2: Unit test repository** (optional but recommended)

Create `backend/tests/unit/test_categories_repository_bank_prompts.py` with mocked cursor returning two rows for salary names and asserting keys — **or** extend existing categories tests if present.

- [ ] **Step 3: Commit**

```bash
git add backend/src/repositories/categories.py backend/tests/unit/test_categories_repository_bank_prompts.py
git commit -m "feat(categories): bank expense/inflow prompt rows and salary id lookup"
```

(Omit test file line in `git add` if skipped.)

---

### Task 5: BankCategorizationService — dual prompts, router, deterministic path

**Files:**
- Modify: `backend/src/services/bank_categorization.py`

- [ ] **Step 1: Imports and constants**

Add:

```python
from ..bank_inflow_salary_rules import try_deterministic_inflow_salary_rule
```

Replace single `SYSTEM_PROMPT` / `USER_PROMPT_TEMPLATE` with:

- `SYSTEM_PROMPT_EXPENSE` — text **equal** to current `SYSTEM_PROMPT`.
- `SYSTEM_PROMPT_INFLOW` — same opening + extra bullets per spec (wpływ vs wydatek semantics, no „Jedzenie” for obvious payroll, prefer Wynagrodzenie children when listing allows).
- `USER_PROMPT_TEMPLATE` — shared f-string with new placeholders: `{direction_line}`, `{categories_table}` — where `direction_line` is `Kierunek: wpływ na konto (kwota dodatnia).` or `Kierunek: wydatek z konta (kwota ujemna lub zero).` (use **wydatek** for `<= 0` per spec).

- [ ] **Step 2: `build()`**

After init fields, set:

- `self.categories_table_expense` from `get_categories_for_bank_expense_prompt()` via markdown helper (same loop as today).
- `self.categories_table_inflow` from `get_categories_for_bank_inflow_prompt()`.
- `self._salary_rule_categories: dict[str, tuple[int, str]]` from `get_salary_category_ids_for_bank_rules()` — keys `pensja_ada`, `pensja_pawel` (normalize key names to match `try_deterministic_inflow_salary_rule` return values).

If `try_deterministic_inflow_salary_rule` returns `"pensja_ada"` map to `self._salary_rule_categories["pensja_ada"]`.

Deprecate `self.categories_table` — replace all uses: expense path uses `categories_table_expense`, inflow LLM path uses `categories_table_inflow`.

- [ ] **Step 3: Private helpers**

```python
def _deterministic_inflow_candidates(self, tx: BankTransactionDetail) -> list[dict] | None:
    if tx.amount <= 0:
        return None
    key = try_deterministic_inflow_salary_rule(tx.counterparty)
    if key is None or not self._salary_rule_categories:
        return None
    pair = self._salary_rule_categories.get(key)
    if pair is None:
        return None
    cid, cname = pair
    return [{"category_id": cid, "category_name": cname, "category_score": 1.0}]

def _prompt_parts_for_tx(self, tx: BankTransactionDetail) -> tuple[str, str, str]:
    """Returns (system_prompt, categories_table, direction_line)."""
    if tx.amount > 0:
        return (
            self.SYSTEM_PROMPT_INFLOW,
            self.categories_table_inflow,
            "Kierunek: wpływ na konto (kwota dodatnia).",
        )
    return (
        self.SYSTEM_PROMPT_EXPENSE,
        self.categories_table_expense,
        "Kierunek: wydatek z konta (kwota ujemna lub zero).",
    )
```

- [ ] **Step 4: `assign_candidates` / `assign_candidates_async`**

At start of each:

```python
det = self._deterministic_inflow_candidates(tx)
if det is not None:
    return det
system_prompt, categories_table, direction_line = self._prompt_parts_for_tx(tx)
# build user prompt with categories_table and direction_line
# Pass system_prompt into responses.create — API may need instructions in `input`; check current code: today only user message. If model ignores system, prepend system text to user message OR add instructions field per OpenAI Responses API.
```

**Critical:** Current code sends **only** `role: user`. If your SDK supports `instructions` parameter on `responses.create`, set `instructions=system_prompt`. If not, prepend to user text:

```python
user_text = f"{system_prompt}\n\n" + prompt_body
```

Use whichever matches existing project patterns (grep `responses.create` elsewhere).

Refactor duplicated LLM call into `_assign_via_llm(self, tx, context_section, system_prompt, categories_table, direction_line, sync: bool)` to keep one place for tool schema.

- [ ] **Step 5: Run focused tests**

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/test_services_llm.py -v -k "BankCategorization"
```

Fix any failures (`build()` now mocks must provide new repository methods).

- [ ] **Step 6: Full backend unit suite** (quality gate)

```bash
cd /home/pawel/eye-budget/backend && pytest tests/unit/ -q
```

Expected: **green**.

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/bank_categorization.py backend/tests/unit/test_services_llm.py
git commit -m "feat(bank): route inflow vs expense prompts and deterministic salary"
```

---

### Task 6: Integration-style test — deterministic path skips LLM

**Files:**
- Modify: `backend/tests/unit/test_services_llm.py` (or new file)

- [ ] **Step 1: Add test**

```python
def test_assign_candidates_inflow_pern_skips_llm(self):
    mock_db = MagicMock()
    mock_db.conn = None
    mock_client = MagicMock()
    svc = BankCategorizationService(
        db_context=mock_db,
        client=mock_client,
        async_client=MagicMock(),
    )
    svc.categories_table_expense = "|"
    svc.categories_table_inflow = "|"
    svc._salary_rule_categories = {
        "pensja_ada": (130, "Pensja Ada"),
        "pensja_pawel": (131, "Pensja Paweł"),
    }
    tx = BankTransactionDetail(
        id=1,
        reference_number="R1",
        booking_date="2024-01-01",
        counterparty="PERN SP. Z O.O.",
        amount=100.0,
        currency="PLN",
    )
    result = svc.assign_candidates(tx)
    assert result == [
        {"category_id": 130, "category_name": "Pensja Ada", "category_score": 1.0}
    ]
    mock_client.responses.create.assert_not_called()
```

Adjust IDs **130/131** to match your test DB if you use real IDs — in unit test use arbitrary ints **42/43** consistently.

- [ ] **Step 2: Commit**

```bash
git add backend/tests/unit/test_services_llm.py
git commit -m "test(bank): deterministic inflow salary skips OpenAI"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task(s) |
|------------------|---------|
| `amount > 0` → wpływ prompt + expense∪income list | Task 5 |
| `amount <= 0` → wydatek prompt + expense only | Task 5 |
| Deterministic Pern / Software Eng before LLM | Task 2, 5, 6 |
| Case-insensitive matching | Task 2 tests |
| Wynagrodzenie parent + reparent pensji | Task 3 |
| `get_categories()` unchanged for receipts | Task 4 (new methods only) |
| Direction line in user template for inflow | Task 5 |
| Celery / import unchanged | Task 5 (same public methods) |

**Placeholder scan:** none intentional.

**Type consistency:** `try_deterministic_inflow_salary_rule` returns `"pensja_pawel"` / `"pensja_ada"`; repository dict keys must match exactly.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-21-bank-inflow-categorization-routing.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach do you prefer?
