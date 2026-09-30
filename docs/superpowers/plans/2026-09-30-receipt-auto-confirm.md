# Receipt Auto-Confirm (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically confirm receipts whose categories can be derived with confidence from confirmed history, leave the rest in `to_confirm` with human-readable reasons, and let the user re-score the backlog (dry run first).

**Architecture:** A history-first pipeline replaces the "LLM normalizes + LLM categorizes everything" step: `ProductResolver` maps raw names to existing products (exact → trigram fuzzy → LLM pick-from-shortlist), `category_history` yields a dominant category per product, `CategoriesService` is asked only about the rest (with few-shot examples), and a pure `evaluate()` gate decides. When the gate passes, the existing `App.confirm_receipt` runs with `confirmation_source="auto"`. A Celery task re-scores the backlog without re-running OCR.

**Tech Stack:** Python 3.11 / FastAPI / Pydantic v2 / psycopg2 / Yoyo / Celery / OpenAI Responses API / `pg_trgm` (fallback `rapidfuzz`); Next.js 14 / TypeScript / Zod / TanStack Query / Vitest.

**Spec:** `docs/superpowers/specs/2026-09-30-receipt-auto-confirm-design.md`

## Global Constraints

- All user-facing strings in Polish (UI copy and `reason.message`).
- Backend: raw parameterized SQL (`%s`), `commit()` on success / `rollback()` in `except`; all Pydantic models in `backend/src/data.py`; all routes in `backend/src/main.py` with `response_model=`.
- Every endpoint change touches: `main.py`, `data.py`, `frontend/app/api/.../route.ts`, `frontend/lib/api.ts` + `frontend/lib/types.ts`.
- Frontend: only primitives from `frontend/components/ui/index.ts`; Tailwind + `clsx`; types via `z.infer`; invalidate queries after mutations; API errors via `QueryErrorNotice` / `MutationErrorNotice`.
- Tests: pytest with `@pytest.mark.unit` / `@pytest.mark.integration`, AAA comments; unit App tests via `make_app()`.
- Env defaults: `RECEIPT_AUTO_CONFIRM_ENABLED=false`, `RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE=0.9`, `RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT=2`, `RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE=0.9`.
- Fuzzy thresholds: auto-accept at similarity ≥ `0.85`; shortlist = top `10` with similarity ≥ `0.3`.
- Sum tolerance: `|Σ price − total| ≤ 0.01`.
- Ground truth is written only for `confirmation_source == "manual"`.
- Versions at the end: backend `1.10.0 → 1.11.0`, frontend `1.9.0 → 1.10.0`.
- Never read/modify `.env`, `backend/yoyo.ini`.

## Commands

- Backend unit: `cd backend && ../venv/bin/python -m pytest tests/unit -m unit -q -p no:cacheprovider --no-cov`
- Backend single file: `cd backend && ../venv/bin/python -m pytest tests/unit/<file>.py -q --no-cov`
- Backend integration (Docker): `cd backend && ../venv/bin/python -m pytest tests/integration -m integration -q --no-cov`
- Frontend: `cd frontend && npm run test:run && npm run lint && npx tsc --noEmit`

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `backend/migrations/20260930_03_pg-trgm.sql` | create | Guarded `pg_trgm` + GIN index |
| `backend/migrations/20260930_04_receipts-scans-auto-confirm.sql` | create | `confirmation_source`, `auto_confirm_reasons` |
| `backend/migrations/20260930_05_prompt-analytics-auto-confirm-reverted.sql` | create | `auto_confirm_reverted` flag |
| `backend/src/services/receipt_auto_confirm.py` | create | Settings, `ProductResolution`, pure `evaluate()` |
| `backend/src/services/category_history.py` | create | Pure `dominant_category()` |
| `backend/src/repositories/category_history.py` | create | History counts SQL, vendor history |
| `backend/src/services/product_resolver.py` | create | Raw name → product id |
| `backend/src/services/receipt_categorization.py` | create | History + AI → candidates + resolutions |
| `backend/src/tasks/rescore_pending_receipts.py` | create | Celery task |
| `backend/src/repositories/products.py` | modify | Trigram search, upsert alt name, names by ids |
| `backend/src/repositories/vendors.py` | modify | Upsert alt name |
| `backend/src/repositories/receipts_scans.py` | modify | New columns, filter, pending scans |
| `backend/src/repositories/prompt_analytics.py` | modify | `mark_auto_confirm_reverted` |
| `backend/src/services/products.py` | modify | `resolve_products` LLM call |
| `backend/src/services/categories.py` | modify | Few-shot examples, `category_ids` |
| `backend/src/data.py` | modify | New models + fields |
| `backend/src/app.py` | modify | Wiring, confirm/reopen, pipeline, rescore |
| `backend/src/main.py` | modify | `POST /receipts/rescore`, list filter |
| `backend/src/celery_app.py` | modify | Register task |
| `backend/src/tasks/process_receipts.py` | modify | `auto_confirmed` in progress payload |
| `frontend/lib/types.ts`, `frontend/lib/api.ts` | modify | Schemas + client |
| `frontend/app/api/receipts/rescore/route.ts` | create | Proxy |
| `frontend/lib/categorySource.ts` | create | Pure label helper |
| `frontend/components/CategorySourcePill.tsx` | create | Source pill |
| `frontend/components/AutoConfirmReasonsPanel.tsx` | create | Reasons panel |
| `frontend/components/RescoreReceiptsModal.tsx` | create | Backlog re-score modal |
| `frontend/app/receipts/[id]/page.tsx` | modify | Pills, panel, auto banner |
| `frontend/app/receipts/page.tsx` | modify | Auto pill, tab, rescore button |

---

### Task 1: Database migrations

**Files:**
- Create: `backend/migrations/20260930_03_pg-trgm.sql`
- Create: `backend/migrations/20260930_04_receipts-scans-auto-confirm.sql`
- Create: `backend/migrations/20260930_05_prompt-analytics-auto-confirm-reverted.sql`
- Test: `backend/tests/integration/test_auto_confirm_migrations.py`

**Interfaces:**
- Produces: columns `receipts_scans.confirmation_source TEXT NULL CHECK IN ('manual','auto')`, `receipts_scans.auto_confirm_reasons JSONB NULL`, `prompt_analytics.auto_confirm_reverted BOOLEAN NOT NULL DEFAULT FALSE`; extension `pg_trgm` when privileges allow.

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/integration/test_auto_confirm_migrations.py
import pytest
import psycopg2


def _connect(pg):
    return psycopg2.connect(
        host=pg.get_container_host_ip(),
        port=pg.get_exposed_port(5432),
        dbname=pg.dbname,
        user=pg.username,
        password=pg.password,
    )


@pytest.mark.integration
def test_receipts_scans_has_auto_confirm_columns(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'receipts_scans' "
            "AND column_name IN ('confirmation_source', 'auto_confirm_reasons')"
        )
        columns = {row[0] for row in cur.fetchall()}
    conn.close()

    # Assert
    assert columns == {"confirmation_source", "auto_confirm_reasons"}


@pytest.mark.integration
def test_prompt_analytics_has_reverted_flag(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'prompt_analytics' AND column_name = 'auto_confirm_reverted'"
        )
        row = cur.fetchone()
    conn.close()

    # Assert
    assert row is not None
    assert "false" in row[0]


@pytest.mark.integration
def test_pg_trgm_installed_in_test_container(migrated_db):
    # Arrange
    conn = _connect(migrated_db)

    # Act
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        row = cur.fetchone()
    conn.close()

    # Assert
    assert row is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/integration/test_auto_confirm_migrations.py -q --no-cov`
Expected: 3 FAIL (columns/extension missing).

- [ ] **Step 3: Write the migrations**

```sql
-- backend/migrations/20260930_03_pg-trgm.sql
-- depends: 20260930_02_receipts-scans-ocr-raw

-- pg_trgm may be unavailable on a managed Postgres without CREATE privileges;
-- the application falls back to rapidfuzz in that case.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION
    WHEN insufficient_privilege OR undefined_file THEN
        RAISE NOTICE 'pg_trgm not available: %', SQLERRM;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        CREATE INDEX IF NOT EXISTS idx_products_alternative_names_name_trgm
            ON products_alternative_names USING gin (name gin_trgm_ops);
    END IF;
END $$;
```

```sql
-- backend/migrations/20260930_04_receipts-scans-auto-confirm.sql
-- depends: 20260930_03_pg-trgm

ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS confirmation_source TEXT,
    ADD COLUMN IF NOT EXISTS auto_confirm_reasons JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'receipts_scans_confirmation_source_check'
    ) THEN
        ALTER TABLE receipts_scans
            ADD CONSTRAINT receipts_scans_confirmation_source_check
            CHECK (confirmation_source IS NULL OR confirmation_source IN ('manual', 'auto'));
    END IF;
END $$;

UPDATE receipts_scans SET confirmation_source = 'manual'
WHERE status = 'done' AND confirmation_source IS NULL;
```

```sql
-- backend/migrations/20260930_05_prompt-analytics-auto-confirm-reverted.sql
-- depends: 20260930_04_receipts-scans-auto-confirm

ALTER TABLE prompt_analytics
    ADD COLUMN IF NOT EXISTS auto_confirm_reverted BOOLEAN NOT NULL DEFAULT FALSE;
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && ../venv/bin/python -m pytest tests/integration/test_auto_confirm_migrations.py -q --no-cov`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/20260930_0[345]_*.sql backend/tests/integration/test_auto_confirm_migrations.py
git commit -m "feat(backend): migrations for receipt auto-confirm and pg_trgm"
```

---

### Task 2: Auto-confirm rules (pure `evaluate`)

**Files:**
- Create: `backend/src/services/receipt_auto_confirm.py`
- Test: `backend/tests/unit/test_receipt_auto_confirm.py`

**Interfaces:**
- Consumes: `TransactionModel`, `ProductItem` from `src/data.py`.
- Produces:
  - `SOURCE_HISTORY = "history"`, `SOURCE_AI = "ai"`
  - `AutoConfirmSettings(enabled: bool=False, min_ai_confidence: float=0.9, history_min_count: int=2, history_min_share: float=0.9)` with `@classmethod from_env() -> AutoConfirmSettings`
  - `ProductResolution(raw_name: str, product_id: int | None, normalized_name: str | None, category_id: int | None, category_name: str | None, source: str | None, confidence: float, history_count: int = 0)`
  - `AutoConfirmReason(code: str, message: str, blocking: bool)` with `to_dict() -> dict`
  - `AutoConfirmDecision(ok: bool, reasons: list[AutoConfirmReason])`
  - `normalize_score(score: float) -> float`
  - `evaluate(transaction: TransactionModel, resolutions: list[ProductResolution], vendor_has_history: bool, settings: AutoConfirmSettings) -> AutoConfirmDecision`
  - `evaluation_error_reason() -> AutoConfirmReason`, `confirm_failed_reason() -> AutoConfirmReason`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_receipt_auto_confirm.py
import pytest

from src.data import ProductItem, TransactionModel
from src.services.receipt_auto_confirm import (
    AutoConfirmSettings,
    ProductResolution,
    evaluate,
    normalize_score,
)

SETTINGS = AutoConfirmSettings(enabled=True, min_ai_confidence=0.9, history_min_count=2, history_min_share=0.9)


def _tx(products, total):
    return TransactionModel(vendor="Lidl", title="PARAGON FISKALNY", products=products, total=total, date="2026-09-30")


def _history(name, category_id=1):
    return ProductResolution(name, 10, "Mleko", category_id, "Nabiał", "history", 0.95, 5)


def _ai(name, confidence, category_id=2):
    return ProductResolution(name, None, None, category_id, "Pieczywo", "ai", confidence, 0)


@pytest.mark.unit
def test_all_history_and_sum_matches_is_ok():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 3.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=True, settings=SETTINGS)

    # Assert
    assert decision.ok is True
    assert decision.reasons == []


@pytest.mark.unit
def test_sum_mismatch_blocks_with_polish_message():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=47.30)], 49.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=True, settings=SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "sum_mismatch"
    assert decision.reasons[0].message == "Suma produktów 47,30 zł ≠ 49,99 zł"
    assert decision.reasons[0].blocking is True


@pytest.mark.unit
def test_discount_lines_count_towards_sum():
    # Arrange
    tx = _tx(
        [ProductItem(name="MALINY", quantity=1, price=10.00), ProductItem(name="OPUST MALINY", quantity=1, price=-2.50)],
        7.50,
    )

    # Act
    decision = evaluate(tx, [_history("MALINY"), _history("OPUST MALINY", 3)], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_sum_within_one_grosz_tolerance_is_ok():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 4.00)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_low_ai_confidence_blocks():
    # Arrange
    tx = _tx([ProductItem(name="SER KOZI 150G", quantity=1, price=9.99)], 9.99)

    # Act
    decision = evaluate(tx, [_ai("SER KOZI 150G", 0.62)], True, SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "low_confidence"
    assert decision.reasons[0].message == "Nowy produkt „SER KOZI 150G”: pewność AI 62%"


@pytest.mark.unit
def test_high_ai_confidence_passes():
    # Arrange
    tx = _tx([ProductItem(name="BULKA", quantity=1, price=0.99)], 0.99)

    # Act
    decision = evaluate(tx, [_ai("BULKA", 0.93)], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_product_without_resolution_blocks():
    # Arrange
    tx = _tx([ProductItem(name="X", quantity=1, price=1.0)], 1.0)

    # Act
    decision = evaluate(tx, [], True, SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "no_category"
    assert decision.reasons[0].message == "Brak kategorii dla „X”"


@pytest.mark.unit
def test_new_vendor_is_non_blocking_reason():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 3.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=False, settings=SETTINGS)

    # Assert
    assert decision.ok is True
    assert [(r.code, r.blocking) for r in decision.reasons] == [("vendor_new", False)]
    assert decision.reasons[0].message == "Pierwszy paragon ze sklepu „Lidl”"


@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", [(0.87, 0.87), (87.0, 0.87), (1.0, 1.0), (0.0, 0.0)])
def test_normalize_score_accepts_fraction_or_percent(raw, expected):
    # Act / Assert
    assert normalize_score(raw) == pytest.approx(expected)


@pytest.mark.unit
def test_settings_from_env(monkeypatch):
    # Arrange
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_ENABLED", "true")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE", "0.8")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT", "3")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE", "0.75")

    # Act
    settings = AutoConfirmSettings.from_env()

    # Assert
    assert settings == AutoConfirmSettings(True, 0.8, 3, 0.75)


@pytest.mark.unit
def test_settings_from_env_defaults_disabled(monkeypatch):
    # Arrange
    for key in (
        "RECEIPT_AUTO_CONFIRM_ENABLED",
        "RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE",
        "RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT",
        "RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE",
    ):
        monkeypatch.delenv(key, raising=False)

    # Act
    settings = AutoConfirmSettings.from_env()

    # Assert
    assert settings == AutoConfirmSettings()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_auto_confirm.py -q --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.services.receipt_auto_confirm'`.

- [ ] **Step 3: Implement**

```python
# backend/src/services/receipt_auto_confirm.py
from __future__ import annotations

import os
from dataclasses import dataclass

from ..data import TransactionModel

SOURCE_HISTORY = "history"
SOURCE_AI = "ai"
SUM_TOLERANCE = 0.01


@dataclass(frozen=True)
class AutoConfirmSettings:
    enabled: bool = False
    min_ai_confidence: float = 0.9
    history_min_count: int = 2
    history_min_share: float = 0.9

    @classmethod
    def from_env(cls) -> "AutoConfirmSettings":
        enabled_raw = os.getenv("RECEIPT_AUTO_CONFIRM_ENABLED", "false").strip().lower()
        return cls(
            enabled=enabled_raw in ("1", "true", "yes"),
            min_ai_confidence=float(os.getenv("RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE", "0.9")),
            history_min_count=int(os.getenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT", "2")),
            history_min_share=float(os.getenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE", "0.9")),
        )


@dataclass(frozen=True)
class ProductResolution:
    raw_name: str
    product_id: int | None
    normalized_name: str | None
    category_id: int | None
    category_name: str | None
    source: str | None
    confidence: float
    history_count: int = 0


@dataclass(frozen=True)
class AutoConfirmReason:
    code: str
    message: str
    blocking: bool

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "blocking": self.blocking}


@dataclass(frozen=True)
class AutoConfirmDecision:
    ok: bool
    reasons: list[AutoConfirmReason]


def normalize_score(score: float) -> float:
    return score / 100.0 if score > 1.0 else score


def evaluation_error_reason() -> AutoConfirmReason:
    return AutoConfirmReason("evaluation_error", "Nie udało się ocenić automatycznie", True)


def confirm_failed_reason() -> AutoConfirmReason:
    return AutoConfirmReason("confirm_failed", "Automatyczne potwierdzenie nie powiodło się", True)


def _pln(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " zł"


def evaluate(
    transaction: TransactionModel,
    resolutions: list[ProductResolution],
    vendor_has_history: bool,
    settings: AutoConfirmSettings,
) -> AutoConfirmDecision:
    reasons: list[AutoConfirmReason] = []

    products_sum = round(sum(p.price for p in transaction.products), 2)
    if abs(products_sum - transaction.total) > SUM_TOLERANCE + 1e-9:
        reasons.append(AutoConfirmReason(
            "sum_mismatch",
            f"Suma produktów {_pln(products_sum)} ≠ {_pln(transaction.total)}",
            True,
        ))

    by_name = {r.raw_name: r for r in resolutions}
    for name in dict.fromkeys(p.name for p in transaction.products):
        resolution = by_name.get(name)
        if resolution is None or resolution.category_id is None:
            reasons.append(AutoConfirmReason("no_category", f"Brak kategorii dla „{name}”", True))
        elif resolution.source == SOURCE_AI and resolution.confidence < settings.min_ai_confidence:
            reasons.append(AutoConfirmReason(
                "low_confidence",
                f"Nowy produkt „{name}”: pewność AI {round(resolution.confidence * 100)}%",
                True,
            ))

    if not vendor_has_history:
        reasons.append(AutoConfirmReason(
            "vendor_new", f"Pierwszy paragon ze sklepu „{transaction.vendor}”", False
        ))

    return AutoConfirmDecision(ok=not any(r.blocking for r in reasons), reasons=reasons)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_auto_confirm.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/receipt_auto_confirm.py backend/tests/unit/test_receipt_auto_confirm.py
git commit -m "feat(backend): pure auto-confirm gate for receipts"
```

