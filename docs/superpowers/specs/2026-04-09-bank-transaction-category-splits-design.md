# Bank Transaction Category Splits — Design

**Date:** 2026-04-09  
**Status:** Approved  
**Feature branch:** `009-bank-transaction-category-splits` (suggested)

---

## Problem

Bank transactions without linked receipts currently support only one category. Some transactions (e.g. a supermarket run covering food + household chemicals) span multiple expense types. The user needs to split a single transaction amount across multiple categories, each with an explicit PLN amount.

---

## Scope & Constraints

- Applies only to bank transactions **without** a linked receipt. Receipt-linked transactions derive their categories from receipt line items (unchanged).
- The AI category suggestions remain single-category (unchanged).
- Default behavior is unchanged: one transaction → one category.
- Splitting is **optional** and user-initiated.
- The sum of all split amounts **must equal** the transaction amount exactly.
- A split requires **at least 2** category–amount pairs.
- Polish UI strings throughout.

---

## Data Model

### New table: `bank_transaction_category_splits`

```sql
-- depends: 20260227_01_bank_transactions
CREATE TABLE IF NOT EXISTS bank_transaction_category_splits (
    id                  SERIAL PRIMARY KEY,
    bank_transaction_id INTEGER NOT NULL
                            REFERENCES bank_transactions(id) ON DELETE CASCADE,
    category_id         INTEGER NOT NULL
                            REFERENCES categories(id) ON DELETE RESTRICT,
    amount              NUMERIC(12, 2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_btcs_bank_transaction_id
    ON bank_transaction_category_splits(bank_transaction_id);
```

### Invariant: one or the other, never both

| State | `bank_transactions.category_id` | rows in splits table |
|---|---|---|
| No category | NULL | 0 |
| Single category | `<id>` | 0 |
| Split | NULL | ≥ 2 |

The backend enforces this invariant on every write:
- `PUT /splits` → clears `category_id`, replaces all splits
- `DELETE /splits` → removes all splits, sets `category_id = NULL`
- `PATCH /category` → deletes any existing splits before setting `category_id`

---

## Backend

### Pydantic models (`backend/src/data.py`)

```python
class BankTransactionSplit(BaseModel):
    id: int
    category_id: int
    category_name: str
    amount: Decimal

class SplitItem(BaseModel):
    category_id: int
    amount: Decimal

class UpdateBankTransactionSplitsRequest(BaseModel):
    splits: list[SplitItem]  # len >= 2, sum == transaction.amount
```

**`BankTransactionListItem` — two new fields:**
```python
split_category_name: str | None = None  # first split's category name
split_count: int | None = None          # total number of splits (None or 0 = single-category mode)
```

**`BankTransactionDetail` — one new field:**
```python
category_splits: list[BankTransactionSplit] | None = None
```

### New repository: `BankTransactionSplitsRepository`

- `upsert_splits(tx_id, splits: list[SplitItem]) -> list[BankTransactionSplit]`  
  DELETE existing + INSERT new in one DB transaction. Clears `category_id` on `bank_transactions`.
- `delete_splits(tx_id) -> bool`  
  Deletes all splits. Does NOT touch `category_id` (caller decides).
- `get_splits(tx_id) -> list[BankTransactionSplit]`  
  LEFT JOIN with categories to resolve names.

### Changes to `BankTransactionsRepository`

- `get_list(...)` — adds LEFT JOIN on `bank_transaction_category_splits` to populate `split_category_name` and `split_count`
- `get_by_id(tx_id)` — adds LEFT JOIN to populate `category_splits`
- `update_category(tx_id, category_id)` — calls `delete_splits(tx_id)` first to preserve invariant

### New routes (`backend/src/main.py`)

```
PUT  /bank-transactions/{tx_id}/splits
DELETE /bank-transactions/{tx_id}/splits
```

**PUT validation (returns 409 on failure):**
1. `len(request.splits) >= 2`
2. `sum(s.amount for s in request.splits) == transaction.amount` (exact Decimal comparison)
3. All `category_id` values must exist (404 otherwise)

