# API Contracts: Budget Analysis (Read & Affordability)

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13  
All routes in `backend/src/main.py` under `# --- Budget Analysis ---`.

---

## GET /budget/analysis/monthly

Returns spending breakdown by category for a given month with month-over-month comparison.

**Query params**:
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `year` | int | No | current year | YYYY |
| `month` | int | No | current month | 1–12 |

**Response 200**: `BudgetMonthlyResponse`
```json
{
  "year": 2026,
  "month": 3,
  "total_expenses_pln": 5430.50,
  "total_income_pln": 12000.00,
  "surplus_pln": 6569.50,
  "categories": [
    {
      "category_id": 4,
      "category_name": "Jedzenie",
      "classification": "essential",
      "total_pln": 1200.00,
      "pct_of_total": 22.1,
      "prev_month_pln": 1100.00,
      "change_pct": 9.1
    }
  ],
  "prev_month_total_pln": 5100.00,
  "month_over_month_change_pct": 6.5
}
```

**Errors**: `400` if year/month invalid.  
**Index requirement**: Existing indexes on `booking_date` (bank/cash transactions) cover this query.

---

## GET /budget/analysis/recurring-expenses

Returns detected recurring monthly and annual cyclical expenses.

**Query params**: none  
**Response 200**: `list[RecurringExpenseItem]`
```json
[
  {
    "vendor_name": "Orange Polska",
    "category_name": "Telefon",
    "frequency": "monthly",
    "avg_amount_pln": 89.99,
    "last_occurrence_date": "2026-03-02",
    "next_expected_date": "2026-04-02",
    "amount_min_pln": 89.99,
    "amount_max_pln": 89.99,
    "occurrence_count": 14
  },
  {
    "vendor_name": "PZU",
    "category_name": "Ubezpieczenie",
    "frequency": "annual",
    "avg_amount_pln": 2950.00,
    "last_occurrence_date": "2025-11-15",
    "next_expected_date": "2026-11-15",
    "amount_min_pln": 2800.00,
    "amount_max_pln": 3100.00,
    "occurrence_count": 3
  }
]
```

**Notes**: Computed live from transaction history using the heuristic in `research.md`. Response cached for 1 hour (React Query `staleTime`).

---

## GET /budget/analysis/cyclical-alerts

Returns cyclical expenses with next occurrence within 90 days, sorted by `days_until` ascending.

**Query params**: none  
**Response 200**: `list[CyclicalAlertItem]`
```json
[
  {
    "vendor_name": "PZU",
    "category_name": "Ubezpieczenie",
    "next_expected_date": "2026-06-01",
    "days_until": 80,
    "expected_amount_pln": 2950.00,
    "amount_range_pln": "2800–3100 PLN"
  }
]
```

---

## GET /budget/analysis/affordability

Evaluates whether a given amount is strategically affordable right now.

**Query params**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `amount_pln` | float | Yes | Purchase amount to evaluate |

**Response 200**: `AffordabilityCheckResponse`
```json
{
  "verdict": "yellow",
  "amount_pln": 500.00,
  "available_this_month_pln": 3200.00,
  "upcoming_obligations_30d_pln": 890.00,
  "active_goal_allocations_pln": 1500.00,
  "freely_available_pln": 810.00,
  "financial_focus_label": "Nadpłata kredytu hipotecznego",
  "narrative": "Technicznie możesz sobie pozwolić na ten wydatek, ale 500 zł pochodzi z puli zarezerwowanej na nadpłatę kredytu. Rozważ, czy to naprawdę teraz priorytet."
}
```

**Errors**: `400` if `amount_pln` ≤ 0.

---

## GET /budget/category-classifications

Returns all spending categories with their current essential/discretionary classification.

**Response 200**: `list[CategoryClassificationItem]`  
**Side effect**: If the table has no entries, auto-seeds all categories using keyword heuristic (see `research.md`).

---

## PUT /budget/category-classifications/{category_id}

Overrides the classification for a specific category. Sets `is_user_override = true`.

**Path param**: `category_id` (int)  
**Body**: `UpdateCategoryClassificationRequest`
```json
{ "classification": "essential" }
```
**Response 200**: `CategoryClassificationItem`  
**Errors**: `404` if category_id not found; `400` if classification value invalid.

---

## GET /budget/financial-focus

Returns the currently active financial focus. Returns `null` fields if none is set.

**Response 200**: `FinancialFocusResponse`
```json
{
  "id": 1,
  "label": "Nadpłata kredytu hipotecznego",
  "description": "Chcę nadpłacać kredyt o min. 1000 zł miesięcznie",
  "is_active": true
}
```

---

## PUT /budget/financial-focus

Sets (or replaces) the active financial focus. Deactivates any previously active focus.

**Body**: `SetFinancialFocusRequest`
```json
{
  "label": "Fundusz na budowę domu",
  "description": "Oszczędzam na wkład własny i koszty budowy"
}
```
**Response 200**: `FinancialFocusResponse`

---

## POST /budget/emergency-advisor

Given an emergency expense amount, returns discretionary spending cuts and goal impact analysis.

**Body**: `EmergencyAdvisorRequest`
```json
{ "amount_pln": 4000.00, "description": "Nowy laptop do pracy" }
```
**Response 200**: `EmergencyAdvisorResponse`
```json
{
  "amount_pln": 4000.00,
  "fully_coverable_by_cuts": true,
  "discretionary_cuts": [
    {
      "category_name": "Restauracje",
      "classification": "discretionary",
      "avg_monthly_spend_pln": 600.00,
      "suggested_cut_pln": 600.00,
      "months_to_cover": 6.7
    },
    {
      "category_name": "Rozrywka",
      "classification": "discretionary",
      "avg_monthly_spend_pln": 250.00,
      "suggested_cut_pln": 250.00,
      "months_to_cover": 16.0
    }
  ],
  "total_cuttable_pln": 850.00,
  "goal_impacts": [
    {
      "goal_id": 2,
      "goal_name": "Wyjazd w góry",
      "monthly_allocation_pln": 500.00,
      "impact_description": "Wstrzymanie tej alokacji przez 8 miesięcy pokryje koszt laptopa."
    }
  ],
  "recovery_months": 5,
  "narrative": "Zakup laptopa za 4 000 zł można sfinansować ograniczając wydatki na restauracje i rozrywkę przez ok. 5 miesięcy lub wstrzymując alokację na cel 'Wyjazd w góry'."
}
```