---

### Task 3: Category history (verdict + repository)

**Files:**
- Create: `backend/src/services/category_history.py`
- Create: `backend/src/repositories/category_history.py`
- Test: `backend/tests/unit/test_category_history.py`

**Interfaces:**
- Produces:
  - `HistoryVerdict(category_id: int, category_name: str, count: int, share: float)`
  - `dominant_category(counts: dict[int, tuple[str, int]], min_count: int, min_share: float) -> HistoryVerdict | None` (`counts` = `{category_id: (category_name, count)}`)
  - `CategoryHistoryRepository(db_context)` with
    - `get_category_counts(product_ids: list[int]) -> dict[int, dict[int, tuple[str, int]]]` (`{product_id: {category_id: (name, count)}}`)
    - `vendor_has_confirmed_receipts(vendor_id: int | None) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_category_history.py
import pytest
from unittest.mock import MagicMock

from src.repositories.category_history import CategoryHistoryRepository
from src.services.category_history import HistoryVerdict, dominant_category


def _repo(fetchall=None, fetchone=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    repo = CategoryHistoryRepository.__new__(CategoryHistoryRepository)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_dominant_category_returns_verdict_above_thresholds():
    # Act
    verdict = dominant_category({1: ("Nabiał", 14), 2: ("Słodycze", 1)}, min_count=2, min_share=0.9)

    # Assert
    assert verdict == HistoryVerdict(1, "Nabiał", 14, pytest.approx(14 / 15))


@pytest.mark.unit
def test_dominant_category_none_when_count_too_low():
    # Act / Assert
    assert dominant_category({1: ("Nabiał", 1)}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_dominant_category_none_when_share_too_low():
    # Act / Assert
    assert dominant_category({1: ("Nabiał", 5), 2: ("Słodycze", 5)}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_dominant_category_none_for_empty_history():
    # Act / Assert
    assert dominant_category({}, min_count=2, min_share=0.9) is None


@pytest.mark.unit
def test_get_category_counts_groups_by_product():
    # Arrange
    repo, cursor = _repo(fetchall=[(10, 1, "Nabiał", 3), (10, 2, "Słodycze", 1), (11, 5, "Pieczywo", 2)])

    # Act
    result = repo.get_category_counts([10, 11])

    # Assert
    assert result == {10: {1: ("Nabiał", 3), 2: ("Słodycze", 1)}, 11: {5: ("Pieczywo", 2)}}
    sql, params = cursor.execute.call_args[0]
    assert "COALESCE(rti.product_id, pan.product)" in sql
    assert params == ([10, 11],)


@pytest.mark.unit
def test_get_category_counts_empty_ids_skips_query():
    # Arrange
    repo, cursor = _repo()

    # Act
    result = repo.get_category_counts([])

    # Assert
    assert result == {}
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_get_category_counts_db_error_rolls_back():
    # Arrange
    repo, cursor = _repo()
    cursor.execute.side_effect = Exception("boom")

    # Act
    result = repo.get_category_counts([1])

    # Assert
    assert result == {}
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_vendor_has_confirmed_receipts_true():
    # Arrange
    repo, _ = _repo(fetchone=(True,))

    # Act / Assert
    assert repo.vendor_has_confirmed_receipts(3) is True


@pytest.mark.unit
def test_vendor_has_confirmed_receipts_none_vendor_is_false():
    # Arrange
    repo, cursor = _repo()

    # Act / Assert
    assert repo.vendor_has_confirmed_receipts(None) is False
    cursor.execute.assert_not_called()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_category_history.py -q --no-cov`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/services/category_history.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryVerdict:
    category_id: int
    category_name: str
    count: int
    share: float


def dominant_category(
    counts: dict[int, tuple[str, int]],
    min_count: int,
    min_share: float,
) -> HistoryVerdict | None:
    total = sum(count for _, count in counts.values())
    if total == 0:
        return None
    category_id, (category_name, count) = max(counts.items(), key=lambda kv: kv[1][1])
    share = count / total
    if count < min_count or share < min_share:
        return None
    return HistoryVerdict(category_id, category_name, count, share)
```

```python
# backend/src/repositories/category_history.py
from abc import ABC


class CategoryHistoryRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def get_category_counts(self, product_ids: list[int]) -> dict[int, dict[int, tuple[str, int]]]:
        """Confirmed category counts per normalized product.

        Legacy items may have product_id NULL; they are attributed through
        products_alternative_names by raw name.
        """
        if not self.conn or not product_ids:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(rti.product_id, pan.product) AS pid,
                           rti.category_id,
                           c.name,
                           COUNT(*)
                    FROM receipt_transaction_items rti
                    LEFT JOIN products_alternative_names pan ON pan.name = rti.raw_product_name
                    JOIN categories c ON c.id = rti.category_id
                    WHERE COALESCE(rti.product_id, pan.product) = ANY(%s)
                    GROUP BY 1, 2, 3
                    """,
                    (list(product_ids),),
                )
                result: dict[int, dict[int, tuple[str, int]]] = {}
                for product_id, category_id, category_name, count in cursor.fetchall():
                    result.setdefault(product_id, {})[category_id] = (category_name, int(count))
                return result
        except Exception as e:
            print("Failed to fetch category history:", e)
            self.conn.rollback()
            return {}

    def vendor_has_confirmed_receipts(self, vendor_id: int | None) -> bool:
        if not self.conn or vendor_id is None:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM receipt_transactions WHERE vendor_id = %s)",
                    (vendor_id,),
                )
                row = cursor.fetchone()
                return bool(row and row[0])
        except Exception as e:
            print("Failed to check vendor history:", e)
            self.conn.rollback()
            return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_category_history.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/category_history.py backend/src/repositories/category_history.py backend/tests/unit/test_category_history.py
git commit -m "feat(backend): category history verdict and repository"
```

---

### Task 4: Product/vendor repository extensions

**Files:**
- Modify: `backend/src/repositories/products.py` (append methods)
- Modify: `backend/src/repositories/vendors.py` (append method)
- Modify: `backend/requirements.txt` (add `rapidfuzz>=3.9.0`)
- Test: `backend/tests/unit/test_products_repository_similarity.py`
- Test: `backend/tests/integration/test_products_similarity.py`

**Interfaces:**
- Produces on `ProductsRepository`:
  - `has_trigram_support() -> bool`
  - `find_similar_alternative_names(name: str, limit: int = 10, min_similarity: float = 0.3) -> list[tuple[str, int, float]]` → `(alt_name, product_id, similarity)` sorted desc
  - `get_all_alternative_names() -> list[tuple[str, int]]`
  - `get_names_by_ids(product_ids: list[int]) -> dict[int, str]`
  - `upsert_alternative_name(alternative_name: str, product_id: int) -> bool` (overwrites mapping)
- Produces on `VendorsRepository`: `upsert_alternative_name(alternative_name: str, vendor_id: int) -> bool`

- [ ] **Step 1: Write the failing unit tests**

```python
# backend/tests/unit/test_products_repository_similarity.py
import pytest
from unittest.mock import MagicMock

from src.repositories.products import ProductsRepository
from src.repositories.vendors import VendorsRepository


def _repo(cls, fetchall=None, fetchone=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    repo = cls.__new__(cls)
    repo.conn = conn
    return repo, cursor


@pytest.mark.unit
def test_has_trigram_support_true():
    # Arrange
    repo, _ = _repo(ProductsRepository, fetchone=(True,))

    # Act / Assert
    assert repo.has_trigram_support() is True


@pytest.mark.unit
def test_has_trigram_support_error_is_false():
    # Arrange
    repo, cursor = _repo(ProductsRepository)
    cursor.execute.side_effect = Exception("boom")

    # Act / Assert
    assert repo.has_trigram_support() is False


@pytest.mark.unit
def test_find_similar_alternative_names_maps_rows():
    # Arrange
    repo, cursor = _repo(ProductsRepository, fetchall=[("MLEKO 2%", 4, 0.72)])

    # Act
    rows = repo.find_similar_alternative_names("MLEKO 3%", limit=5, min_similarity=0.3)

    # Assert
    assert rows == [("MLEKO 2%", 4, 0.72)]
    sql, params = cursor.execute.call_args[0]
    assert "similarity(name, %s)" in sql
    assert params == ("MLEKO 3%", "MLEKO 3%", "MLEKO 3%", 0.3, 5)


@pytest.mark.unit
def test_find_similar_alternative_names_error_rolls_back_and_raises():
    # Arrange
    repo, cursor = _repo(ProductsRepository)
    cursor.execute.side_effect = Exception("function similarity does not exist")

    # Act / Assert
    with pytest.raises(Exception):
        repo.find_similar_alternative_names("X")
    repo.conn.rollback.assert_called_once()


@pytest.mark.unit
def test_get_all_alternative_names():
    # Arrange
    repo, _ = _repo(ProductsRepository, fetchall=[("A", 1), ("B", 2)])

    # Act / Assert
    assert repo.get_all_alternative_names() == [("A", 1), ("B", 2)]


@pytest.mark.unit
def test_get_names_by_ids():
    # Arrange
    repo, cursor = _repo(ProductsRepository, fetchall=[(1, "Mleko"), (2, "Chleb")])

    # Act
    result = repo.get_names_by_ids([1, 2])

    # Assert
    assert result == {1: "Mleko", 2: "Chleb"}
    assert cursor.execute.call_args[0][1] == ([1, 2],)


@pytest.mark.unit
def test_get_names_by_ids_empty_skips_query():
    # Arrange
    repo, cursor = _repo(ProductsRepository)

    # Act / Assert
    assert repo.get_names_by_ids([]) == {}
    cursor.execute.assert_not_called()


@pytest.mark.unit
def test_product_upsert_alternative_name_overwrites():
    # Arrange
    repo, cursor = _repo(ProductsRepository)

    # Act
    ok = repo.upsert_alternative_name("MLEKO", 7)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "ON CONFLICT (name) DO UPDATE SET product = EXCLUDED.product" in sql
    assert params == ("MLEKO", 7)
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_vendor_upsert_alternative_name_overwrites():
    # Arrange
    repo, cursor = _repo(VendorsRepository)

    # Act
    ok = repo.upsert_alternative_name("BIEDRONKA 1234", 3)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "ON CONFLICT (name) DO UPDATE SET vendor = EXCLUDED.vendor" in sql
    assert params == ("BIEDRONKA 1234", 3)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_products_repository_similarity.py -q --no-cov`
Expected: FAIL with `AttributeError: ... has no attribute 'has_trigram_support'`.

- [ ] **Step 3: Implement — append to `ProductsRepository`**

```python
    def has_trigram_support(self) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')")
                row = cursor.fetchone()
                return bool(row and row[0])
        except Exception as e:
            print(f"Failed to check pg_trgm: {e}")
            self.conn.rollback()
            return False

    def find_similar_alternative_names(
        self, name: str, limit: int = 10, min_similarity: float = 0.3
    ) -> List[tuple[str, int, float]]:
        """Trigram search over raw receipt names. Raises when pg_trgm is unavailable."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT name, product, similarity(name, %s) AS score
                    FROM products_alternative_names
                    WHERE name %% %s AND similarity(name, %s) >= %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (name, name, name, min_similarity, limit),
                )
                return [(r[0], r[1], float(r[2])) for r in cursor.fetchall()]
        except Exception:
            self.conn.rollback()
            raise

    def get_all_alternative_names(self) -> List[tuple[str, int]]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT name, product FROM products_alternative_names")
                return [(r[0], r[1]) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Failed to list alternative names: {e}")
            self.conn.rollback()
            return []

    def get_names_by_ids(self, product_ids: List[int]) -> dict[int, str]:
        if not self.conn or not product_ids:
            return {}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM products WHERE id = ANY(%s)", (list(product_ids),))
                return {r[0]: r[1] for r in cursor.fetchall()}
        except Exception as e:
            print(f"Failed to get product names: {e}")
            self.conn.rollback()
            return {}

    def upsert_alternative_name(self, alternative_name: str, product_id: int) -> bool:
        """Link a raw name to a product, replacing any previous mapping."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO products_alternative_names (name, product) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET product = EXCLUDED.product",
                    (alternative_name, product_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Failed to upsert alternative name: {e}")
            self.conn.rollback()
            return False
```

Append to `VendorsRepository`:

```python
    def upsert_alternative_name(self, alternative_name: str, vendor_id: int) -> bool:
        """Link a raw vendor name to a vendor, replacing any previous mapping."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO vendors_alternative_names (name, vendor) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET vendor = EXCLUDED.vendor",
                    (alternative_name, vendor_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Failed to upsert vendor alternative name: {e}")
            self.conn.rollback()
            return False
```

Add to `backend/requirements.txt` after `cachetools>=5.3.0`:

```
rapidfuzz>=3.9.0
```

Then install: `cd backend && ../venv/bin/pip install "rapidfuzz>=3.9.0"`

- [ ] **Step 4: Write the integration test**

```python
# backend/tests/integration/test_products_similarity.py
import pytest


@pytest.mark.integration
def test_find_similar_alternative_names_tolerates_ocr_diacritics(integration_app):
    # Arrange
    repo = integration_app.products_repository
    product_id = repo.insert_product("Mleko")
    repo.insert_alternative_name("MLEKO ŁACIĄTE 2% 1L C", product_id)

    # Act
    rows = repo.find_similar_alternative_names("MLEKO LACIATE 2% 1L C")

    # Assert
    assert rows
    assert rows[0][1] == product_id
    assert rows[0][2] >= 0.3


@pytest.mark.integration
def test_upsert_alternative_name_replaces_mapping(integration_app):
    # Arrange
    repo = integration_app.products_repository
    wrong = repo.insert_product("Ser")
    right = repo.insert_product("Masło")
    repo.insert_alternative_name("MASLO EXTRA 200G", wrong)

    # Act
    repo.upsert_alternative_name("MASLO EXTRA 200G", right)

    # Assert
    assert repo.get_product_by_alternative_name("MASLO EXTRA 200G") == right
```

- [ ] **Step 5: Run unit + integration**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_products_repository_similarity.py tests/unit/test_products_repository.py tests/unit/test_vendors_repository.py -q --no-cov && ../venv/bin/python -m pytest tests/integration/test_products_similarity.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/repositories/products.py backend/src/repositories/vendors.py backend/requirements.txt backend/tests/unit/test_products_repository_similarity.py backend/tests/integration/test_products_similarity.py
git commit -m "feat(backend): trigram product search and overwriting alias upserts"
```

---

### Task 5: LLM services — product resolution call and few-shot categories

**Files:**
- Modify: `backend/src/data.py` (add models after `ProductMappings`)
- Modify: `backend/src/services/products.py` (add `resolve_products`)
- Modify: `backend/src/services/categories.py` (`category_ids`, `examples`)
- Test: `backend/tests/unit/test_services_llm_resolution.py`

**Interfaces:**
- Produces in `data.py`:
  - `ProductResolutionLLMItem(raw_name: str, product_id: int | None = None, new_product_name: str | None = None)`
  - `ProductResolutionsLLM(items: List[ProductResolutionLLMItem])`
- Produces `ProductsService.resolve_products(items: list[tuple[str, list[NormalizedProductItem]]]) -> ProductResolutionsLLM`
- Produces `CategoriesService.category_ids: set[int]` (filled by `build()`), `CategoriesService.assign_category_candidates(transaction_model, examples: list[tuple[str, str]] | None = None) -> dict`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_services_llm_resolution.py
import json
import pytest
from unittest.mock import MagicMock

from src.data import NormalizedProductItem, ProductItem, TransactionModel
from src.services.categories import CategoriesService
from src.services.products import ProductsService


def _client_returning(arguments: dict) -> MagicMock:
    client = MagicMock()
    call = MagicMock()
    call.type = "function_call"
    call.arguments = json.dumps(arguments)
    client.responses.create.return_value.output = [call]
    return client


def _prompt_text(client: MagicMock) -> str:
    kwargs = client.responses.create.call_args.kwargs
    return kwargs["input"][0]["content"][0]["text"]


@pytest.mark.unit
def test_resolve_products_lists_candidates_and_parses_response():
    # Arrange
    client = _client_returning({"items": [{"raw_name": "MLEKO 2%", "product_id": 4, "new_product_name": None}]})
    svc = ProductsService(client=client)

    # Act
    result = svc.resolve_products([("MLEKO 2%", [NormalizedProductItem(id=4, name="Mleko")])])

    # Assert
    assert result.items[0].product_id == 4
    text = _prompt_text(client)
    assert "MLEKO 2%" in text
    assert "[4] Mleko" in text


@pytest.mark.unit
def test_resolve_products_marks_missing_candidates():
    # Arrange
    client = _client_returning({"items": [{"raw_name": "SER KOZI", "product_id": None, "new_product_name": "Ser kozi"}]})
    svc = ProductsService(client=client)

    # Act
    result = svc.resolve_products([("SER KOZI", [])])

    # Assert
    assert result.items[0].new_product_name == "Ser kozi"
    assert "SER KOZI | kandydaci: brak" in _prompt_text(client)


@pytest.mark.unit
def test_resolve_products_raises_without_function_call():
    # Arrange
    client = MagicMock()
    client.responses.create.return_value.output = []
    svc = ProductsService(client=client)

    # Act / Assert
    with pytest.raises(ValueError):
        svc.resolve_products([("X", [])])


@pytest.mark.unit
def test_assign_category_candidates_appends_examples():
    # Arrange
    client = _client_returning({"category_candidates": []})
    svc = CategoriesService(db_context=MagicMock(), client=client)
    svc.categories = "| category_id |"
    tx = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="SER", quantity=1, price=5)], total=5, date="2026-09-30")

    # Act
    svc.assign_category_candidates(tx, examples=[("SER GOUDA 150G", "Nabiał")])

    # Assert
    text = _prompt_text(client)
    assert "- SER GOUDA 150G -> Nabiał" in text


