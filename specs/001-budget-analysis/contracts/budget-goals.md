# API Contracts: Financial Goals

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13  
All routes in `backend/src/main.py` under `# --- Budget Analysis ---`.

---

## GET /budget/goals/surplus

Returns the current monthly surplus analysis used as the basis for goal allocation decisions.

**Response 200**: `MonthlySurplusResponse`
```json
{
  "avg_income_3m_pln": 12000.00,
  "avg_expenses_3m_pln": 5200.00,
  "avg_surplus_3m_pln": 6800.00,
  "current_month_income_pln": 12000.00,
  "current_month_expenses_pln": 4800.00,
  "current_month_surplus_pln": 7200.00,
  "total_monthly_goal_allocations_pln": 2500.00,
  "unallocated_surplus_pln": 4700.00
}
```

---

## GET /budget/goals

Returns all financial goals (active and inactive), ordered by `priority_rank` ascending.

**Response 200**: `list[FinancialGoalListItem]`
```json
[
  {
    "id": 1,
    "name": "Nadpłata kredytu hipotecznego",
    "target_amount_pln": 50000.00,
    "target_date": null,
    "priority_rank": 1,
    "monthly_allocation_amount_pln": 1000.00,
    "accumulated_progress_pln": 3000.00,
    "progress_pct": 6.0,
    "months_to_completion": 47,
    "projected_completion_date": "2030-02-01",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Wyjazd w góry",
    "target_amount_pln": 3000.00,
    "target_date": "2026-07-01",
    "priority_rank": 2,
    "monthly_allocation_amount_pln": 750.00,
    "accumulated_progress_pln": 750.00,
    "progress_pct": 25.0,
    "months_to_completion": 3,
    "projected_completion_date": "2026-06-01",
    "is_active": true
  }
]
```

---

## POST /budget/goals

Creates a new financial goal.

**Body**: `CreateFinancialGoalRequest`
```json
{
  "name": "Fundusz na budowę domu",
  "target_amount_pln": 200000.00,
  "target_date": "2030-01-01",
  "priority_rank": 3,
  "monthly_allocation_amount_pln": 2000.00
}
```
**Response 201**: `FinancialGoalListItem` (full object with computed fields)  
**Errors**: `400` if `target_amount_pln` ≤ 0 or `monthly_allocation_amount_pln` < 0.

---

## PUT /budget/goals/{id}

Updates an existing financial goal. All fields are optional — only provided fields are updated.

**Path param**: `id` (int)  
**Body**: `UpdateFinancialGoalRequest`
```json
{
  "monthly_allocation_amount_pln": 1500.00
}
```
**Response 200**: `FinancialGoalListItem`  
**Errors**: `404` if goal not found.

**Note on progress accumulation**: `accumulated_progress` advances automatically on the 1st of each month by the goal's `monthly_allocation_amount` (Celery beat task `advance_goal_progress`). It can also be manually adjusted via this endpoint by providing `accumulated_progress_pln` (reserved for corrections).

---

## DELETE /budget/goals/{id}

Soft-deletes a goal by setting `is_active = false`. Historical progress is preserved.

**Path param**: `id` (int)  
**Response 204**  
**Errors**: `404` if goal not found.
