# Research: Budget Analysis & Insights

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13

---

## Decision 1: Recurring Expense Detection Algorithm

**Decision**: Heuristic pattern matching on vendor + amount range + date interval  
**Rationale**: The transaction volume is small (100–500/month per household). A lightweight SQL-based heuristic is sufficient, is deterministic, avoids ML dependencies, and can run inline within an API response. Full ML clustering would add complexity with no measurable benefit at this scale.

**Algorithm**:
1. Group expenses by `vendor_id` (or `description` when vendor is null).
2. For each vendor group, collect all expense transactions sorted by date.
3. Classify as **monthly recurring** if: ≥ 3 occurrences, median interval between occurrences is 25–35 days, standard deviation of amount is ≤ 20% of mean amount.
4. Classify as **annual cyclical** if: ≥ 2 occurrences across different years, median interval is 300–400 days.
5. Next expected date = last occurrence date + median interval.
6. Expected amount = mean amount ± 1 standard deviation (shown as a range).
7. Alert threshold for cyclical: 90 days before next expected date.

**Alternatives considered**:
- OpenAI classification of transactions (rejected: latency + cost for each analysis load; non-deterministic)
- Full time-series clustering with scikit-learn (rejected: unnecessary dependency; overkill for 100–500 tx/month)

---

## Decision 2: Affordability Check Logic

**Decision**: Three-factor point-in-time evaluation producing a structured verdict  
**Rationale**: The spec requires a verdict that goes beyond "do I have the money?" to "should I spend it now?" This requires combining balance, upcoming obligations, and active goal allocations.

**Algorithm**:
```
available_this_month = income_this_month - expenses_this_month_so_far
upcoming_30_days     = sum of recurring/cyclical expenses expected in next 30 days
goal_allocation      = sum of monthly allocations across all active goals
safety_buffer        = max(0, upcoming_30_days + goal_allocation)
freely_available     = available_this_month - safety_buffer

verdict:
  GREEN  if purchase_amount ≤ freely_available
  YELLOW if purchase_amount ≤ available_this_month but > freely_available
  RED    if purchase_amount > available_this_month
```

The response always includes:
- `verdict`: green | yellow | red
- `available_this_month`: PLN (current month surplus so far)
- `upcoming_obligations_30d`: PLN
- `active_goal_allocations`: PLN
- `freely_available`: PLN
- `financial_focus_label`: text (the current focus label, e.g. "Nadpłata kredytu")
- `narrative`: short Polish text explaining the verdict