@pytest.mark.unit
def test_assign_category_candidates_without_examples_has_no_examples_block():
    # Arrange
    client = _client_returning({"category_candidates": []})
    svc = CategoriesService(db_context=MagicMock(), client=client)
    tx = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="SER", quantity=1, price=5)], total=5, date="2026-09-30")

    # Act
    svc.assign_category_candidates(tx)

    # Assert
    assert "Previously confirmed" not in _prompt_text(client)


@pytest.mark.unit
def test_build_collects_category_ids():
    # Arrange
    svc = CategoriesService(db_context=MagicMock(), client=MagicMock())
    svc.categories_repository = MagicMock()
    svc.categories_repository.get_categories.return_value = [(1, "Nabiał", "Jedzenie"), (2, "Pieczywo", "Jedzenie")]

    # Act
    svc.build()

    # Assert
    assert svc.category_ids == {1, 2}
    assert "Nabiał" in svc.categories
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_services_llm_resolution.py -q --no-cov`
Expected: FAIL (`ImportError`/`AttributeError`).

- [ ] **Step 3: Implement**

Add to `backend/src/data.py` directly after `class ProductMappings`:

```python
class ProductResolutionLLMItem(BaseModel):
    """LLM decision for one raw receipt product name."""
    raw_name: str = Field(..., description="The product name exactly as given in the input list.")
    product_id: int | None = Field(
        default=None,
        description="ID of the matching existing product from this name's candidate list, or null if none fits.",
    )
    new_product_name: str | None = Field(
        default=None,
        description="Normalized, generic Polish product name to create when product_id is null.",
    )


class ProductResolutionsLLM(BaseModel):
    """LLM tool-call schema for resolving raw receipt names to existing products."""
    items: List[ProductResolutionLLMItem] = Field(..., description="One decision per input product name.")
```

In `backend/src/services/products.py` update the import and add the method:

```python
from ..data import NormalizedProductItem, ProductItem, ProductMappings, ProductResolutionsLLM
```

```python
    def resolve_products(
        self, items: List[tuple[str, List[NormalizedProductItem]]]
    ) -> ProductResolutionsLLM:
        """Pick an existing product for each raw name or propose a new normalized name."""
        lines = []
        for raw_name, candidates in items:
            listed = ", ".join(f"[{c.id}] {c.name}" for c in candidates) or "brak"
            lines.append(f"- {raw_name} | kandydaci: {listed}")
        full_prompt = (
            "For each Polish receipt product name below, choose the existing normalized product that "
            "denotes the same generic product (ignore brands, sizes, weights and OCR typos) from that "
            "name's candidate list and return its product_id. Only use IDs from that name's own list. "
            "If no candidate fits, return product_id null and new_product_name following these rules:\n"
            f"{self.prompt}\n\nProducts:\n" + "\n".join(lines)
        )
        tool_name = "resolve_product_names"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Resolve Polish receipt product names to existing normalized products",
                "parameters": ProductResolutionsLLM.model_json_schema(),
            }
        ]
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[{"role": "user", "content": [{"type": "input_text", "text": full_prompt}]}],
        )
        tool_call = next((item for item in response.output if item.type == "function_call"), None)
        if tool_call is None:
            raise ValueError("No function call found in OpenAI response")
        return ProductResolutionsLLM(**json.loads(tool_call.arguments))
```

In `backend/src/services/categories.py`:
- in `__init__` add `self.category_ids: set[int] = set()` after `self.categories = ""`;
- replace `build` and change `assign_category_candidates` signature + prompt building:

```python
    def build(self):
        rows = self.categories_repository.get_categories() or []
        self.category_ids = {row[0] for row in rows}
        self.categories = self._map_categories(rows)
```

```python
    def assign_category_candidates(
        self,
        transaction_model: TransactionModel,
        examples: list[tuple[str, str]] | None = None,
    ):
        tool_name = "get_category_candidates"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Get category candidates for each product in the transaction",
                "parameters": CategoryCandidatesProducts.model_json_schema(),
            }
        ]
        prompt = self.prompt.format(
            self.categories,
            transaction_model.model_dump_json(),
        )
        if examples:
            lines = "\n".join(f"- {name} -> {category}" for name, category in examples)
            prompt += (
                "\nPreviously confirmed assignments of similar products "
                "(treat them as strong hints):\n" + lines
            )
        # ... unchanged: self.client.responses.create(...) using `prompt`, parse tool call, return args
```

- [ ] **Step 4: Run to verify it passes (plus existing LLM tests)**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_services_llm_resolution.py tests/unit/test_services_llm.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/data.py backend/src/services/products.py backend/src/services/categories.py backend/tests/unit/test_services_llm_resolution.py
git commit -m "feat(backend): LLM product resolution and few-shot category hints"
```

---

### Task 6: `ProductResolver`

**Files:**
- Create: `backend/src/services/product_resolver.py`
- Test: `backend/tests/unit/test_product_resolver.py`

**Interfaces:**
- Consumes: `ProductsRepository` methods from Task 4 plus existing `get_product_by_alternative_name`, `get_product_by_name`, `insert_product`, `insert_alternative_name`; `ProductsService.resolve_products` (Task 5).
- Produces:
  - `FUZZY_AUTO_ACCEPT = 0.85`, `SHORTLIST_SIZE = 10`, `SHORTLIST_MIN_SIMILARITY = 0.3`
  - `SimilarName(name: str, product_id: int, score: float)`
  - `ResolvedProduct(raw_name: str, product_id: int | None, normalized_name: str | None, method: str, similar: list[SimilarName])` — `method ∈ {"exact","fuzzy","llm_existing","llm_new","unresolved"}`
  - `ProductResolver(products_repository, products_service)` with `resolve(raw_names: list[str]) -> list[ResolvedProduct]` (same order/length as input) and `find_similar(raw_name: str) -> list[SimilarName]`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_product_resolver.py
import pytest
from unittest.mock import MagicMock

from src.data import ProductResolutionLLMItem, ProductResolutionsLLM
from src.services.product_resolver import ProductResolver


def _resolver(trgm=True):
    repo = MagicMock()
    repo.has_trigram_support.return_value = trgm
    repo.get_product_by_alternative_name.return_value = None
    repo.find_similar_alternative_names.return_value = []
    repo.get_names_by_ids.side_effect = lambda ids: {i: f"P{i}" for i in ids}
    service = MagicMock()
    return ProductResolver(repo, service), repo, service


@pytest.mark.unit
def test_exact_match_skips_llm():
    # Arrange
    resolver, repo, service = _resolver()
    repo.get_product_by_alternative_name.return_value = 5

    # Act
    result = resolver.resolve(["MLEKO"])

    # Assert
    assert result[0].product_id == 5
    assert result[0].method == "exact"
    assert result[0].normalized_name == "P5"
    service.resolve_products.assert_not_called()


@pytest.mark.unit
def test_high_similarity_is_auto_accepted_and_linked():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("MLEKO ŁACIATE", 7, 0.9)]

    # Act
    result = resolver.resolve(["MLEKO LACIATE"])

    # Assert
    assert result[0].method == "fuzzy"
    assert result[0].product_id == 7
    repo.insert_alternative_name.assert_called_once_with("MLEKO LACIATE", 7)
    service.resolve_products.assert_not_called()


@pytest.mark.unit
def test_medium_similarity_goes_to_llm_and_accepts_listed_id():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("SER GOUDA", 3, 0.5)]
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="SER EDAM", product_id=3)]
    )

    # Act
    result = resolver.resolve(["SER EDAM"])

    # Assert
    assert result[0].method == "llm_existing"
    assert result[0].product_id == 3
    repo.insert_alternative_name.assert_called_once_with("SER EDAM", 3)
    items = service.resolve_products.call_args[0][0]
    assert items[0][0] == "SER EDAM"
    assert [c.id for c in items[0][1]] == [3]


@pytest.mark.unit
def test_llm_id_outside_shortlist_is_treated_as_new():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("SER GOUDA", 3, 0.5)]
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="SER EDAM", product_id=999, new_product_name="Ser")]
    )
    repo.get_product_by_name.return_value = None
    repo.insert_product.return_value = 12

    # Act
    result = resolver.resolve(["SER EDAM"])

    # Assert
    assert result[0].method == "llm_new"
    assert result[0].product_id == 12
    repo.insert_product.assert_called_once_with("Ser")


@pytest.mark.unit
def test_llm_new_reuses_existing_product_by_name():
    # Arrange
    resolver, repo, service = _resolver()
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="CHLEB ZYTNI", new_product_name="Chleb")]
    )
    repo.get_product_by_name.return_value = 2

    # Act
    result = resolver.resolve(["CHLEB ZYTNI"])

    # Assert
    assert result[0].product_id == 2
    repo.insert_product.assert_not_called()
    repo.insert_alternative_name.assert_called_once_with("CHLEB ZYTNI", 2)


@pytest.mark.unit
def test_llm_failure_leaves_products_unresolved():
    # Arrange
    resolver, repo, service = _resolver()
    service.resolve_products.side_effect = Exception("openai down")

    # Act
    result = resolver.resolve(["X"])

    # Assert
    assert result[0].method == "unresolved"
    assert result[0].product_id is None


@pytest.mark.unit
def test_duplicate_names_resolved_once_and_order_kept():
    # Arrange
    resolver, repo, service = _resolver()
    repo.get_product_by_alternative_name.side_effect = lambda n: {"RABAT": 1, "MLEKO": 2}[n]

    # Act
    result = resolver.resolve(["RABAT", "MLEKO", "RABAT"])

    # Assert
    assert [r.product_id for r in result] == [1, 2, 1]
    assert repo.get_product_by_alternative_name.call_count == 2


@pytest.mark.unit
def test_rapidfuzz_fallback_without_trigram():
    # Arrange
    resolver, repo, service = _resolver(trgm=False)
    repo.get_all_alternative_names.return_value = [("MLEKO ŁACIĄTE 2% 1L", 7), ("CHLEB", 8)]

    # Act
    similar = resolver.find_similar("MLEKO LACIATE 2% 1L")

    # Assert
    assert similar[0].product_id == 7
    assert 0.0 < similar[0].score <= 1.0
    repo.find_similar_alternative_names.assert_not_called()


@pytest.mark.unit
def test_trigram_error_switches_to_fallback():
    # Arrange
    resolver, repo, service = _resolver(trgm=True)
    repo.find_similar_alternative_names.side_effect = Exception("no similarity()")
    repo.get_all_alternative_names.return_value = [("CHLEB", 8)]

    # Act
    similar = resolver.find_similar("CHLEB")

    # Assert
    assert similar == []  # exact same raw name is excluded from "similar"
    repo.get_all_alternative_names.assert_called_once()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_product_resolver.py -q --no-cov`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/services/product_resolver.py
from __future__ import annotations

from dataclasses import dataclass, replace

from rapidfuzz import fuzz, process, utils

from ..data import NormalizedProductItem

FUZZY_AUTO_ACCEPT = 0.85
SHORTLIST_SIZE = 10
SHORTLIST_MIN_SIMILARITY = 0.3


@dataclass(frozen=True)
class SimilarName:
    name: str
    product_id: int
    score: float


@dataclass(frozen=True)
class ResolvedProduct:
    raw_name: str
    product_id: int | None
    normalized_name: str | None
    method: str
    similar: list[SimilarName]


class ProductResolver:
    def __init__(self, products_repository, products_service):
        self.products_repository = products_repository
        self.products_service = products_service
        self._trigram: bool | None = None
        self._fallback_names: list[tuple[str, int]] | None = None

    def resolve(self, raw_names: list[str]) -> list[ResolvedProduct]:
        resolved: dict[str, ResolvedProduct] = {}
        pending: list[tuple[str, list[SimilarName]]] = []

        for raw_name in dict.fromkeys(raw_names):
            product_id = self.products_repository.get_product_by_alternative_name(raw_name)
            if product_id is not None:
                resolved[raw_name] = ResolvedProduct(raw_name, product_id, None, "exact", [])
                continue
            similar = self.find_similar(raw_name)
            if similar and similar[0].score >= FUZZY_AUTO_ACCEPT:
                best = similar[0]
                self.products_repository.insert_alternative_name(raw_name, best.product_id)
                resolved[raw_name] = ResolvedProduct(raw_name, best.product_id, None, "fuzzy", similar)
                continue
            pending.append((raw_name, similar))

        if pending:
            resolved.update(self._resolve_with_llm(pending))

        ids = [r.product_id for r in resolved.values() if r.product_id is not None]
        names = self.products_repository.get_names_by_ids(sorted(set(ids)))
        return [
            replace(resolved[n], normalized_name=names.get(resolved[n].product_id, resolved[n].normalized_name))
            for n in raw_names
        ]

    def find_similar(self, raw_name: str) -> list[SimilarName]:
        rows: list[tuple[str, int, float]]
        if self._trigram is None:
            self._trigram = self.products_repository.has_trigram_support()
        if self._trigram:
            try:
                rows = self.products_repository.find_similar_alternative_names(
                    raw_name, limit=SHORTLIST_SIZE, min_similarity=SHORTLIST_MIN_SIMILARITY
                )
            except Exception as e:
                print(f"Trigram search failed, falling back to rapidfuzz: {e}")
                self._trigram = False
                rows = self._fuzzy_rows(raw_name)
        else:
            rows = self._fuzzy_rows(raw_name)
        return [SimilarName(name, pid, float(score)) for name, pid, score in rows if name != raw_name]

    def _fuzzy_rows(self, raw_name: str) -> list[tuple[str, int, float]]:
        if self._fallback_names is None:
            self._fallback_names = self.products_repository.get_all_alternative_names()
        choices = {i: name for i, (name, _) in enumerate(self._fallback_names)}
        matches = process.extract(
            raw_name, choices, scorer=fuzz.ratio, processor=utils.default_process, limit=SHORTLIST_SIZE
        )
        rows = []
        for name, score, index in matches:
            normalized = score / 100.0
            if normalized >= SHORTLIST_MIN_SIMILARITY:
                rows.append((name, self._fallback_names[index][1], normalized))
        return rows

    def _resolve_with_llm(self, pending: list[tuple[str, list[SimilarName]]]) -> dict[str, ResolvedProduct]:
        candidate_ids = sorted({s.product_id for _, similar in pending for s in similar})
        names_by_id = self.products_repository.get_names_by_ids(candidate_ids)

        items: list[tuple[str, list[NormalizedProductItem]]] = []
        allowed: dict[str, set[int]] = {}
        for raw_name, similar in pending:
            candidates: list[NormalizedProductItem] = []
            for s in similar:
                if s.product_id in allowed.setdefault(raw_name, set()) or s.product_id not in names_by_id:
                    continue
                allowed[raw_name].add(s.product_id)
                candidates.append(NormalizedProductItem(id=s.product_id, name=names_by_id[s.product_id]))
            items.append((raw_name, candidates))

        try:
            decisions = {i.raw_name: i for i in self.products_service.resolve_products(items).items}
        except Exception as e:
            print(f"LLM product resolution failed: {e}")
            decisions = {}

        out: dict[str, ResolvedProduct] = {}
        for raw_name, similar in pending:
            decision = decisions.get(raw_name)
            if decision and decision.product_id in allowed.get(raw_name, set()):
                self.products_repository.insert_alternative_name(raw_name, decision.product_id)
                out[raw_name] = ResolvedProduct(raw_name, decision.product_id, None, "llm_existing", similar)
                continue
            new_name = decision.new_product_name.strip() if decision and decision.new_product_name else ""
            if not new_name:
                out[raw_name] = ResolvedProduct(raw_name, None, None, "unresolved", similar)
                continue
            product_id = self.products_repository.get_product_by_name(new_name)
            if product_id is None:
                product_id = self.products_repository.insert_product(new_name)
            if product_id is not None:
                self.products_repository.insert_alternative_name(raw_name, product_id)
            out[raw_name] = ResolvedProduct(raw_name, product_id, new_name, "llm_new", similar)
        return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_product_resolver.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/product_resolver.py backend/tests/unit/test_product_resolver.py
git commit -m "feat(backend): product resolver with trigram, rapidfuzz fallback and LLM shortlist"
```