Both endpoints return `BankTransactionDetail`.

---

## Frontend

### Zod schemas (`frontend/lib/types.ts`)

```typescript
const BankTransactionSplitSchema = z.object({
  id: z.number(),
  category_id: z.number(),
  category_name: z.string(),
  amount: z.number(),
});

// BankTransactionListItemSchema — add:
split_category_name: z.string().nullable().optional(),
split_count: z.number().nullable().optional(),

// BankTransactionDetailSchema — add:
category_splits: z.array(BankTransactionSplitSchema).nullable().optional(),
```

### API functions (`frontend/lib/api.ts`)

```typescript
saveBankTransactionSplits(
  id: number,
  splits: { category_id: number; amount: number }[]
): Promise<BankTransactionDetail>  // PUT /api/bank-transactions/{id}/splits

deleteBankTransactionSplits(id: number): Promise<BankTransactionDetail>
// DELETE /api/bank-transactions/{id}/splits
```

### Next.js proxy route (`frontend/app/api/bank-transactions/[id]/splits/route.ts`)

Thin proxy using `proxyPut` and `proxyDelete` from `lib/proxy.ts`. No business logic.

### List view — Category column (`frontend/app/bank-transactions/page.tsx`)

Priority order (first match wins):

| Condition | Rendered |
|---|---|
| `receipt_category_name` set | `receipt_category_name` + optional `+N` badge (unchanged) |
| `split_count >= 2` | `split_category_name` + `+N` badge (same visual style as receipt case) |
| `category_name` set | `category_name` plain text (unchanged) |
| none | *Nie przypisano* italic gray (unchanged) |

### Category card — expanded list row & detail page

**Single-category mode** (no splits — current behaviour, unchanged):
```
[dropdown]   [Zapisz kategorię]
[AI candidates with score bars]
────────────────────
+ Podziel na kategorie  ← new link, triggers split editor
```

**Split mode** (splits exist):
```
Podział na kategorie:
  [Jedzenie  ▾]  [ 120,00 ]  [×]
  [Chemia    ▾]  [  80,00 ]  [×]
  [+ Dodaj kategorię]

  Suma: 200,00 / 200,00 PLN  ✓      ← live running total
  [Zapisz podział]   [Anuluj]
────────────────────
Wróć do jednej kategorii  ← DELETE /splits + clears category_id
```

**UI rules:**
- "Zapisz podział" is disabled while `sum(amounts) ≠ transaction.amount` or any field is empty.
- Live sum is shown in red when it doesn't match, green/neutral when it does.
- Minimum 2 rows; adding a row appends a blank entry; removing a row is only allowed when ≥ 3 rows exist (to keep ≥ 2).
- Category dropdowns reuse the same `listCategories()` data already fetched on the page.
- After a successful save or delete, `queryClient.invalidateQueries()` on the relevant bank transaction keys.
- "Wróć do jednej kategorii" calls `deleteBankTransactionSplits(id)` — no category is pre-selected afterwards (user picks from dropdown as usual).

---

## Testing

### Backend unit tests

- `BankTransactionSplitsRepository.upsert_splits` — happy path, sum mismatch, invalid category
- `BankTransactionsRepository.update_category` — verify splits are deleted before category is set
- Route `PUT /bank-transactions/{id}/splits` — validates len < 2, sum mismatch, category not found
- Route `DELETE /bank-transactions/{id}/splits` — verify `category_id` is NULL afterwards

### Backend integration test

- Full round-trip: import transaction → split into 2 categories → verify list shows `split_count=2` → delete split → verify `category_id = NULL`

### Frontend

- Category column rendering: receipt case, split case, single-category case, none case
- Split editor: sum validation disables save button, running total updates live

---

## Out of scope

- AI suggestions for splits (LLM continues to propose one category only)
- Splitting receipt-linked transactions (categories come from receipt items)
- Reporting / analytics aggregated by split amounts (future feature)
