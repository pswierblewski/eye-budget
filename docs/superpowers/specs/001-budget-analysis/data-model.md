# Data Model: Budget Analysis & Insights

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13

---

## Database Schema (PostgreSQL)

### Migration dependency chain

```
20260310_01_readd-text-regions   ← most recent existing migration
  └─ 20260313_01_budget-category-classifications
       └─ 20260313_02_budget-financial-focus
            └─ 20260313_03_budget-financial-goals
                 └─ 20260313_04_budget-simulations
                      └─ 20260313_05_budget-ai-recommendations
```

---

### Table: `budget_category_classifications`

Stores the essential/discretionary classification per spending category. Auto-seeded on first access; user override flag separates system-defaults from manual choices.

```sql
-- Migration: 20260313_01_budget-category-classifications
-- depends: 20260310_01_readd-text-regions

CREATE TABLE IF NOT EXISTS budget_category_classifications (
    id               SERIAL PRIMARY KEY,
    category_id      INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    classification   VARCHAR(20) NOT NULL CHECK (classification IN ('essential', 'discretionary')),
    is_user_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_budget_category_classifications_category UNIQUE (category_id)
);

CREATE INDEX IF NOT EXISTS idx_budget_cat_class_category_id
    ON budget_category_classifications(category_id);
```

---

### Table: `budget_financial_focus`

Holds the user's active financial priority (e.g. "Nadpłata kredytu hipotecznego"). Only one record is active at a time.

```sql
-- Migration: 20260313_02_budget-financial-focus
-- depends: 20260313_01_budget-category-classifications

CREATE TABLE IF NOT EXISTS budget_financial_focus (
    id          SERIAL PRIMARY KEY,
    label       VARCHAR(200) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### Table: `budget_financial_goals`

User-defined savings targets. Progress accumulates via monthly surplus allocations.

```sql
-- Migration: 20260313_03_budget-financial-goals
-- depends: 20260313_02_budget-financial-focus