---

### Task 7: `ReceiptCategorizationService`

**Files:**
- Create: `backend/src/services/receipt_categorization.py`
- Test: `backend/tests/unit/test_receipt_categorization.py`

**Interfaces:**
- Consumes: `ProductResolver.resolve/find_similar` (Task 6), `CategoriesService.assign_category_candidates(tx, examples=...)` + `.category_ids` (Task 5), `CategoryHistoryRepository` (Task 3), `dominant_category` (Task 3), `ProductResolution`, `AutoConfirmSettings`, `normalize_score`, `SOURCE_*` (Task 2).
- Produces:
  - `CategorizationResult(candidates: dict, resolutions: list[ProductResolution], vendor_has_history: bool)`
  - `ReceiptCategorizationService(product_resolver, categories_service, category_history_repository, settings)` with `categorize(transaction_model: TransactionModel, vendor_id: int | None) -> CategorizationResult`
  - `candidates` shape: `{"category_candidates": [{"product_name", "category_candidates": [{"category_id","category_name","category_score"}], "source": "history"|"ai", "product_id": int|None, "history_count": int}]}`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_receipt_categorization.py
import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, TransactionModel
from src.services.product_resolver import ResolvedProduct, SimilarName
from src.services.receipt_auto_confirm import AutoConfirmSettings
from src.services.receipt_categorization import ReceiptCategorizationService

SETTINGS = AutoConfirmSettings(enabled=True)


def _tx(*names):
    return TransactionModel(
        vendor="Lidl", title="P",
        products=[ProductItem(name=n, quantity=1, price=1.0) for n in names],
        total=float(len(names)), date="2026-09-30",
    )


def _service(resolved, counts_by_call, ai_response=None, category_ids=None):
    resolver = MagicMock()
    resolver.resolve.return_value = resolved
    resolver.find_similar.return_value = []
    categories = MagicMock()
    categories.category_ids = category_ids if category_ids is not None else {1, 2, 3}
    categories.assign_category_candidates.return_value = ai_response or {"category_candidates": []}
    history = MagicMock()
    history.get_category_counts.side_effect = counts_by_call
    history.vendor_has_confirmed_receipts.return_value = True
    svc = ReceiptCategorizationService(resolver, categories, history, SETTINGS)
    return svc, resolver, categories, history


@pytest.mark.unit
def test_history_verdict_skips_llm():
    # Arrange
    resolved = [ResolvedProduct("MLEKO", 10, "Mleko", "exact", [])]
    svc, _, categories, _ = _service(resolved, [{10: {1: ("Nabiał", 5)}}])

    # Act
    result = svc.categorize(_tx("MLEKO"), vendor_id=3)

    # Assert
    categories.assign_category_candidates.assert_not_called()
    entry = result.candidates["category_candidates"][0]
    assert entry["source"] == "history"
    assert entry["history_count"] == 5
    assert entry["category_candidates"][0]["category_id"] == 1
    assert result.resolutions[0].source == "history"
    assert result.resolutions[0].category_id == 1
    assert result.vendor_has_history is True


@pytest.mark.unit
def test_products_without_verdict_go_to_llm_with_examples():
    # Arrange
    resolved = [
        ResolvedProduct("MLEKO", 10, "Mleko", "exact", []),
        ResolvedProduct("SER EDAM", 11, "Ser", "llm_existing", [SimilarName("SER GOUDA", 12, 0.6)]),
    ]
    ai = {"category_candidates": [{"product_name": "SER EDAM", "category_candidates": [
        {"category_id": 1, "category_name": "Nabiał", "category_score": 0.95},
        {"category_id": 2, "category_name": "Inne", "category_score": 0.05},
    ]}]}
    svc, _, categories, _ = _service(
        resolved,
        [{10: {1: ("Nabiał", 5)}}, {12: {1: ("Nabiał", 3)}}],
        ai_response=ai,
    )

    # Act
    result = svc.categorize(_tx("MLEKO", "SER EDAM"), vendor_id=3)

    # Assert
    tx_arg = categories.assign_category_candidates.call_args[0][0]
    assert [p.name for p in tx_arg.products] == ["SER EDAM"]
    assert categories.assign_category_candidates.call_args.kwargs["examples"] == [("SER GOUDA", "Nabiał")]
    ai_resolution = result.resolutions[1]
    assert ai_resolution.source == "ai"
    assert ai_resolution.category_id == 1
    assert ai_resolution.confidence == pytest.approx(0.95)


@pytest.mark.unit
def test_ai_candidates_with_unknown_category_ids_are_dropped():
    # Arrange
    resolved = [ResolvedProduct("X", None, None, "unresolved", [])]
    ai = {"category_candidates": [{"product_name": "X", "category_candidates": [
        {"category_id": 999, "category_name": "Halucynacja", "category_score": 0.99},
    ]}]}
    svc, _, _, _ = _service(resolved, [{}, {}], ai_response=ai, category_ids={1, 2})

    # Act
    result = svc.categorize(_tx("X"), vendor_id=None)

    # Assert
    assert result.candidates["category_candidates"][0]["category_candidates"] == []
    assert result.resolutions[0].category_id is None


@pytest.mark.unit
def test_percent_scores_are_normalized():
    # Arrange
    resolved = [ResolvedProduct("X", None, None, "unresolved", [])]
    ai = {"category_candidates": [{"product_name": "X", "category_candidates": [
        {"category_id": 1, "category_name": "Nabiał", "category_score": 91},
    ]}]}
    svc, _, _, _ = _service(resolved, [{}, {}], ai_response=ai)

    # Act
    result = svc.categorize(_tx("X"), vendor_id=None)

    # Assert
    assert result.resolutions[0].confidence == pytest.approx(0.91)


@pytest.mark.unit
def test_duplicate_product_names_produce_one_entry():
    # Arrange
    resolved = [ResolvedProduct("RABAT", 1, "Rabat", "exact", []), ResolvedProduct("RABAT", 1, "Rabat", "exact", [])]
    svc, _, _, _ = _service(resolved, [{1: {3: ("Rabaty", 4)}}])

    # Act
    result = svc.categorize(_tx("RABAT", "RABAT"), vendor_id=None)

    # Assert
    assert len(result.candidates["category_candidates"]) == 1
    assert len(result.resolutions) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_categorization.py -q --no-cov`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/services/receipt_categorization.py
from __future__ import annotations

from dataclasses import dataclass

from ..data import TransactionModel
from .category_history import dominant_category
from .receipt_auto_confirm import (
    SOURCE_AI,
    SOURCE_HISTORY,
    AutoConfirmSettings,
    ProductResolution,
    normalize_score,
)

MAX_EXAMPLES = 30
EXAMPLES_PER_PRODUCT = 5


@dataclass(frozen=True)
class CategorizationResult:
    candidates: dict
    resolutions: list[ProductResolution]
    vendor_has_history: bool


class ReceiptCategorizationService:
    def __init__(self, product_resolver, categories_service, category_history_repository, settings: AutoConfirmSettings):
        self.product_resolver = product_resolver
        self.categories_service = categories_service
        self.category_history_repository = category_history_repository
        self.settings = settings

    def categorize(self, transaction_model: TransactionModel, vendor_id: int | None) -> CategorizationResult:
        raw_names = [p.name for p in transaction_model.products]
        unique_names = list(dict.fromkeys(raw_names))
        by_name = {r.raw_name: r for r in self.product_resolver.resolve(raw_names)}

        product_ids = sorted({r.product_id for r in by_name.values() if r.product_id is not None})
        counts = self.category_history_repository.get_category_counts(product_ids)
        verdicts = {}
        for name, resolved in by_name.items():
            if resolved.product_id is None:
                continue
            verdict = dominant_category(
                counts.get(resolved.product_id, {}),
                self.settings.history_min_count,
                self.settings.history_min_share,
            )
            if verdict is not None:
                verdicts[name] = verdict

        ai_by_name: dict[str, list[dict]] = {}
        needs_ai = [n for n in unique_names if n not in verdicts]
        if needs_ai:
            subset = transaction_model.model_copy(
                update={"products": [p for p in transaction_model.products if p.name in set(needs_ai)]}
            )
            response = self.categories_service.assign_category_candidates(
                subset, examples=self._examples(needs_ai, by_name)
            )
            valid_ids = self.categories_service.category_ids
            for entry in (response or {}).get("category_candidates", []):
                candidates = [
                    c for c in entry.get("category_candidates", [])
                    if not valid_ids or c.get("category_id") in valid_ids
                ]
                ai_by_name[entry.get("product_name", "")] = candidates

        entries: list[dict] = []
        resolutions: list[ProductResolution] = []
        for name in unique_names:
            resolved = by_name[name]
            verdict = verdicts.get(name)
            if verdict is not None:
                entries.append({
                    "product_name": name,
                    "category_candidates": [{
                        "category_id": verdict.category_id,
                        "category_name": verdict.category_name,
                        "category_score": round(verdict.share, 4),
                    }],
                    "source": SOURCE_HISTORY,
                    "product_id": resolved.product_id,
                    "history_count": verdict.count,
                })
                resolutions.append(ProductResolution(
                    name, resolved.product_id, resolved.normalized_name,
                    verdict.category_id, verdict.category_name, SOURCE_HISTORY, verdict.share, verdict.count,
                ))
                continue
            candidates = ai_by_name.get(name, [])
            top = max(candidates, key=lambda c: c.get("category_score", 0), default=None)
            entries.append({
                "product_name": name,
                "category_candidates": candidates,
                "source": SOURCE_AI,
                "product_id": resolved.product_id,
                "history_count": 0,
            })
            resolutions.append(ProductResolution(
                name,
                resolved.product_id,
                resolved.normalized_name,
                top.get("category_id") if top else None,
                top.get("category_name") if top else None,
                SOURCE_AI,
                normalize_score(float(top.get("category_score", 0))) if top else 0.0,
                0,
            ))

        return CategorizationResult(
            candidates={"category_candidates": entries},
            resolutions=resolutions,
            vendor_has_history=self.category_history_repository.vendor_has_confirmed_receipts(vendor_id),
        )

    def _examples(self, names: list[str], by_name: dict) -> list[tuple[str, str]]:
        similar_ids: dict[str, int] = {}
        for name in names:
            similar = by_name[name].similar or self.product_resolver.find_similar(name)
            for s in similar[:EXAMPLES_PER_PRODUCT]:
                similar_ids.setdefault(s.name, s.product_id)
        if not similar_ids:
            return []
        counts = self.category_history_repository.get_category_counts(sorted(set(similar_ids.values())))
        examples = []
        for alt_name, product_id in similar_ids.items():
            verdict = dominant_category(counts.get(product_id, {}), min_count=1, min_share=0.5)
            if verdict is not None:
                examples.append((alt_name, verdict.category_name))
        return examples[:MAX_EXAMPLES]
```

Note for the test `test_ai_candidates_with_unknown_category_ids_are_dropped`: `find_similar` returns `[]`, so `_examples` returns early and `get_category_counts` is called only once; `side_effect` lists with extra items are fine.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipt_categorization.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/receipt_categorization.py backend/tests/unit/test_receipt_categorization.py
git commit -m "feat(backend): history-first receipt categorization service"
```

---

### Task 8: Receipts/analytics repositories and API models

**Files:**
- Modify: `backend/src/data.py`
- Modify: `backend/src/repositories/receipts_scans.py`
- Modify: `backend/src/repositories/prompt_analytics.py`
- Modify: `backend/tests/unit/test_receipts_scans_repository.py` (existing fake rows)
- Test: `backend/tests/unit/test_receipts_scans_auto_confirm.py`

**Interfaces:**
- Produces in `data.py`:
  - `AutoConfirmReasonItem(code: str, message: str, blocking: bool)` (declare **before** `ReceiptScanListItem`)
  - `ReceiptScanListItem.confirmation_source: str | None = None`
  - `ReceiptScanDetail.confirmation_source: str | None = None`, `ReceiptScanDetail.auto_confirm_reasons: list[AutoConfirmReasonItem] | None = None`
  - `RescoreReasonCount(code: str, message: str, count: int)`, `RescoreReport(dry_run: bool, total: int, eligible: int, confirmed: int, skipped: int, errors: int, top_reasons: list[RescoreReasonCount])`
- Produces on `ReceiptsScansRepository`:
  - `set_status_done(scan_id: int, confirmation_source: str = "manual") -> bool`
  - `set_status_to_confirm_by_id(scan_id)` now also clears `confirmation_source`
  - `set_auto_confirm_reasons(scan_id: int, reasons: list[dict]) -> bool`
  - `set_category_candidates_if_pending(scan_id: int, candidates: dict) -> bool`
  - `get_pending_for_rescore() -> list[ProcessedScan]`
  - `get_all(..., confirmation_source: str | None = None)`; `get_by_id` fills the two new fields
- Produces `PromptAnalyticsRepository.mark_auto_confirm_reverted(scan_id: int) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_receipts_scans_auto_confirm.py
import pytest
from unittest.mock import MagicMock

from src.data import ReceiptsScanStatus
from src.repositories.prompt_analytics import PromptAnalyticsRepository
from src.repositories.receipts_scans import ReceiptsScansRepository