**Alternatives considered**:
- Pure balance check (rejected: too simplistic, doesn't answer "should I")
- AI-generated affordability verdict (rejected: too slow and expensive for a near-real-time check; reserved for simulation)

---

## Decision 3: Budget Simulation — Projection Model

**Decision**: Deterministic projection math + OpenAI narrative generation in Celery  
**Rationale**: The projection math is deterministic and fast (iterate over months, subtract expense, recalculate goal progress). AI is used only for the human-readable narrative and suggestions — not for the numbers. This separation makes the output verifiable and keeps the mathematical core testable.

**Projection algorithm**:
```
baseline_monthly_income   = average income over last 3 complete months
baseline_monthly_expenses = average total expenses over last 3 complete months (excluding income)
baseline_surplus          = baseline_monthly_income - baseline_monthly_expenses

for each month in projection_horizon (12 for one-time, 24 for recurring):
  simulated_expenses = baseline_monthly_expenses
  if expense_type == 'one_time' and current_month == start_month:
    simulated_expenses += expense_amount
  elif expense_type == 'recurring' and current_month >= start_month:
    simulated_expenses += expense_amount

  baseline_surplus_month[m]  = baseline_surplus
  simulated_surplus_month[m] = baseline_monthly_income - simulated_expenses

  for each active goal:
    remaining = goal.target_amount - goal.accumulated_progress
    if simulated_surplus_month[m] >= goal.monthly_allocation:
      goal_progress[m] += goal.monthly_allocation
    else:
      goal_delayed = True
```

**Goal impact calculation**:
- Baseline months to completion = ceil(remaining / monthly_allocation)
- Simulated months to completion = recalculated with reduced surplus if allocation becomes impossible
- Delay = simulated_completion_date - baseline_completion_date

**OpenAI prompt** (structured, function-call pattern — same as OCR service):
- Input: projection data as JSON (monthly surpluses, goal impacts, expense definition)
- Output schema: `SimulationNarrative` Pydantic model with `summary`, `implications`, `suggestions: list[SimulationSuggestion]` (each: `description`, `monthly_saving_pln`, `months_required`)
- Model: `gpt-4o-mini` (cost-effective for structured narrative generation)

**Alternatives considered**:
- Fully AI-generated projection numbers (rejected: non-deterministic, untestable, costly)
- Synchronous simulation in HTTP response (rejected: violates constitution Principle III for long-running ops)

---

## Decision 4: Background AI Recommendations

**Decision**: Celery task, daily schedule or manual trigger; stored in `budget_ai_recommendations` table  
**Rationale**: Passive AI recommendations are generated from aggregated historical data. They do not need to be real-time. Storing the result avoids re-generating on every page load (latency + cost). A daily Celery beat schedule (or on-demand trigger) is the right pattern, matching the existing task infrastructure.

**Prompt approach**: Same OpenAI function-call pattern as OCR service. Input context includes:
- Last 3 months of category-level spending (with amounts)
- Monthly surplus trend
- Active goals
- Current financial focus

Output schema: `AIRecommendationsPayload` with `insights: list[AIInsight]` (each: `title`, `body`, `amount_pln: Optional[float]`, `insight_type: str`)

**Trigger logic**:
1. New data trigger: if new transactions were added since last generation AND total new transactions ≥ 10 → enqueue task
2. Daily scheduled task via Celery beat: check if recommendations are older than 24h → enqueue
3. Manual: `POST /budget/ai-recommendations/refresh` enqueues immediately

**Alternatives considered**:
- Live generation on page load (rejected: 2–5 second latency; cost per page view)
- Caching in Redis without DB storage (rejected: no history; can't show "last updated" timestamp reliably)

---

## Decision 5: Category Auto-Classification (Essential vs. Discretionary)

**Decision**: Keyword/pattern matching against category names → auto-populate `budget_category_classifications` on first access; user override stored as a separate flag  
**Rationale**: The categories are already in Polish and follow predictable naming conventions (e.g., "Jedzenie", "Restauracje", "Kredyty", "Subskrypcje"). A keyword map handles the common cases immediately with zero user effort, while the override mechanism gives full control.

**Keyword map (representative)**:
```python
ESSENTIAL_KEYWORDS = [
    "kredyt", "hipoteka", "czynsz", "najem", "prąd", "gaz", "woda",
    "internet", "telefon", "ubezpieczenie", "podatek", "zus", "transport",
    "paliwo", "lekarstwo", "leczenie", "szkoła", "przedszkole",
]
DISCRETIONARY_KEYWORDS = [
    "restauracja", "kawiarnia", "rozrywka", "hobby", "ubrania", "kosmetyki",
    "elektronika", "podróże", "wakacje", "sport", "gry", "streaming",
    "sklep z alkoholem", "prezenty",
]
# default for unmatched: 'discretionary'
```

First `GET /budget/category-classifications` seeds the table with auto-detected values for all existing categories.

**Alternatives considered**:
- OpenAI classification of category names (rejected: unnecessary for a known-Polish keyword set; non-deterministic)
- Manual-only classification (rejected: poor out-of-the-box experience; user must set up before feature is useful)

---

## Decision 6: Monthly Surplus Calculation

**Decision**: Average of last 3 complete months' income; average of last 3 complete months' expenses  
**Rationale**: A single month can be an outlier (holiday spending, one-off bonus). A 3-month rolling average provides a stable baseline for goal projections and affordability checks while being responsive enough to reflect genuine life changes within a quarter.

**Income identification**: Income transactions = `amount > 0` in bank/cash transactions. This matches the existing convention used in `UnifiedTransactionsRepository.get_analytics()`.

**Current-month surplus** (for affordability check): uses actual this-month data, not the rolling average, so the check is always current.

---

## Decision 7: Chart Library

**Decision**: recharts (already installed, confirmed in `frontend/AGENTS.md`)  
**Rationale**: Zero additional dependency. recharts is declarative, React-friendly, and well-supported. The existing codebase already lists it as a dependency.

**Chart types needed**:
- `BarChart` — monthly spending by category
- `LineChart` — multi-month surplus/expense trend
- `ComposedChart` — simulation baseline vs. simulated surplus side-by-side
- `PieChart` — monthly category share breakdown

**Alternatives considered**: Chart.js, Victory (both rejected — recharts already present)

---

## Decision 8: Pusher Channel Naming for Budget Tasks

**Decision**: `budget-channel` with events `budget.simulation.done`, `budget.simulation.failed`, `budget.recommendations.done`  
**Rationale**: Follows the existing naming pattern (`receipts-channel`, `import-channel`). Single channel for all budget async tasks keeps subscriptions simple on the frontend.

**Payload shapes**:
- `budget.simulation.done`: `{ "simulation_id": int, "status": "done" }`
- `budget.simulation.failed`: `{ "simulation_id": int, "error": str }`
- `budget.recommendations.done`: `{ "generated_at": ISO8601 }`