CREATE TABLE IF NOT EXISTS budget_financial_goals (
    id                        SERIAL PRIMARY KEY,
    name                      VARCHAR(200) NOT NULL,
    target_amount             NUMERIC(12,2) NOT NULL,
    target_date               DATE,
    priority_rank             INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    accumulated_progress      NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_goals_is_active
    ON budget_financial_goals(is_active);
```

---

### Table: `budget_simulations`

Stores both the input parameters and the computed result of a what-if simulation.

```sql
-- Migration: 20260313_04_budget-simulations
-- depends: 20260313_03_budget-financial-goals

CREATE TABLE IF NOT EXISTS budget_simulations (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    expense_name        VARCHAR(200) NOT NULL,
    expense_amount      NUMERIC(12,2) NOT NULL,
    expense_type        VARCHAR(20) NOT NULL CHECK (expense_type IN ('one_time', 'recurring')),
    expense_start_date  DATE NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    result_json         JSONB,
    error_message       TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_simulations_status
    ON budget_simulations(status);
CREATE INDEX IF NOT EXISTS idx_budget_simulations_created_at
    ON budget_simulations(created_at DESC);
```

---

### Table: `budget_ai_recommendations`

Stores AI-generated background recommendations. The `is_current` flag marks the latest generation.

```sql
-- Migration: 20260313_05_budget-ai-recommendations
-- depends: 20260313_04_budget-simulations

CREATE TABLE IF NOT EXISTS budget_ai_recommendations (
    id                  SERIAL PRIMARY KEY,
    generated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    data_through_date   DATE NOT NULL,
    recommendations_json JSONB NOT NULL DEFAULT '[]',
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,
    months_of_data      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_budget_ai_recs_is_current
    ON budget_ai_recommendations(is_current);
CREATE INDEX IF NOT EXISTS idx_budget_ai_recs_generated_at
    ON budget_ai_recommendations(generated_at DESC);
```

---

## Pydantic Models (backend/src/data.py)

All models are added in a new `# --- Budget Analysis ---` section at the end of `data.py`.

### Category Classifications

```python
class CategoryClassificationItem(BaseModel):
    category_id: int
    category_name: str
    classification: str           # 'essential' | 'discretionary'
    is_user_override: bool

class UpdateCategoryClassificationRequest(BaseModel):
    classification: str           # 'essential' | 'discretionary'
```

### Financial Focus

```python
class FinancialFocusResponse(BaseModel):
    id: Optional[int]
    label: str
    description: Optional[str]
    is_active: bool

class SetFinancialFocusRequest(BaseModel):
    label: str
    description: Optional[str] = None
```

### Monthly Budget Analysis

```python
class BudgetCategoryMonthlyItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    classification: str           # 'essential' | 'discretionary'
    total_pln: float
    pct_of_total: float
    prev_month_pln: float
    change_pct: float             # positive = more spending vs prior month

class BudgetMonthlyResponse(BaseModel):
    year: int
    month: int                    # 1–12
    total_expenses_pln: float
    total_income_pln: float
    surplus_pln: float
    categories: list[BudgetCategoryMonthlyItem]
    prev_month_total_pln: float
    month_over_month_change_pct: float
```

### Recurring & Cyclical Expenses

```python
class RecurringExpenseItem(BaseModel):
    vendor_name: str
    category_name: Optional[str]
    frequency: str                # 'monthly' | 'annual'
    avg_amount_pln: float
    last_occurrence_date: str     # ISO date
    next_expected_date: str       # ISO date
    amount_min_pln: float
    amount_max_pln: float
    occurrence_count: int

class CyclicalAlertItem(BaseModel):
    vendor_name: str
    category_name: Optional[str]
    next_expected_date: str       # ISO date
    days_until: int
    expected_amount_pln: float
    amount_range_pln: str         # e.g. "2800–3200 PLN"
```

### Affordability Check

```python
class AffordabilityCheckRequest(BaseModel):
    amount_pln: float
    description: Optional[str] = None

class AffordabilityCheckResponse(BaseModel):
    verdict: str                  # 'green' | 'yellow' | 'red'
    amount_pln: float
    available_this_month_pln: float
    upcoming_obligations_30d_pln: float
    active_goal_allocations_pln: float
    freely_available_pln: float
    financial_focus_label: Optional[str]
    narrative: str                # Polish
```

### Financial Goals

```python
class FinancialGoalListItem(BaseModel):
    id: int
    name: str
    target_amount_pln: float
    target_date: Optional[str]
    priority_rank: int
    monthly_allocation_amount_pln: float
    accumulated_progress_pln: float
    progress_pct: float
    months_to_completion: Optional[int]
    projected_completion_date: Optional[str]
    is_active: bool

class CreateFinancialGoalRequest(BaseModel):
    name: str
    target_amount_pln: float
    target_date: Optional[str] = None
    priority_rank: int = 0
    monthly_allocation_amount_pln: float = 0.0

class UpdateFinancialGoalRequest(BaseModel):
    name: Optional[str] = None
    target_amount_pln: Optional[float] = None
    target_date: Optional[str] = None
    priority_rank: Optional[int] = None
    monthly_allocation_amount_pln: Optional[float] = None
    is_active: Optional[bool] = None

class MonthlySurplusResponse(BaseModel):
    avg_income_3m_pln: float
    avg_expenses_3m_pln: float
    avg_surplus_3m_pln: float
    current_month_income_pln: float
    current_month_expenses_pln: float
    current_month_surplus_pln: float
    total_monthly_goal_allocations_pln: float
    unallocated_surplus_pln: float
```

### Budget Simulation

```python
class CreateBudgetSimulationRequest(BaseModel):
    name: str
    expense_name: str
    expense_amount_pln: float
    expense_type: str             # 'one_time' | 'recurring'
    expense_start_date: str       # ISO date

class SimulationMonthlyPoint(BaseModel):
    month: str                    # 'YYYY-MM'
    baseline_surplus_pln: float
    simulated_surplus_pln: float

class SimulationGoalImpact(BaseModel):
    goal_id: int
    goal_name: str
    baseline_completion_date: Optional[str]
    simulated_completion_date: Optional[str]
    delay_months: int

class SimulationSuggestion(BaseModel):
    description: str              # Polish
    monthly_saving_pln: float
    months_required: int

class SimulationResultPayload(BaseModel):
    projection: list[SimulationMonthlyPoint]
    goal_impacts: list[SimulationGoalImpact]
    ai_summary: str               # Polish narrative
    ai_implications: str          # Polish
    ai_suggestions: list[SimulationSuggestion]

class BudgetSimulationListItem(BaseModel):
    id: int
    name: str
    expense_name: str
    expense_amount_pln: float
    expense_type: str
    expense_start_date: str
    status: str
    created_at: str

class BudgetSimulationDetail(BaseModel):
    id: int
    name: str
    expense_name: str
    expense_amount_pln: float
    expense_type: str
    expense_start_date: str
    status: str
    result: Optional[SimulationResultPayload]
    error_message: Optional[str]
    created_at: str
```

### AI Recommendations

```python
class AIInsightItem(BaseModel):
    title: str                    # Polish
    body: str                     # Polish; references specific PLN amounts
    amount_pln: Optional[float]
    insight_type: str             # 'saving_opportunity' | 'goal_advice' | 'warning' | 'general'

class AIRecommendationsResponse(BaseModel):
    insights: list[AIInsightItem]
    generated_at: Optional[str]   # ISO datetime
    data_through_date: Optional[str]
    months_of_data: int
    has_sufficient_data: bool     # True when months_of_data >= 3
```

### Emergency Advisor

```python
class EmergencyAdvisorRequest(BaseModel):
    amount_pln: float
    description: Optional[str] = None

class EmergencyReductionOption(BaseModel):
    category_name: str
    classification: str           # always 'discretionary'
    avg_monthly_spend_pln: float
    suggested_cut_pln: float
    months_to_cover: float        # how many months of cuts cover the emergency

class EmergencyGoalImpact(BaseModel):
    goal_id: int
    goal_name: str
    monthly_allocation_pln: float
    impact_description: str       # Polish

class EmergencyAdvisorResponse(BaseModel):
    amount_pln: float
    fully_coverable_by_cuts: bool
    discretionary_cuts: list[EmergencyReductionOption]
    total_cuttable_pln: float
    goal_impacts: list[EmergencyGoalImpact]
    recovery_months: Optional[int]
    narrative: str                # Polish
```

---

## Zod Schemas (frontend/lib/types.ts)

Representative schemas — full set mirrors the Pydantic models above.

```typescript
// Category classifications
export const CategoryClassificationItemSchema = z.object({
  category_id: z.number(),
  category_name: z.string(),
  classification: z.enum(["essential", "discretionary"]),
  is_user_override: z.boolean(),
});
export type CategoryClassificationItem = z.infer<typeof CategoryClassificationItemSchema>;

// Monthly analysis
export const BudgetCategoryMonthlyItemSchema = z.object({
  category_id: z.number().nullable(),
  category_name: z.string(),
  classification: z.enum(["essential", "discretionary"]),
  total_pln: z.number(),
  pct_of_total: z.number(),
  prev_month_pln: z.number(),
  change_pct: z.number(),
});
export const BudgetMonthlyResponseSchema = z.object({
  year: z.number(),
  month: z.number(),
  total_expenses_pln: z.number(),
  total_income_pln: z.number(),
  surplus_pln: z.number(),
  categories: z.array(BudgetCategoryMonthlyItemSchema),
  prev_month_total_pln: z.number(),
  month_over_month_change_pct: z.number(),
});

// Affordability
export const AffordabilityCheckResponseSchema = z.object({
  verdict: z.enum(["green", "yellow", "red"]),
  amount_pln: z.number(),
  available_this_month_pln: z.number(),
  upcoming_obligations_30d_pln: z.number(),
  active_goal_allocations_pln: z.number(),
  freely_available_pln: z.number(),
  financial_focus_label: z.string().nullable(),
  narrative: z.string(),
});

// Simulation
export const SimulationMonthlyPointSchema = z.object({
  month: z.string(),
  baseline_surplus_pln: z.number(),
  simulated_surplus_pln: z.number(),
});
export const BudgetSimulationDetailSchema = z.object({
  id: z.number(),
  name: z.string(),
  expense_name: z.string(),
  expense_amount_pln: z.number(),
  expense_type: z.enum(["one_time", "recurring"]),
  expense_start_date: z.string(),
  status: z.enum(["pending", "processing", "done", "failed"]),
  result: z.object({
    projection: z.array(SimulationMonthlyPointSchema),
    goal_impacts: z.array(z.object({
      goal_id: z.number(),
      goal_name: z.string(),
      baseline_completion_date: z.string().nullable(),
      simulated_completion_date: z.string().nullable(),
      delay_months: z.number(),
    })),
    ai_summary: z.string(),
    ai_implications: z.string(),
    ai_suggestions: z.array(z.object({
      description: z.string(),
      monthly_saving_pln: z.number(),
      months_required: z.number(),
    })),
  }).nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});

// AI Recommendations
export const AIRecommendationsResponseSchema = z.object({
  insights: z.array(z.object({
    title: z.string(),
    body: z.string(),
    amount_pln: z.number().nullable(),
    insight_type: z.enum(["saving_opportunity", "goal_advice", "warning", "general"]),
  })),
  generated_at: z.string().nullable(),
  data_through_date: z.string().nullable(),
  months_of_data: z.number(),
  has_sufficient_data: z.boolean(),
});
```

---

## Entity Relationship Summary

```
categories (existing)
  └─ budget_category_classifications  (1:1, optional — seeded on first access)

budget_financial_focus (1 row max active)

budget_financial_goals (many per user)
  └─ referenced by: budget_simulations.result_json → goal_impacts[].goal_id

budget_simulations
  └─ result_json: SimulationResultPayload (denormalized JSONB — no FK needed)

budget_ai_recommendations
  └─ recommendations_json: list[AIInsightItem] (denormalized JSONB)
```

No cross-feature foreign keys are introduced. All budget entities are self-contained.