def _repo(cls=ReceiptsScansRepository, fetchone=None, fetchall=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    repo = cls.__new__(cls)
    repo.conn = conn
    repo.table = "receipts_scans"
    return repo, cursor


@pytest.mark.unit
def test_set_status_done_records_source():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_done(5, "auto")

    # Assert
    sql, params = cursor.execute.call_args[0]
    assert "confirmation_source = %s" in sql
    assert params == (ReceiptsScanStatus.DONE, "auto", 5)


@pytest.mark.unit
def test_set_status_done_defaults_to_manual():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_done(5)

    # Assert
    assert cursor.execute.call_args[0][1] == (ReceiptsScanStatus.DONE, "manual", 5)


@pytest.mark.unit
def test_set_status_to_confirm_clears_source():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_to_confirm_by_id(5)

    # Assert
    assert "confirmation_source = NULL" in cursor.execute.call_args[0][0]


@pytest.mark.unit
def test_set_auto_confirm_reasons_writes_json():
    # Arrange
    repo, cursor = _repo()
    reasons = [{"code": "sum_mismatch", "message": "m", "blocking": True}]

    # Act
    ok = repo.set_auto_confirm_reasons(5, reasons)

    # Assert
    assert ok is True
    _, params = cursor.execute.call_args[0]
    assert params[0].adapted == reasons
    assert params[1] == 5


@pytest.mark.unit
def test_set_category_candidates_if_pending_true_when_row_updated():
    # Arrange
    repo, cursor = _repo(fetchone=(5,))

    # Act
    ok = repo.set_category_candidates_if_pending(5, {"category_candidates": []})

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "status = %s" in sql
    assert params[1:] == (5, ReceiptsScanStatus.TO_CONFIRM)


@pytest.mark.unit
def test_set_category_candidates_if_pending_false_when_status_changed():
    # Arrange
    repo, _ = _repo(fetchone=None)

    # Act / Assert
    assert repo.set_category_candidates_if_pending(5, {}) is False


@pytest.mark.unit
def test_get_pending_for_rescore_parses_results():
    # Arrange
    good = {"vendor": "Lidl", "date": "2026-09-30", "title": "P", "total": 1.0, "products": []}
    repo, cursor = _repo(fetchall=[(1, "a.jpg", good), (2, "b.jpg", {"broken": True})])

    # Act
    scans = repo.get_pending_for_rescore()

    # Assert
    assert [s.id for s in scans] == [1]
    assert cursor.execute.call_args[0][1] == (ReceiptsScanStatus.TO_CONFIRM,)


@pytest.mark.unit
def test_get_by_id_reads_confirmation_fields():
    # Arrange
    repo, _ = _repo(fetchone=(
        1, "a.jpg", "done", None, None, None, [], None, None, None,
        "auto", [{"code": "vendor_new", "message": "m", "blocking": False}],
    ))

    # Act
    detail = repo.get_by_id(1)

    # Assert
    assert detail.confirmation_source == "auto"
    assert detail.auto_confirm_reasons[0].code == "vendor_new"


@pytest.mark.unit
def test_get_all_filters_and_returns_confirmation_source():
    # Arrange
    repo, cursor = _repo(fetchall=[
        (1, "a.jpg", "done", "Lidl", "2026-09-30", "1.0", [], 3, False, 1, "auto"),
    ])

    # Act
    items, total = repo.get_all(confirmation_source="auto")

    # Assert
    assert items[0].confirmation_source == "auto"
    assert total == 1
    sql, params = cursor.execute.call_args[0]
    assert "rs.confirmation_source = %s" in sql
    assert "auto" in params


@pytest.mark.unit
def test_mark_auto_confirm_reverted():
    # Arrange
    repo, cursor = _repo(cls=PromptAnalyticsRepository)

    # Act
    ok = repo.mark_auto_confirm_reverted(5)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "auto_confirm_reverted = TRUE" in sql
    assert params == (5,)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipts_scans_auto_confirm.py -q --no-cov`
Expected: FAIL.

- [ ] **Step 3: Implement models in `data.py`**

Insert before `class ReceiptScanListItem`:

```python
class AutoConfirmReasonItem(BaseModel):
    """Why a receipt was (not) auto-confirmed. `message` is user-facing Polish copy."""
    code: str
    message: str
    blocking: bool
```

Add field to `ReceiptScanListItem` (after `has_transaction_link`):

```python
    confirmation_source: str | None = None
```

Add fields to `ReceiptScanDetail` (after `ocr_raw`):

```python
    confirmation_source: str | None = None
    auto_confirm_reasons: list[AutoConfirmReasonItem] | None = None
```

Add after `ConfirmReceiptRequest`:

```python
class RescoreReasonCount(BaseModel):
    code: str
    message: str  # first message seen for this code
    count: int


class RescoreReport(BaseModel):
    """Result of re-scoring pending receipts (Celery task result and Pusher payload)."""
    dry_run: bool
    total: int
    eligible: int
    confirmed: int
    skipped: int
    errors: int
    top_reasons: list[RescoreReasonCount]
```

- [ ] **Step 4: Implement repository changes in `receipts_scans.py`**

Update the import to include `AutoConfirmReasonItem`. Replace `set_status_done` and `set_status_to_confirm_by_id`:

```python
    def set_status_done(self, scan_id: int, confirmation_source: str = "manual") -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s, confirmation_source = %s WHERE id = %s",
                    (ReceiptsScanStatus.DONE, confirmation_source, scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to set status to done:", e)
            self.conn.rollback()
            return False

    def set_status_to_confirm_by_id(self, scan_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET status = %s, confirmation_source = NULL WHERE id = %s",
                    (ReceiptsScanStatus.TO_CONFIRM, scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to reset status to to_confirm:", e)
            self.conn.rollback()
            return False
```

Add new methods (next to `set_status_done`):

```python
    def set_auto_confirm_reasons(self, scan_id: int, reasons: list[dict]) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET auto_confirm_reasons = %s WHERE id = %s",
                    (extras.Json(reasons), scan_id),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to set auto confirm reasons:", e)
            self.conn.rollback()
            return False

    def set_category_candidates_if_pending(self, scan_id: int, candidates: dict) -> bool:
        """Store candidates only while the scan is still awaiting confirmation."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE " + self.table + " SET categories_candidates = %s "
                    "WHERE id = %s AND status = %s RETURNING id",
                    (extras.Json(candidates), scan_id, ReceiptsScanStatus.TO_CONFIRM),
                )
                row = cursor.fetchone()
                self.conn.commit()
                return row is not None
        except Exception as e:
            print("Failed to set category candidates for pending scan:", e)
            self.conn.rollback()
            return False

    def get_pending_for_rescore(self) -> list[ProcessedScan]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, filename, result FROM " + self.table +
                    " WHERE status = %s AND result IS NOT NULL ORDER BY id",
                    (ReceiptsScanStatus.TO_CONFIRM,),
                )
                scans = []
                for row in cursor.fetchall():
                    try:
                        scans.append(ProcessedScan(id=row[0], filename=row[1], transaction_model=TransactionModel(**row[2])))
                    except Exception as e:
                        print(f"Skipping scan id={row[0]} for rescore: {e}")
                return scans
        except Exception as e:
            print("Failed to fetch pending scans:", e)
            return []
```

In `get_all`:
- add parameter `confirmation_source: str | None = None` after `tag`;
- after the `tag` condition add:

```python
                if confirmation_source:
                    conditions.append("rs.confirmation_source = %s")
                    params.append(confirmation_source)
```

- change the SELECT so `COUNT(*) OVER () AS total_count` stays at index 9 and append `, rs.confirmation_source` **after** it (index 10);
- add to the `ReceiptScanListItem(...)` constructor: `confirmation_source=row[10],`.

In `get_by_id`:
- SELECT: append `, confirmation_source, auto_confirm_reasons` after `ocr_raw`;
- before `return ReceiptScanDetail(...)` add:

```python
                reasons_model: list[AutoConfirmReasonItem] | None = None
                if isinstance(row[11], list):
                    try:
                        reasons_model = [AutoConfirmReasonItem(**r) for r in row[11]]
                    except Exception:
                        pass
```

- add kwargs `confirmation_source=row[10], auto_confirm_reasons=reasons_model,`.

- [ ] **Step 5: `PromptAnalyticsRepository.mark_auto_confirm_reverted`**

```python
    def mark_auto_confirm_reverted(self, scan_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE prompt_analytics SET auto_confirm_reverted = TRUE WHERE scan_id = %s",
                    (scan_id,),
                )
                self.conn.commit()
                return True
        except Exception as e:
            print("Failed to mark auto confirm reverted:", e)
            self.conn.rollback()
            return False
```

- [ ] **Step 6: Update existing fake rows in `test_receipts_scans_repository.py`**

- `test_get_all_happy_path`, `test_get_all_default_sorts_by_date_desc`, `test_get_all_date_asc_nulls_last`, `test_get_all_id_sort_nulls_last`: append `, None` to every row tuple (11 elements).
- `test_get_by_id_happy_path`: append `None,  # confirmation_source` and `None,  # auto_confirm_reasons` after `None,  # ocr_raw`.
- `test_get_by_id_with_text_regions`: append `None, None` to the tuple.

- [ ] **Step 7: Run repository tests**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_receipts_scans_auto_confirm.py tests/unit/test_receipts_scans_repository.py tests/unit/test_prompt_analytics_repository.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/data.py backend/src/repositories/receipts_scans.py backend/src/repositories/prompt_analytics.py backend/tests/unit/test_receipts_scans_auto_confirm.py backend/tests/unit/test_receipts_scans_repository.py
git commit -m "feat(backend): persist confirmation source and auto-confirm reasons"
```

---

### Task 9: App — wiring, confirm/reopen, `_apply_auto_confirm`

**Files:**
- Modify: `backend/src/app.py`
- Modify: `backend/tests/unit/conftest.py` (`ALL_PARAMS`)
- Modify: `backend/tests/unit/test_receipts.py` (upsert assertions)
- Test: `backend/tests/unit/test_app_auto_confirm.py`

**Interfaces:**
- Consumes: Tasks 2, 3, 6, 7, 8.
- Produces on `App`:
  - constructor kwargs `category_history_repository=None, product_resolver=None, receipt_categorization_service=None, auto_confirm_settings=None`; attributes with the same names
  - `confirm_receipt(scan_id: int, request: ConfirmReceiptRequest, confirmation_source: str = "manual") -> ReceiptScanDetail | None`
  - `_apply_auto_confirm(scan_id: int, decision: AutoConfirmDecision, resolutions: list[ProductResolution], force: bool = False) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_app_auto_confirm.py
import pytest
from unittest.mock import MagicMock

from src.data import ConfirmReceiptRequest, ProductItem, ReceiptScanDetail, TransactionModel
from src.services.receipt_auto_confirm import (
    AutoConfirmDecision,
    AutoConfirmReason,
    AutoConfirmSettings,
    ProductResolution,
)
from tests.unit.conftest import make_app

ENABLED = AutoConfirmSettings(enabled=True)
DISABLED = AutoConfirmSettings(enabled=False)
RESOLUTIONS = [ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)]


def _scan(status="to_confirm", source=None):
    tx = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="MLEKO", quantity=1, price=3.99)], total=3.99, date="2026-09-30")
    return ReceiptScanDetail(id=1, filename="a.jpg", status=status, result=tx, confirmation_source=source)


def _app(settings=ENABLED):
    app = make_app(auto_confirm_settings=settings)
    app.receipts_scans_repository.get_by_id.return_value = _scan()
    app.transactions_repository.create_transaction.return_value = 42
    app.transactions_repository.get_by_scan_id.return_value = None
    return app


@pytest.mark.unit
def test_confirm_receipt_auto_skips_ground_truth_and_records_source():
    # Arrange
    app = _app()

    # Act
    app.confirm_receipt(1, ConfirmReceiptRequest(product_categories={"MLEKO": 1}), confirmation_source="auto")

    # Assert
    app.receipts_scans_repository.set_status_done.assert_called_once_with(1, "auto")
    app.ground_truth_service.create_from_confirmed_receipt.assert_not_called()


@pytest.mark.unit
def test_confirm_receipt_manual_keeps_ground_truth():
    # Arrange
    app = _app()

    # Act
    app.confirm_receipt(1, ConfirmReceiptRequest(product_categories={"MLEKO": 1}))

    # Assert
    app.receipts_scans_repository.set_status_done.assert_called_once_with(1, "manual")
    app.ground_truth_service.create_from_confirmed_receipt.assert_called_once()


@pytest.mark.unit
def test_confirm_receipt_manual_product_normalization_overwrites_mapping():
    # Arrange
    app = _app()
    app.products_repository.get_product_by_name.return_value = 9

    # Act
    app.confirm_receipt(1, ConfirmReceiptRequest(product_categories={"MLEKO": 1}, normalized_products={"MLEKO": "Mleko"}))

    # Assert
    app.products_repository.upsert_alternative_name.assert_called_once_with("MLEKO", 9)


@pytest.mark.unit
def test_reopen_auto_confirmed_marks_reverted():
    # Arrange
    app = _app()
    app.receipts_scans_repository.get_by_id.return_value = _scan(status="done", source="auto")

    # Act
    app.reopen_receipt(1)

    # Assert
    app.prompt_analytics_repository.mark_auto_confirm_reverted.assert_called_once_with(1)


@pytest.mark.unit
def test_reopen_manual_does_not_mark_reverted():
    # Arrange
    app = _app()
    app.receipts_scans_repository.get_by_id.return_value = _scan(status="done", source="manual")

    # Act
    app.reopen_receipt(1)

    # Assert
    app.prompt_analytics_repository.mark_auto_confirm_reverted.assert_not_called()


@pytest.mark.unit
def test_apply_auto_confirm_confirms_when_enabled_and_ok():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock(return_value=_scan(status="done"))

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is True
    request = app.confirm_receipt.call_args[0][1]
    assert request.product_categories == {"MLEKO": 1}
    assert request.normalized_products == {"MLEKO": "Mleko"}
    assert app.confirm_receipt.call_args.kwargs["confirmation_source"] == "auto"
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once_with(1, [])


@pytest.mark.unit
def test_apply_auto_confirm_disabled_only_stores_reasons():
    # Arrange
    app = _app(DISABLED)
    app.confirm_receipt = MagicMock()

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.confirm_receipt.assert_not_called()
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once()


@pytest.mark.unit
def test_apply_auto_confirm_force_ignores_disabled_flag():
    # Arrange
    app = _app(DISABLED)
    app.confirm_receipt = MagicMock(return_value=_scan(status="done"))

    # Act / Assert
    assert app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS, force=True) is True


@pytest.mark.unit
def test_apply_auto_confirm_blocked_decision_does_not_confirm():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock()
    reason = AutoConfirmReason("sum_mismatch", "m", True)

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(False, [reason]), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.confirm_receipt.assert_not_called()
    app.receipts_scans_repository.set_auto_confirm_reasons.assert_called_once_with(1, [reason.to_dict()])


@pytest.mark.unit
def test_apply_auto_confirm_failure_cleans_up():
    # Arrange
    app = _app()
    app.confirm_receipt = MagicMock(side_effect=Exception("db"))

    # Act
    confirmed = app._apply_auto_confirm(1, AutoConfirmDecision(True, []), RESOLUTIONS)

    # Assert
    assert confirmed is False
    app.transactions_repository.delete_by_scan_id.assert_called_once_with(1)
    app.receipts_scans_repository.set_status_to_confirm_by_id.assert_called_once_with(1)
    last_reasons = app.receipts_scans_repository.set_auto_confirm_reasons.call_args[0][1]
    assert last_reasons[-1]["code"] == "confirm_failed"


@pytest.mark.unit
def test_default_settings_are_disabled_in_unit_env(monkeypatch):
    # Arrange
    monkeypatch.delenv("RECEIPT_AUTO_CONFIRM_ENABLED", raising=False)

    # Act
    app = make_app()

    # Assert
    assert app.auto_confirm_settings.enabled is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_app_auto_confirm.py -q --no-cov`
Expected: FAIL (`TypeError: unexpected keyword 'auto_confirm_settings'`).

- [ ] **Step 3: Wire dependencies in `App.__init__`**

Imports at top of `app.py`:

```python
from .repositories.category_history import CategoryHistoryRepository
from .services.product_resolver import ProductResolver
from .services.receipt_categorization import ReceiptCategorizationService
from .services.receipt_auto_confirm import (
    AutoConfirmDecision,
    AutoConfirmSettings,
    ProductResolution,
    confirm_failed_reason,
    evaluate,
    evaluation_error_reason,
)
```

Constructor signature — add after `bank_accounts_repository=None,`:

```python
        category_history_repository=None,
```

and after `ground_truth_service=None,`:

```python
        product_resolver=None,
        receipt_categorization_service=None,
        auto_confirm_settings=None,
```

Body — after the `bank_csv_parser` line:

```python
        self.category_history_repository = (
            category_history_repository or CategoryHistoryRepository(self.eye_budget_db_context)
        )
        self.auto_confirm_settings = auto_confirm_settings or AutoConfirmSettings.from_env()
        self.product_resolver = product_resolver or ProductResolver(
            self.products_repository, self.products_service
        )
        self.receipt_categorization_service = receipt_categorization_service or ReceiptCategorizationService(
            product_resolver=self.product_resolver,
            categories_service=self.categories_service,
            category_history_repository=self.category_history_repository,
            settings=self.auto_confirm_settings,
        )
```

In `backend/tests/unit/conftest.py` add to `ALL_PARAMS`: `"category_history_repository"` (repositories block) and `"product_resolver"`, `"receipt_categorization_service"` (services block). Do **not** add `auto_confirm_settings` — a `MagicMock` would make `enabled` truthy.

- [ ] **Step 4: Modify `confirm_receipt`**

- signature: `def confirm_receipt(self, scan_id: int, request: ConfirmReceiptRequest, confirmation_source: str = "manual") -> ReceiptScanDetail | None:`
- normalized vendor branch: replace `self.vendors_repository.insert_alternative_name(tx_model.vendor, vendor_id)` with `self.vendors_repository.upsert_alternative_name(tx_model.vendor, vendor_id)`
- normalized product branch: replace `self.products_repository.insert_alternative_name(product.name, product_id)` with `self.products_repository.upsert_alternative_name(product.name, product_id)`
- replace `self.receipts_scans_repository.set_status_done(scan_id)` with `self.receipts_scans_repository.set_status_done(scan_id, confirmation_source)`
- wrap the ground-truth call:

```python
        if confirmation_source == "manual":
            self.ground_truth_service.create_from_confirmed_receipt(
                filename=detail.filename,
                minio_object_key=detail.minio_object_key,
                transaction=tx_model,
            )
```

Update `tests/unit/test_receipts.py`: in `test_confirm_receipt_normalized_vendor_path` assert `app.vendors_repository.upsert_alternative_name.assert_called_once_with("BIEDRONKA 1234", 99)`; in `test_confirm_receipt_normalized_vendor_already_exists` use `upsert_alternative_name.assert_called_once()`; in `test_confirm_receipt_normalized_product_path` use `app.products_repository.upsert_alternative_name.assert_called_once()`.

- [ ] **Step 5: Modify `reopen_receipt`**

After the `if detail is None: return None` guard:

```python
        if detail.confirmation_source == "auto":
            self.prompt_analytics_repository.mark_auto_confirm_reverted(scan_id)
```

- [ ] **Step 6: Add `_apply_auto_confirm`** (below `confirm_receipt`)

```python
    def _apply_auto_confirm(
        self,
        scan_id: int,
        decision: AutoConfirmDecision,
        resolutions: list[ProductResolution],
        force: bool = False,
    ) -> bool:
        """Persist the decision's reasons and confirm when allowed. Returns True if confirmed."""
        reasons = [r.to_dict() for r in decision.reasons]
        self.receipts_scans_repository.set_auto_confirm_reasons(scan_id, reasons)
        if not decision.ok or not (force or self.auto_confirm_settings.enabled):
            return False
        normalized = {r.raw_name: r.normalized_name for r in resolutions if r.normalized_name}
        request = ConfirmReceiptRequest(
            product_categories={r.raw_name: r.category_id for r in resolutions if r.category_id is not None},
            normalized_products=normalized or None,
        )
        try:
            confirmed = self.confirm_receipt(scan_id, request, confirmation_source="auto")
        except Exception as e:
            print(f"Auto-confirm failed for scan {scan_id}: {e}")
            confirmed = None
        if confirmed is None:
            self.transactions_repository.delete_by_scan_id(scan_id)
            self.receipts_scans_repository.set_status_to_confirm_by_id(scan_id)
            reasons.append(confirm_failed_reason().to_dict())
            self.receipts_scans_repository.set_auto_confirm_reasons(scan_id, reasons)
            return False
        return True
```

- [ ] **Step 7: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_app_auto_confirm.py tests/unit/test_receipts.py tests/unit/test_di.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/app.py backend/tests/unit/conftest.py backend/tests/unit/test_receipts.py backend/tests/unit/test_app_auto_confirm.py
git commit -m "feat(backend): auto confirmation path in App with cleanup and manual alias overrides"
```

---

### Task 10: App — pipeline integration

**Files:**
- Modify: `backend/src/app.py` (`_process_single_file`, `_run_production_async`, new helpers)
- Modify: `backend/src/tasks/process_receipts.py`
- Modify: `backend/tests/integration/test_pipeline.py` (`_mock_pipeline_services`)
- Test: `backend/tests/unit/test_app_pipeline_auto_confirm.py`
- Test: `backend/tests/unit/tasks/test_process_receipts.py` (extend)

**Interfaces:**
- Consumes: `ReceiptCategorizationService.categorize`, `evaluate`, `_apply_auto_confirm`.
- Produces on `App`:
  - `_categorize_receipt(scan_id: int, filename: str, transaction_model: TransactionModel, vendor_id: int | None) -> CategorizationResult | None`
  - `_evaluate_and_auto_confirm(scan_id: int, transaction_model: TransactionModel, categorization: CategorizationResult | None) -> bool`
  - `on_progress(..., auto_confirmed: bool = False)` keyword in `_run_production_async`
- Pusher `receipt.progress` payload gains `auto_confirmed: bool`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_app_pipeline_auto_confirm.py
import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, TransactionModel
from src.services.receipt_auto_confirm import AutoConfirmSettings, ProductResolution
from src.services.receipt_categorization import CategorizationResult
from tests.unit.conftest import make_app

TX = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="MLEKO", quantity=1, price=3.99)], total=3.99, date="2026-09-30")
RESULT = CategorizationResult(
    candidates={"category_candidates": []},
    resolutions=[ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)],
    vendor_has_history=True,
)


@pytest.mark.unit
def test_categorize_receipt_stores_candidates():
    # Arrange
    app = make_app()
    app.receipt_categorization_service.categorize.return_value = RESULT

    # Act
    result = app._categorize_receipt(1, "a.jpg", TX, vendor_id=3)

    # Assert
    assert result is RESULT
    app.receipt_categorization_service.categorize.assert_called_once_with(TX, 3)
    app.receipts_scans_repository.set_category_candidates.assert_called_once_with("a.jpg", RESULT.candidates)


@pytest.mark.unit
def test_categorize_receipt_falls_back_to_plain_llm_on_error():
    # Arrange
    app = make_app()
    app.receipt_categorization_service.categorize.side_effect = Exception("boom")
    app.categories_service.assign_category_candidates.return_value = {"category_candidates": []}

    # Act
    result = app._categorize_receipt(1, "a.jpg", TX, vendor_id=None)

    # Assert
    assert result is None
    app.categories_service.assign_category_candidates.assert_called_once_with(TX)
    app.receipts_scans_repository.set_category_candidates.assert_called_once_with("a.jpg", {"category_candidates": []})
    reasons = app.receipts_scans_repository.set_auto_confirm_reasons.call_args[0][1]
    assert reasons[0]["code"] == "evaluation_error"


@pytest.mark.unit
def test_evaluate_and_auto_confirm_uses_gate():
    # Arrange
    app = make_app(auto_confirm_settings=AutoConfirmSettings(enabled=True))
    app._apply_auto_confirm = MagicMock(return_value=True)

    # Act
    confirmed = app._evaluate_and_auto_confirm(1, TX, RESULT)

    # Assert
    assert confirmed is True
    decision = app._apply_auto_confirm.call_args[0][1]
    assert decision.ok is True


@pytest.mark.unit
def test_evaluate_and_auto_confirm_none_categorization_returns_false():
    # Arrange
    app = make_app()
    app._apply_auto_confirm = MagicMock()

    # Act / Assert
    assert app._evaluate_and_auto_confirm(1, TX, None) is False
    app._apply_auto_confirm.assert_not_called()


@pytest.mark.unit
def test_process_single_file_runs_history_pipeline(tmp_path):
    # Arrange
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    app = make_app()
    app.preprocessing_service.preprocess_image.return_value = str(img)
    app.receipts_scans_repository.get_scan_id_by_filename.return_value = 1
    app.ocr_service.process_image.return_value = TX.model_dump()
    app.vendors_service.process_vendor.return_value = MagicMock(vendor_name="Lidl")
    app.vendors_repository.process_vendor_mapping.return_value = 3
    app._categorize_receipt = MagicMock(return_value=RESULT)
    app._evaluate_and_auto_confirm = MagicMock(return_value=False)

    # Act
    ok = app._process_single_file("a.jpg")

    # Assert
    assert ok is True
    assert app._categorize_receipt.call_args[0][3] == 3
    app._evaluate_and_auto_confirm.assert_called_once()
    app.products_service.process_products.assert_not_called()
```

Extend `backend/tests/unit/tasks/test_process_receipts.py` with:

```python
    def test_progress_payload_includes_auto_confirmed(self):
        # Arrange
        app = make_app()

        async def fake_run(on_progress=None):
            on_progress(index=1, total=1, filename="/in/a.jpg", status="done", error=None, auto_confirmed=True)

        app._run_production_async = fake_run
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.process_receipts.App", return_value=app),
            patch("src.tasks.process_receipts.PusherService", return_value=mock_pusher),
        ):
            # Act
            process_receipts_task.apply(task_id=TASK_ID, throw=True)

        # Assert
        progress = triggers_with_event(mock_pusher, "receipts", "receipt.progress")
        assert progress[0][0][2]["auto_confirmed"] is True
```

(Place it inside the existing test class; reuse its imports — add `triggers_with_event`/`TASK_ID`/`make_app` imports from `tests.unit.tasks.conftest` if missing.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_app_pipeline_auto_confirm.py tests/unit/tasks/test_process_receipts.py -q --no-cov`
Expected: FAIL.

- [ ] **Step 3: Add helpers to `App`** (next to `_handle_ocr_dict`)

```python
    def _categorize_receipt(
        self, scan_id: int, filename: str, transaction_model: TransactionModel, vendor_id: int | None
    ) -> "CategorizationResult | None":
        """History-first categorization; on failure falls back to the plain LLM path."""
        try:
            result = self.receipt_categorization_service.categorize(transaction_model, vendor_id)
        except Exception as e:
            print(f"History-based categorization failed for {filename}, falling back: {e}")
            candidates = self.categories_service.assign_category_candidates(transaction_model)
            self.receipts_scans_repository.set_category_candidates(filename, candidates)
            self.receipts_scans_repository.set_auto_confirm_reasons(scan_id, [evaluation_error_reason().to_dict()])
            return None
        self.receipts_scans_repository.set_category_candidates(filename, result.candidates)
        return result

    def _evaluate_and_auto_confirm(
        self, scan_id: int, transaction_model: TransactionModel, categorization: "CategorizationResult | None"
    ) -> bool:
        if categorization is None:
            return False
        decision = evaluate(
            transaction_model,
            categorization.resolutions,
            categorization.vendor_has_history,
            self.auto_confirm_settings,
        )
        return self._apply_auto_confirm(scan_id, decision, categorization.resolutions)
```

Add `CategorizationResult` to the import from `.services.receipt_categorization` and drop the string quotes if preferred.

- [ ] **Step 4: Update `_process_single_file`**

Replace the block from `vendor_mapping = self.vendors_service.process_vendor(...)` through the localization `try/except` with:

```python
            vendor_mapping = self.vendors_service.process_vendor(transaction_model.vendor)
            vendor_id = self.vendors_repository.process_vendor_mapping(vendor_mapping)
            transaction_model = transaction_model.model_copy(
                update={"vendor": vendor_mapping.vendor_name}
            )

            categorization = self._categorize_receipt(scan_id, filename, transaction_model, vendor_id)

            try:
                products = [p.model_dump() for p in transaction_model.products]
                self._run_localization(scan_id, preprocessed_image_path, products)
            except Exception as loc_err:
                print(f"Text localization failed for {filename} (non-fatal): {loc_err}")

            self._evaluate_and_auto_confirm(scan_id, transaction_model, categorization)
            return True
```

- [ ] **Step 5: Update `_run_production_async`**

Inside `_process_file`, declare `auto_confirmed = False` next to `file_error`. Replace the block from `vendor_mapping = await asyncio.to_thread(...)` through the localization `try/except` with:

```python
                        vendor_mapping = await asyncio.to_thread(
                            self.vendors_service.process_vendor, transaction_model.vendor
                        )
                        async with db_lock:
                            vendor_id = await asyncio.to_thread(
                                self.vendors_repository.process_vendor_mapping, vendor_mapping
                            )
                        transaction_model = transaction_model.model_copy(
                            update={"vendor": vendor_mapping.vendor_name}
                        )

                        # Categorization interleaves DB reads/writes with LLM calls on the
                        # shared connection, so it runs under the DB lock.
                        async with db_lock:
                            categorization = await asyncio.to_thread(
                                self._categorize_receipt, scan_id, file, transaction_model, vendor_id
                            )

                        try:
                            products = [p.model_dump() for p in transaction_model.products]
                            await asyncio.to_thread(
                                self._run_localization, scan_id, preprocessed_image_path, products
                            )
                        except Exception as loc_err:
                            print(f"Text localization failed for {file} (non-fatal): {loc_err}")

                        async with db_lock:
                            auto_confirmed = await asyncio.to_thread(
                                self._evaluate_and_auto_confirm, scan_id, transaction_model, categorization
                            )
```

And pass it to the callback:

```python
                on_progress(
                    index=idx,
                    total=total,
                    filename=file,
                    status=status,
                    error=file_error,
                    auto_confirmed=auto_confirmed,
                )
```

- [ ] **Step 6: Update `process_receipts_task.on_progress`**

```python
    def on_progress(
        index: int,
        total: int,
        filename: str,
        status: str,
        error: str | None = None,
        auto_confirmed: bool = False,
    ):
        payload = {
            "task_id": task_id,
            "index": index,
            "total": total,
            "filename": os.path.basename(filename),
            "status": status,
            "auto_confirmed": auto_confirmed,
        }
        if error:
            payload["error"] = error
        pusher.trigger("receipts", "receipt.progress", payload)
```

- [ ] **Step 7: Update the integration helper `_mock_pipeline_services`** in `backend/tests/integration/test_pipeline.py` — append before `return tmp.name`:

```python
    from src.services.receipt_categorization import CategorizationResult
    app.receipt_categorization_service = MagicMock()
    app.receipt_categorization_service.categorize.return_value = CategorizationResult(
        candidates={"category_candidates": []}, resolutions=[], vendor_has_history=False
    )
```

- [ ] **Step 8: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit -m unit -q --no-cov`
Expected: all PASS.
Run: `cd backend && ../venv/bin/python -m pytest tests/integration/test_pipeline.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/src/app.py backend/src/tasks/process_receipts.py backend/tests/unit/test_app_pipeline_auto_confirm.py backend/tests/unit/tasks/test_process_receipts.py backend/tests/integration/test_pipeline.py
git commit -m "feat(backend): run history categorization and auto-confirm in receipt pipeline"
```

---

### Task 11: Backlog re-score — App, Celery task, routes

**Files:**
- Modify: `backend/src/app.py` (`rescore_pending_receipts`, `get_all_receipts` filter)
- Create: `backend/src/tasks/rescore_pending_receipts.py`
- Modify: `backend/src/celery_app.py`
- Modify: `backend/src/main.py`
- Test: `backend/tests/unit/test_app_rescore.py`
- Test: `backend/tests/unit/tasks/test_rescore_pending_receipts.py`
- Test: `backend/tests/integration/test_rescore_routes.py`

**Interfaces:**
- Consumes: Tasks 7–10.
- Produces:
  - `App.rescore_pending_receipts(dry_run: bool, on_progress=None) -> RescoreReport` (`on_progress(index: int, total: int)`)
  - `App.get_all_receipts(..., confirmation_source: str | None = None)`
  - Celery `tasks.rescore_pending_receipts` → returns `RescoreReport.model_dump()`; Pusher events on channel `receipts`: `receipt.rescore_progress {task_id,index,total}`, `receipt.rescore_done {task_id, report}`, `receipt.rescore_error {task_id, error}`
  - `POST /receipts/rescore?dry_run=true|false` → 202 `TaskResponse`
  - `GET /receipts?confirmation_source=auto|manual`

- [ ] **Step 1: Write the failing App tests**

```python
# backend/tests/unit/test_app_rescore.py
import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, ReceiptScanDetail, TransactionModel
from src.repositories.receipts_scans import ProcessedScan
from src.services.receipt_auto_confirm import AutoConfirmSettings, ProductResolution
from src.services.receipt_categorization import CategorizationResult
from tests.unit.conftest import make_app


def _tx(total=3.99):
    return TransactionModel(vendor="LIDL SP. Z O.O.", title="P", products=[ProductItem(name="MLEKO", quantity=1, price=3.99)], total=total, date="2026-09-30")


def _result():
    return CategorizationResult(
        candidates={"category_candidates": []},
        resolutions=[ProductResolution("MLEKO", 10, "Mleko", 1, "Nabiał", "history", 1.0, 5)],
        vendor_has_history=True,
    )


def _app(scans):
    app = make_app(auto_confirm_settings=AutoConfirmSettings(enabled=False))
    app.receipts_scans_repository.get_pending_for_rescore.return_value = scans
    app.receipts_scans_repository.set_category_candidates_if_pending.return_value = True
    app.receipts_scans_repository.get_by_id.return_value = ReceiptScanDetail(id=1, filename="a.jpg", status="to_confirm")
    app.vendors_repository.get_vendor_by_alternative_name.return_value = 3
    app.vendors_repository.get_normalized_name_by_alternative_name.return_value = "Lidl"
    app.receipt_categorization_service.categorize.return_value = _result()
    app._apply_auto_confirm = MagicMock(return_value=True)
    return app


@pytest.mark.unit
def test_dry_run_counts_eligible_without_confirming():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx()), ProcessedScan(2, "b.jpg", _tx(total=9.99))])

    # Act
    report = app.rescore_pending_receipts(dry_run=True)

    # Assert
    assert report.total == 2
    assert report.eligible == 1
    assert report.confirmed == 0
    app._apply_auto_confirm.assert_not_called()
    assert app.receipts_scans_repository.set_auto_confirm_reasons.call_count == 2
    assert report.top_reasons[0].code == "sum_mismatch"
    assert report.top_reasons[0].count == 1


@pytest.mark.unit
def test_uses_normalized_vendor_for_categorization():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])

    # Act
    app.rescore_pending_receipts(dry_run=True)

    # Assert
    tx_arg, vendor_id = app.receipt_categorization_service.categorize.call_args[0]
    assert tx_arg.vendor == "Lidl"
    assert vendor_id == 3


@pytest.mark.unit
def test_real_run_force_confirms_eligible():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.confirmed == 1
    assert app._apply_auto_confirm.call_args.kwargs["force"] is True


@pytest.mark.unit
def test_scan_confirmed_meanwhile_is_skipped():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipts_scans_repository.set_category_candidates_if_pending.return_value = False

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.skipped == 1
    app._apply_auto_confirm.assert_not_called()


@pytest.mark.unit
def test_status_change_before_confirm_is_skipped():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipts_scans_repository.get_by_id.return_value = ReceiptScanDetail(id=1, filename="a.jpg", status="done")

    # Act
    report = app.rescore_pending_receipts(dry_run=False)

    # Assert
    assert report.skipped == 1
    assert report.confirmed == 0


@pytest.mark.unit
def test_errors_are_counted_and_progress_reported():
    # Arrange
    app = _app([ProcessedScan(1, "a.jpg", _tx())])
    app.receipt_categorization_service.categorize.side_effect = Exception("llm")
    progress = MagicMock()

    # Act
    report = app.rescore_pending_receipts(dry_run=True, on_progress=progress)

    # Assert
    assert report.errors == 1
    progress.assert_called_once_with(index=1, total=1)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_app_rescore.py -q --no-cov`
Expected: FAIL (`AttributeError: 'App' object has no attribute 'rescore_pending_receipts'`).

- [ ] **Step 3: Implement `App.rescore_pending_receipts`** (below `_evaluate_and_auto_confirm`; add `RescoreReport, RescoreReasonCount` to the `.data` import)

```python
    def rescore_pending_receipts(self, dry_run: bool, on_progress=None) -> RescoreReport:
        """Re-run categorization + gate for all to_confirm scans (no OCR)."""
        scans = self.receipts_scans_repository.get_pending_for_rescore()
        reason_counts: dict[str, list] = {}
        eligible = confirmed = skipped = errors = 0

        for index, scan in enumerate(scans, start=1):
            try:
                raw = scan.transaction_model
                vendor_id = self.vendors_repository.get_vendor_by_alternative_name(raw.vendor)
                normalized_vendor = (
                    self.vendors_repository.get_normalized_name_by_alternative_name(raw.vendor) or raw.vendor
                )
                transaction_model = raw.model_copy(update={"vendor": normalized_vendor})
                result = self.receipt_categorization_service.categorize(transaction_model, vendor_id)
                if not self.receipts_scans_repository.set_category_candidates_if_pending(scan.id, result.candidates):
                    skipped += 1
                    continue
                decision = evaluate(
                    transaction_model, result.resolutions, result.vendor_has_history, self.auto_confirm_settings
                )
                for reason in decision.reasons:
                    entry = reason_counts.setdefault(reason.code, [reason.message, 0])
                    entry[1] += 1
                if decision.ok:
                    eligible += 1
                if dry_run or not decision.ok:
                    self.receipts_scans_repository.set_auto_confirm_reasons(
                        scan.id, [r.to_dict() for r in decision.reasons]
                    )
                    continue
                current = self.receipts_scans_repository.get_by_id(scan.id)
                if current is None or current.status != ReceiptsScanStatus.TO_CONFIRM:
                    skipped += 1
                    continue
                if self._apply_auto_confirm(scan.id, decision, result.resolutions, force=True):
                    confirmed += 1
            except Exception as e:
                print(f"Rescore failed for scan {scan.id}: {e}")
                errors += 1
            finally:
                if on_progress:
                    on_progress(index=index, total=len(scans))

        top_reasons = [
            RescoreReasonCount(code=code, message=message, count=count)
            for code, (message, count) in sorted(reason_counts.items(), key=lambda kv: -kv[1][1])[:5]
        ]
        return RescoreReport(
            dry_run=dry_run,
            total=len(scans),
            eligible=eligible,
            confirmed=confirmed,
            skipped=skipped,
            errors=errors,
            top_reasons=top_reasons,
        )
```

Note: `continue` inside `try` still runs `finally`, so progress is reported for skipped scans too.

Also add `confirmation_source: str | None = None` to `App.get_all_receipts` and pass it through to `self.receipts_scans_repository.get_all(..., confirmation_source=confirmation_source)`.

- [ ] **Step 4: Run App tests**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit/test_app_rescore.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 5: Write the failing task test**

```python
# backend/tests/unit/tasks/test_rescore_pending_receipts.py
import pytest
from unittest.mock import MagicMock, patch

from src.data import RescoreReport
from src.tasks.rescore_pending_receipts import rescore_pending_receipts_task
from tests.unit.tasks.conftest import TASK_ID, assert_app_disposed, make_app, triggers_with_event

REPORT = RescoreReport(dry_run=True, total=2, eligible=1, confirmed=0, skipped=0, errors=0, top_reasons=[])


@pytest.mark.unit
class TestRescorePendingReceiptsTask:
    def test_success_emits_done_with_report_and_returns_it(self):
        # Arrange
        app = make_app()

        def fake_rescore(dry_run, on_progress=None):
            on_progress(index=1, total=2)
            return REPORT

        app.rescore_pending_receipts = MagicMock(side_effect=fake_rescore)
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.rescore_pending_receipts.App", return_value=app),
            patch("src.tasks.rescore_pending_receipts.PusherService", return_value=mock_pusher),
        ):
            # Act
            result = rescore_pending_receipts_task.apply(kwargs={"dry_run": True}, task_id=TASK_ID, throw=True)

        # Assert
        assert result.get() == REPORT.model_dump()
        assert app.rescore_pending_receipts.call_args.kwargs["dry_run"] is True
        progress = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_progress")
        assert progress[0][0][2] == {"task_id": TASK_ID, "index": 1, "total": 2}
        done = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_done")
        assert done[0][0][2]["report"] == REPORT.model_dump()
        assert_app_disposed(app)

    def test_exception_emits_error_and_reraises(self):
        # Arrange
        app = make_app()
        app.rescore_pending_receipts = MagicMock(side_effect=RuntimeError("db down"))
        mock_pusher = MagicMock()

        with (
            patch("src.tasks.rescore_pending_receipts.App", return_value=app),
            patch("src.tasks.rescore_pending_receipts.PusherService", return_value=mock_pusher),
        ):
            with pytest.raises(RuntimeError):
                rescore_pending_receipts_task.apply(kwargs={"dry_run": False}, task_id=TASK_ID, throw=True)

        err = triggers_with_event(mock_pusher, "receipts", "receipt.rescore_error")
        assert "db down" in err[0][0][2]["error"]
        assert_app_disposed(app)
```

- [ ] **Step 6: Implement the task and register it**

```python
# backend/src/tasks/rescore_pending_receipts.py
from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.rescore_pending_receipts")
def rescore_pending_receipts_task(self, dry_run: bool = True):
    """Celery task: re-score to_confirm receipts with history-based categorization."""
    task_id = self.request.id
    pusher = PusherService()
    my_app = App()

    def on_progress(index: int, total: int):
        pusher.trigger(
            "receipts",
            "receipt.rescore_progress",
            {"task_id": task_id, "index": index, "total": total},
        )

    try:
        report = my_app.rescore_pending_receipts(dry_run=dry_run, on_progress=on_progress).model_dump()
        pusher.trigger("receipts", "receipt.rescore_done", {"task_id": task_id, "report": report})
        return report
    except Exception as exc:
        pusher.trigger("receipts", "receipt.rescore_error", {"task_id": task_id, "error": str(exc)})
        raise
    finally:
        my_app.dispose()
```

In `backend/src/celery_app.py` add `"src.tasks.rescore_pending_receipts",` to `include`.

- [ ] **Step 7: Routes in `main.py`**

Import: `from src.tasks.rescore_pending_receipts import rescore_pending_receipts_task`.

Add after `evaluate_receipts`:

```python
@app.post("/receipts/rescore", response_model=TaskResponse, status_code=202)
def rescore_receipts(dry_run: bool = True):
    """Re-score pending receipts with history-based categorization. dry_run=true confirms nothing."""
    task = rescore_pending_receipts_task.delay(dry_run=dry_run)
    return TaskResponse(task_id=task.id)
```

In `list_receipts` add parameter `confirmation_source: Literal["auto", "manual"] | None = None,` (after `tag`) and pass `confirmation_source=confirmation_source` to `my_app.get_all_receipts(...)`.

- [ ] **Step 8: Route test**

```python
# backend/tests/integration/test_rescore_routes.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_rescore_defaults_to_dry_run(client):
    # Arrange
    task = MagicMock(id="t-1")
    with patch("src.main.rescore_pending_receipts_task") as mock_task:
        mock_task.delay.return_value = task

        # Act
        response = client.post("/receipts/rescore")

    # Assert
    assert response.status_code == 202
    assert response.json() == {"task_id": "t-1"}
    mock_task.delay.assert_called_once_with(dry_run=True)


@pytest.mark.integration
def test_rescore_real_run(client):
    # Arrange
    with patch("src.main.rescore_pending_receipts_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="t-2")

        # Act
        client.post("/receipts/rescore?dry_run=false")

    # Assert
    mock_task.delay.assert_called_once_with(dry_run=False)


@pytest.mark.integration
def test_list_receipts_rejects_unknown_confirmation_source(client):
    # Act
    response = client.get("/receipts?confirmation_source=robot")

    # Assert
    assert response.status_code == 422
```

- [ ] **Step 9: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit -m unit -q --no-cov && ../venv/bin/python -m pytest tests/integration/test_rescore_routes.py -q --no-cov`
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/src/app.py backend/src/tasks/rescore_pending_receipts.py backend/src/celery_app.py backend/src/main.py backend/tests/unit/test_app_rescore.py backend/tests/unit/tasks/test_rescore_pending_receipts.py backend/tests/integration/test_rescore_routes.py
git commit -m "feat(backend): backlog rescore task, endpoint and confirmation_source filter"
```

---

### Task 12: Frontend contract — schemas, client, proxy

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/api/receipts/rescore/route.ts`
- Test: `frontend/lib/receiptAutoConfirmSchema.test.ts`

**Interfaces:**
- Produces in `types.ts`: `AutoConfirmReasonSchema`/`AutoConfirmReason`, `RescoreReportSchema`/`RescoreReport`; `CategoryCandidatesSchema` gains optional `source`, `product_id`, `history_count`; `ReceiptScanListItemSchema.confirmation_source`; `ReceiptScanDetailSchema.confirmation_source`, `.auto_confirm_reasons`.
- Produces in `api.ts`: `rescorePendingReceipts(dryRun: boolean): Promise<TaskResponse>`; `listReceipts` accepts `confirmation_source?: "auto" | "manual"`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/lib/receiptAutoConfirmSchema.test.ts
/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import { ReceiptScanDetailSchema, ReceiptScanListItemSchema, RescoreReportSchema } from "./types";

const baseDetail = {
  id: 1,
  filename: "a.jpg",
  status: "to_confirm",
  result: null,
  categories_candidates: {
    category_candidates: [
      {
        product_name: "MLEKO",
        category_candidates: [{ category_id: 1, category_name: "Nabiał", category_score: 0.93 }],
        source: "history",
        product_id: 10,
        history_count: 14,
      },
    ],
  },
  minio_object_key: null,
  transaction: null,
};

describe("receipt auto-confirm schemas", () => {
  it("parses candidate source metadata and reasons", () => {
    const parsed = ReceiptScanDetailSchema.parse({
      ...baseDetail,
      confirmation_source: null,
      auto_confirm_reasons: [{ code: "sum_mismatch", message: "Suma produktów 1,00 zł ≠ 2,00 zł", blocking: true }],
    });

    expect(parsed.categories_candidates?.category_candidates[0].source).toBe("history");
    expect(parsed.categories_candidates?.category_candidates[0].history_count).toBe(14);
    expect(parsed.auto_confirm_reasons?.[0].blocking).toBe(true);
  });

  it("parses legacy detail without new fields", () => {
    const legacy = {
      ...baseDetail,
      categories_candidates: {
        category_candidates: [
          { product_name: "MLEKO", category_candidates: [{ category_id: 1, category_name: "Nabiał", category_score: 0.9 }] },
        ],
      },
    };

    const parsed = ReceiptScanDetailSchema.parse(legacy);

    expect(parsed.confirmation_source).toBeUndefined();
    expect(parsed.categories_candidates?.category_candidates[0].source).toBeUndefined();
  });

  it("parses list item confirmation_source", () => {
    const parsed = ReceiptScanListItemSchema.parse({
      id: 1, filename: "a.jpg", status: "done", vendor: null, date: null, total: null, confirmation_source: "auto",
    });

    expect(parsed.confirmation_source).toBe("auto");
  });

  it("parses rescore report", () => {
    const parsed = RescoreReportSchema.parse({
      dry_run: true, total: 47, eligible: 32, confirmed: 0, skipped: 1, errors: 0,
      top_reasons: [{ code: "low_confidence", message: "Nowy produkt „X”: pewność AI 62%", count: 9 }],
    });

    expect(parsed.eligible).toBe(32);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run lib/receiptAutoConfirmSchema.test.ts`
Expected: FAIL (`RescoreReportSchema` not exported).

- [ ] **Step 3: Implement `types.ts`**

Replace `CategoryCandidatesSchema`:

```ts
export const CategoryCandidatesSchema = z.object({
  product_name: z.string(),
  category_candidates: z.array(CategoryCandidateSchema),
  source: z.enum(["history", "ai"]).nullable().optional(),
  product_id: z.number().nullable().optional(),
  history_count: z.number().nullable().optional(),
});
```

Add before `ReceiptScanListItemSchema`:

```ts
export const ConfirmationSourceSchema = z.enum(["manual", "auto"]);

export const AutoConfirmReasonSchema = z.object({
  code: z.string(),
  message: z.string(),
  blocking: z.boolean(),
});
export type AutoConfirmReason = z.infer<typeof AutoConfirmReasonSchema>;
```

Add to `ReceiptScanListItemSchema`: `confirmation_source: ConfirmationSourceSchema.nullable().optional(),`

Add to `ReceiptScanDetailSchema` (after `ocr_raw`):

```ts
  confirmation_source: ConfirmationSourceSchema.nullable().optional(),
  auto_confirm_reasons: z.array(AutoConfirmReasonSchema).nullable().optional(),
```

Add after `ReceiptScanDetail` type:

```ts
export const RescoreReportSchema = z.object({
  dry_run: z.boolean(),
  total: z.number(),
  eligible: z.number(),
  confirmed: z.number(),
  skipped: z.number(),
  errors: z.number(),
  top_reasons: z.array(z.object({ code: z.string(), message: z.string(), count: z.number() })),
});
export type RescoreReport = z.infer<typeof RescoreReportSchema>;
```

- [ ] **Step 4: Implement `api.ts` and proxy route**

In `listReceipts`: add `confirmation_source?: "auto" | "manual";` to the params type, destructure it, and add `if (confirmation_source) qs.set("confirmation_source", confirmation_source);`.

Add after `processReceipts`:

```ts
export async function rescorePendingReceipts(dryRun: boolean): Promise<TaskResponse> {
  return apiFetch(`/api/receipts/rescore?dry_run=${dryRun ? "true" : "false"}`, TaskResponseSchema, {
    method: "POST",
  });
}
```

```ts
// frontend/app/api/receipts/rescore/route.ts
import { proxyPost } from "@/lib/proxy";

export async function POST(req: Request) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  return proxyPost(`/receipts/rescore${qs ? `?${qs}` : ""}`);
}
```

- [ ] **Step 5: Run tests + types**

Run: `cd frontend && npx vitest run lib/receiptAutoConfirmSchema.test.ts && npx tsc --noEmit`
Expected: PASS, no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts frontend/app/api/receipts/rescore/route.ts frontend/lib/receiptAutoConfirmSchema.test.ts
git commit -m "feat(frontend): schemas and client for receipt auto-confirm"
```

---

### Task 13: Frontend receipt detail — source pills, reasons, auto banner

**Files:**
- Create: `frontend/lib/categorySource.ts`
- Create: `frontend/components/CategorySourcePill.tsx`
- Create: `frontend/components/AutoConfirmReasonsPanel.tsx`
- Modify: `frontend/app/receipts/[id]/page.tsx`
- Test: `frontend/lib/categorySource.test.ts`
- Test: `frontend/components/AutoConfirmReasonsPanel.test.tsx`

**Interfaces:**
- Produces:
  - `categorySourceLabel(info: { source?: "history" | "ai" | null; history_count?: number | null; topScore?: number | null }): string | null`
  - `<CategorySourcePill source historyCount topScore />`
  - `<AutoConfirmReasonsPanel reasons={AutoConfirmReason[]} />` (renders nothing for empty list)

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/lib/categorySource.test.ts
/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import { categorySourceLabel } from "./categorySource";

describe("categorySourceLabel", () => {
  it("labels history with count", () => {
    expect(categorySourceLabel({ source: "history", history_count: 14 })).toBe("z historii (14×)");
  });

  it("labels AI with fraction score as percent", () => {
    expect(categorySourceLabel({ source: "ai", topScore: 0.62 })).toBe("AI · 62%");
  });

  it("labels AI with percent score", () => {
    expect(categorySourceLabel({ source: "ai", topScore: 91 })).toBe("AI · 91%");
  });

  it("labels AI without score", () => {
    expect(categorySourceLabel({ source: "ai", topScore: null })).toBe("AI");
  });

  it("returns null for legacy candidates", () => {
    expect(categorySourceLabel({})).toBeNull();
  });
});
```

```tsx
// frontend/components/AutoConfirmReasonsPanel.test.tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutoConfirmReasonsPanel } from "./AutoConfirmReasonsPanel";

describe("AutoConfirmReasonsPanel", () => {
  it("lists blocking and informational reasons", () => {
    render(
      <AutoConfirmReasonsPanel
        reasons={[
          { code: "sum_mismatch", message: "Suma produktów 47,30 zł ≠ 49,99 zł", blocking: true },
          { code: "vendor_new", message: "Pierwszy paragon ze sklepu „Lidl”", blocking: false },
        ]}
      />
    );

    expect(screen.getByText("Dlaczego nie potwierdzono automatycznie")).toBeInTheDocument();
    expect(screen.getByText("Suma produktów 47,30 zł ≠ 49,99 zł")).toBeInTheDocument();
    expect(screen.getByText("Pierwszy paragon ze sklepu „Lidl”")).toBeInTheDocument();
  });

  it("renders nothing when there are no blocking reasons", () => {
    const { container } = render(
      <AutoConfirmReasonsPanel reasons={[{ code: "vendor_new", message: "x", blocking: false }]} />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run lib/categorySource.test.ts components/AutoConfirmReasonsPanel.test.tsx`
Expected: FAIL (modules missing).

- [ ] **Step 3: Implement helpers and components**

```ts
// frontend/lib/categorySource.ts
export type CategorySourceInfo = {
  source?: "history" | "ai" | null;
  history_count?: number | null;
  topScore?: number | null;
};

export function categorySourceLabel(info: CategorySourceInfo): string | null {
  if (info.source === "history") return `z historii (${info.history_count ?? 0}×)`;
  if (info.source === "ai") {
    if (info.topScore == null) return "AI";
    const percent = Math.round(info.topScore > 1 ? info.topScore : info.topScore * 100);
    return `AI · ${percent}%`;
  }
  return null;
}
```

```tsx
// frontend/components/CategorySourcePill.tsx
import { Pill } from "@/components/ui";
import { categorySourceLabel, type CategorySourceInfo } from "@/lib/categorySource";

export function CategorySourcePill(props: CategorySourceInfo) {
  const label = categorySourceLabel(props);
  if (!label) return null;
  return (
    <Pill variant={props.source === "history" ? "category-primary" : "category-secondary"} size="sm">
      {label}
    </Pill>
  );
}
```

```tsx
// frontend/components/AutoConfirmReasonsPanel.tsx
import type { AutoConfirmReason } from "@/lib/types";
import { clsx } from "clsx";

export function AutoConfirmReasonsPanel({ reasons }: { reasons: AutoConfirmReason[] }) {
  if (!reasons.some((r) => r.blocking)) return null;
  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50/80 p-4 text-sm text-orange-900">
      <p className="font-semibold mb-2">Dlaczego nie potwierdzono automatycznie</p>
      <ul className="list-disc pl-5 space-y-1">
        {reasons.map((r, i) => (
          <li key={`${r.code}-${i}`} className={clsx(!r.blocking && "text-orange-700/70")}>
            {r.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Integrate into `frontend/app/receipts/[id]/page.tsx`**

Imports:

```tsx
import { CategorySourcePill } from "@/components/CategorySourcePill";
import { AutoConfirmReasonsPanel } from "@/components/AutoConfirmReasonsPanel";
```

Extend the candidates map build (where `candidatesMap` is filled):

```tsx
  const sourceMap: Record<string, { source?: "history" | "ai" | null; history_count?: number | null }> = {};

  if (scan.categories_candidates?.category_candidates) {
    for (const entry of scan.categories_candidates.category_candidates) {
      candidatesMap[entry.product_name] = entry.category_candidates;
      sourceMap[entry.product_name] = { source: entry.source, history_count: entry.history_count };
    }
  }
```

Right after the `failed` block (`{scan.status === "failed" && ...}`), add:

```tsx
      {scan.status === "to_confirm" && scan.auto_confirm_reasons && (
        <AutoConfirmReasonsPanel reasons={scan.auto_confirm_reasons} />
      )}
```

Replace the confirmed banner label `<span className="text-green-600 font-semibold text-sm">✓ Potwierdzono</span>` with:

```tsx
                <span className="text-green-600 font-semibold text-sm">
                  {scan.confirmation_source === "auto" ? "✓ Potwierdzony automatycznie" : "✓ Potwierdzono"}
                </span>
```

In the edit form, directly above `{/* Category selector — hide built-in header since we render it above */}`, add:

```tsx
                    {sourceMap[product.name]?.source && (
                      <div className="px-3 pb-2 flex">
                        <CategorySourcePill
                          source={sourceMap[product.name].source}
                          history_count={sourceMap[product.name].history_count}
                          topScore={
                            (candidatesMap[product.name] ?? []).reduce<number | null>(
                              (max, c) => (max == null || c.category_score > max ? c.category_score : max),
                              null
                            )
                          }
                        />
                      </div>
                    )}
```

- [ ] **Step 5: Run tests, lint, types**

Run: `cd frontend && npm run test:run && npm run lint && npx tsc --noEmit`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/categorySource.ts frontend/lib/categorySource.test.ts frontend/components/CategorySourcePill.tsx frontend/components/AutoConfirmReasonsPanel.tsx frontend/components/AutoConfirmReasonsPanel.test.tsx "frontend/app/receipts/[id]/page.tsx"
git commit -m "feat(frontend): show category source and auto-confirm reasons on receipt detail"
```

---

### Task 14: Frontend receipts list — Auto pill, tab, rescore modal

**Files:**
- Create: `frontend/components/RescoreReceiptsModal.tsx`
- Modify: `frontend/app/receipts/page.tsx`
- Test: `frontend/components/RescoreReceiptsModal.test.tsx`

**Interfaces:**
- Consumes: `rescorePendingReceipts` (Task 12), `getPusher` (`frontend/lib/pusher.ts`), `RescoreReport`.
- Produces: `<RescoreReceiptsModal open onClose onFinished />` — `onFinished()` fires after a real (non-dry) run completes.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/components/RescoreReceiptsModal.test.tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RescoreReceiptsModal } from "./RescoreReceiptsModal";

const handlers: Record<string, (data: unknown) => void> = {};
const bind = vi.fn((event: string, cb: (data: unknown) => void) => { handlers[event] = cb; });
const channel = { bind, unbind_all: vi.fn(), unsubscribe: vi.fn() };

vi.mock("@/lib/pusher", () => ({ getPusher: () => ({ subscribe: () => channel }) }));
const rescore = vi.fn();
vi.mock("@/lib/api", () => ({ rescorePendingReceipts: (dry: boolean) => rescore(dry) }));

function renderModal(onFinished = vi.fn()) {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <RescoreReceiptsModal open onClose={vi.fn()} onFinished={onFinished} />
    </QueryClientProvider>
  );
  return onFinished;
}

describe("RescoreReceiptsModal", () => {
  beforeEach(() => {
    rescore.mockReset();
    bind.mockClear();
    for (const k of Object.keys(handlers)) delete handlers[k];
  });

  it("runs dry run, shows report, then confirms", async () => {
    rescore.mockResolvedValueOnce({ task_id: "dry" }).mockResolvedValueOnce({ task_id: "real" });
    const onFinished = renderModal();

    await userEvent.click(screen.getByRole("button", { name: "Sprawdź oczekujące" }));
    expect(rescore).toHaveBeenCalledWith(true);

    // 3 events bound per run (progress, done, error)
    await waitFor(() => expect(bind).toHaveBeenCalledTimes(3));
    handlers["receipt.rescore_done"]({
      task_id: "dry",
      report: { dry_run: true, total: 47, eligible: 32, confirmed: 0, skipped: 0, errors: 0,
        top_reasons: [{ code: "low_confidence", message: "Nowy produkt „X”: pewność AI 62%", count: 9 }] },
    });

    expect(await screen.findByText("32 z 47 paragonów potwierdziłoby się automatycznie.")).toBeInTheDocument();
    expect(screen.getByText("Nowy produkt „X”: pewność AI 62% — 9×")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Potwierdź automatycznie 32" }));
    expect(rescore).toHaveBeenLastCalledWith(false);

    await waitFor(() => expect(bind).toHaveBeenCalledTimes(6));
    handlers["receipt.rescore_done"]({
      task_id: "real",
      report: { dry_run: false, total: 47, eligible: 32, confirmed: 31, skipped: 1, errors: 0, top_reasons: [] },
    });

    expect(await screen.findByText("Potwierdzono automatycznie 31 paragonów.")).toBeInTheDocument();
    expect(onFinished).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run components/RescoreReceiptsModal.test.tsx`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement the modal**

```tsx
// frontend/components/RescoreReceiptsModal.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, Modal } from "@/components/ui";
import { MutationErrorNotice } from "@/components/QueryState";
import { rescorePendingReceipts } from "@/lib/api";
import { getPusher } from "@/lib/pusher";
import type { RescoreReport } from "@/lib/types";

type Phase = "idle" | "running" | "report" | "done" | "error";

export function RescoreReceiptsModal({
  open,
  onClose,
  onFinished,
}: {
  open: boolean;
  onClose: () => void;
  onFinished: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState<{ index: number; total: number } | null>(null);
  const [report, setReport] = useState<RescoreReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);

  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const mutation = useMutation({
    mutationFn: (dryRun: boolean) => rescorePendingReceipts(dryRun),
    onMutate: () => {
      setPhase("running");
      setProgress(null);
      setErrorMsg(null);
    },
    onSuccess: ({ task_id }) => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
      const channel = getPusher().subscribe("receipts");
      channelRef.current = channel;
      channel.bind("receipt.rescore_progress", (data: { task_id: string; index: number; total: number }) => {
        if (data.task_id !== task_id) return;
        setProgress({ index: data.index, total: data.total });
      });
      channel.bind("receipt.rescore_done", (data: { task_id: string; report: RescoreReport }) => {
        if (data.task_id !== task_id) return;
        setReport(data.report);
        setPhase(data.report.dry_run ? "report" : "done");
        if (!data.report.dry_run) onFinished();
        channel.unbind_all();
        channel.unsubscribe();
      });
      channel.bind("receipt.rescore_error", (data: { task_id: string; error: string }) => {
        if (data.task_id !== task_id) return;
        setErrorMsg(data.error);
        setPhase("error");
        channel.unbind_all();
        channel.unsubscribe();
      });
    },
    onError: () => setPhase("idle"),
  });

  const close = () => {
    if (phase === "running") return;
    setPhase("idle");
    setReport(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={close} maxWidth="lg">
      <div className="p-6 flex flex-col gap-4 text-sm">
        <h2 className="text-lg font-semibold text-gray-900">Przelicz oczekujące paragony</h2>
        <MutationErrorNotice mutation={mutation} />

        {phase === "idle" && (
          <p className="text-gray-600">
            Kategorie paragonów „Do potwierdzenia” zostaną przeliczone na podstawie historii. Najpierw zobaczysz
            raport — nic nie zostanie potwierdzone bez Twojej zgody.
          </p>
        )}

        {phase === "running" && (
          <p className="text-gray-600">
            {progress ? `Przeliczanie ${progress.index} / ${progress.total}…` : "Uruchamianie…"}
          </p>
        )}

        {phase === "report" && report && (
          <div className="flex flex-col gap-2">
            <p className="font-medium text-gray-900">
              {report.eligible} z {report.total} paragonów potwierdziłoby się automatycznie.
            </p>
            {report.top_reasons.length > 0 && (
              <>
                <p className="text-gray-500">Najczęstsze blokady:</p>
                <ul className="list-disc pl-5 text-gray-700 space-y-1">
                  {report.top_reasons.map((r) => (
                    <li key={r.code}>{`${r.message} — ${r.count}×`}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {phase === "done" && report && (
          <p className="font-medium text-green-700">
            Potwierdzono automatycznie {report.confirmed} paragonów.
          </p>
        )}

        {phase === "error" && <p className="text-red-600">Przeliczanie nie powiodło się: {errorMsg}</p>}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={close} disabled={phase === "running"}>
            Zamknij
          </Button>
          {phase === "idle" && (
            <Button onClick={() => mutation.mutate(true)} disabled={mutation.isPending}>
              Sprawdź oczekujące
            </Button>
          )}
          {phase === "report" && report && report.eligible > 0 && (
            <Button onClick={() => mutation.mutate(false)} disabled={mutation.isPending}>
              {`Potwierdź automatycznie ${report.eligible}`}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
```

- [ ] **Step 4: Integrate into `frontend/app/receipts/page.tsx`**

Import: `import { RescoreReceiptsModal } from "@/components/RescoreReceiptsModal";`

Filters — replace constants:

```tsx
const STATUS_FILTERS = [
  "all",
  "pending",
  "processing",
  "to_confirm",
  "done",
  "auto",
  "failed",
] as const;

const FILTER_LABELS: Record<string, string> = {
  all: "Wszystkie",
  pending: "Oczekujące",
  processing: "Przetwarzanie",
  to_confirm: "Do potwierdzenia",
  done: "Gotowe",
  auto: "Potwierdzone automatycznie",
  failed: "Błąd",
};
```

State: `const [rescoreOpen, setRescoreOpen] = useState(false);`

In `listQuery.queryFn`, replace the `status:` line and add the new param:

```tsx
        status: statusFilter === "auto" ? "done" : statusFilter !== "all" ? statusFilter : undefined,
        confirmation_source: statusFilter === "auto" ? "auto" : undefined,
```

In the `FilterTabs` label mapping, render `auto` without a count:

```tsx
            label: s === "all"
              ? <span>{FILTER_LABELS.all} <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{totalAll}</span></span>
              : s === "auto"
                ? <span>{FILTER_LABELS.auto}</span>
                : <span>{FILTER_LABELS[s] ?? s} <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{statusCounts[s] ?? 0}</span></span>,
```

Status column accessor:

```tsx
      accessor: (r) => (
        <span className="inline-flex items-center gap-1">
          <StatusBadge status={r.status} />
          {r.confirmation_source === "auto" && <Pill variant="category-secondary" size="sm">Auto</Pill>}
        </span>
      ),
```

`PageHeader` actions — wrap buttons:

```tsx
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="md" onClick={() => setRescoreOpen(true)}>
              Przelicz oczekujące
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => processMutation.mutate()}
              disabled={processMutation.isPending || progress?.status === "running"}
            >
              {processMutation.isPending || progress?.status === "running" ? "Przetwarzanie…" : "Przetwórz paragony"}
            </Button>
          </div>
        }
```

Render the modal right after `<PageHeader ... />`:

```tsx
      <RescoreReceiptsModal
        open={rescoreOpen}
        onClose={() => setRescoreOpen(false)}
        onFinished={() => {
          queryClient.invalidateQueries({ queryKey: ["receipts"] });
          queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
        }}
      />
```

Also invalidate after a dry run is not needed (lists do not change status), but the detail page reasons do change: in `onFinished` it is sufficient because dry runs only rewrite candidates/reasons of `to_confirm` scans that the user opens fresh (`staleTime` 30 s). Leave as is.

- [ ] **Step 5: Run tests, lint, types**

Run: `cd frontend && npm run test:run && npm run lint && npx tsc --noEmit`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/RescoreReceiptsModal.tsx frontend/components/RescoreReceiptsModal.test.tsx frontend/app/receipts/page.tsx
git commit -m "feat(frontend): auto-confirmed filter, badge and backlog rescore modal"
```

---

### Task 15: Versions, env example, docs, full verification

**Files:**
- Modify: `backend/src/version.py` → `VERSION = "1.11.0"`
- Modify: `frontend/package.json` → `"version": "1.10.0"`
- Modify: `frontend/package-lock.json` → root `"version": "1.10.0"` and `packages[""].version` `"1.10.0"`
- Modify: `.env.example`
- Modify: `context.md`, `CLAUDE.md` (only after checking `git status` — the user had uncommitted edits there when this plan was written; if still dirty, ask before touching)

- [ ] **Step 1: Bump versions**

`backend/src/version.py`:

```python
VERSION = "1.11.0"
```

`backend/tests/unit/test_version.py` has no exact-version assertion (semver regex only) — no change needed.

Frontend: edit `"version"` in `package.json` and both occurrences in `package-lock.json` (top-level `version` and `packages[""].version`).

- [ ] **Step 2: Document env vars in `.env.example`** (append after `MODEL=gpt-5`)

```
# Receipt auto-confirm (history-based). Keep disabled until the dry-run report looks good.
RECEIPT_AUTO_CONFIRM_ENABLED=false
RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE=0.9
RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT=2
RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE=0.9
```

- [ ] **Step 3: Docs** — in `context.md` → *Kluczowe decyzje* add a bullet:

```
- **Auto-potwierdzanie paragonów:** `ProductResolver` (dokładne → `pg_trgm`/`rapidfuzz` → LLM z listy) + `category_history` (dominująca kategoria) → `CategoriesService` tylko dla reszty → `receipt_auto_confirm.evaluate` (suma, pewność). `confirmation_source` `manual|auto`, powody w `auto_confirm_reasons`; flaga `RECEIPT_AUTO_CONFIRM_ENABLED` (domyślnie off); zaległe: `POST /receipts/rescore?dry_run=`. Ground truth tylko z ręcznych potwierdzeń.
```

Update the version line (FE 1.10.0, BE 1.11.0) in `context.md` and `CLAUDE.md` *Recent Changes*/*Active Technologies* accordingly.

- [ ] **Step 4: Full verification**

Run: `cd backend && ../venv/bin/python -m pytest tests/unit -m unit -q`
Expected: all PASS.
Run: `cd backend && ../venv/bin/python -m pytest tests/integration -m integration -q --no-cov`
Expected: all PASS (requires Docker).
Run: `cd frontend && npm run test:run && npm run lint && npx tsc --noEmit && npm run build`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/version.py frontend/package.json frontend/package-lock.json .env.example context.md CLAUDE.md
git commit -m "chore: bump BE 1.11.0 / FE 1.10.0 and document receipt auto-confirm"
```

- [ ] **Step 6: Rollout checklist (manual, after deploy)**

1. Apply migrations (`yoyo apply`); check logs for the `pg_trgm not available` notice — if present, fuzzy search runs on `rapidfuzz`.
2. Keep `RECEIPT_AUTO_CONFIRM_ENABLED=false`.
3. On `/receipts` click „Przelicz oczekujące” → „Sprawdź oczekujące”; review the report and a few receipts' reasons/pills.
4. If satisfied, click „Potwierdź automatycznie N”; spot-check the „Potwierdzone automatycznie” tab.
5. Set `RECEIPT_AUTO_CONFIRM_ENABLED=true` for backend and celery-worker; restart.
6. Watch `prompt_analytics.auto_confirm_reverted` over the next weeks to tune thresholds.
