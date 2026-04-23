# Tasks: Budget Analysis & Insights

**Input**: Design documents from `/specs/001-budget-analysis/`  
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅ · quickstart.md ✅

**Tests**: Not explicitly requested in spec — no test tasks generated. Test scenarios in `quickstart.md`.

**Organization**: Tasks grouped by user story to enable independent delivery of each increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story ([US1]–[US6]) the task belongs to
- All file paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the 5 DB migrations and add the skeleton entry points that all subsequent phases depend on.

- [X] T001 Create migration `backend/migrations/20260313_01_budget-category-classifications.sql` — DDL for `budget_category_classifications` table (see data-model.md)
- [X] T002 Create migration `backend/migrations/20260313_02_budget-financial-focus.sql` — DDL for `budget_financial_focus` table (depends: `20260313_01_budget-category-classifications`)
- [X] T003 Create migration `backend/migrations/20260313_03_budget-financial-goals.sql` — DDL for `budget_financial_goals` table (depends: `20260313_02_budget-financial-focus`)
- [X] T004 Create migration `backend/migrations/20260313_04_budget-simulations.sql` — DDL for `budget_simulations` table (depends: `20260313_03_budget-financial-goals`)
- [X] T005 Create migration `backend/migrations/20260313_05_budget-ai-recommendations.sql` — DDL for `budget_ai_recommendations` table (depends: `20260313_04_budget-simulations`)
- [X] T006 Apply all 5 new migrations via `cd backend && yoyo apply` — verify tables exist in DB
- [X] T007 Add `# --- Budget Analysis ---` comment group to `backend/src/main.py` (empty section, no routes yet — establishes grouping position)
- [X] T008 Add `NavLink` for `/budget` route to the sidebar in `frontend/app/layout.tsx` (label: "Budżet")

**Checkpoint**: DB schema is in place. Backend skeleton ready. Sidebar has Budget entry.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared Pydantic models, Zod schemas, and API client functions that all user story phases need. Must be complete before any story implementation begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T009 Add all `# --- Budget Analysis ---` Pydantic models to `backend/src/data.py`: `CategoryClassificationItem`, `UpdateCategoryClassificationRequest`, `FinancialFocusResponse`, `SetFinancialFocusRequest`, `BudgetCategoryMonthlyItem`, `BudgetMonthlyResponse`, `RecurringExpenseItem`, `CyclicalAlertItem`, `AffordabilityCheckRequest`, `AffordabilityCheckResponse` (see data-model.md)
- [X] T010 Add remaining Pydantic models to `backend/src/data.py`: `FinancialGoalListItem`, `CreateFinancialGoalRequest`, `UpdateFinancialGoalRequest`, `MonthlySurplusResponse`, `CreateBudgetSimulationRequest`, `SimulationMonthlyPoint`, `SimulationGoalImpact`, `SimulationSuggestion`, `SimulationResultPayload`, `BudgetSimulationListItem`, `BudgetSimulationDetail`, `AIInsightItem`, `AIRecommendationsResponse`, `EmergencyAdvisorRequest`, `EmergencyReductionOption`, `EmergencyGoalImpact`, `EmergencyAdvisorResponse` (see data-model.md)
- [X] T011 [P] Add all budget Zod schemas to `frontend/lib/types.ts`: `CategoryClassificationItemSchema`, `BudgetCategoryMonthlyItemSchema`, `BudgetMonthlyResponseSchema`, `RecurringExpenseItemSchema`, `CyclicalAlertItemSchema`, `AffordabilityCheckResponseSchema` and inferred TS types (see data-model.md)
- [X] T012 [P] Add remaining budget Zod schemas to `frontend/lib/types.ts`: `FinancialGoalListItemSchema`, `MonthlySurplusResponseSchema`, `SimulationMonthlyPointSchema`, `BudgetSimulationListItemSchema`, `BudgetSimulationDetailSchema`, `AIRecommendationsResponseSchema`, `EmergencyAdvisorResponseSchema` and inferred TS types
- [X] T013 [P] Add budget API client functions to `frontend/lib/api.ts`: `getBudgetMonthly`, `getBudgetCategoryClassifications`, `updateBudgetCategoryClassification`, `getFinancialFocus`, `setFinancialFocus` — each calling `apiFetch` with the matching Zod schema
- [X] T014 [P] Add remaining API client functions to `frontend/lib/api.ts`: `getBudgetRecurringExpenses`, `getBudgetCyclicalAlerts`, `checkAffordability`, `getBudgetGoals`, `getBudgetSurplus`, `createGoal`, `updateGoal`, `deleteGoal`, `getBudgetSimulations`, `getBudgetSimulation`, `createBudgetSimulation`, `deleteBudgetSimulation`, `getAIRecommendations`, `refreshAIRecommendations`, `getEmergencyAdvice`

**Checkpoint**: All shared type definitions and client functions ready. Backend models declared. Story phases can now proceed.

---

## Phase 3: User Story 1 — Monthly Spending Overview (Priority: P1) 🎯 MVP

**Goal**: Show monthly per-category spending with MoM comparison, trend line chart, and category classification management. User can select any month and see totals, percentages, and changes vs. prior month.

**Independent Test**: Navigate to `/budget`, select a month with transaction data → see per-category breakdown with percentages and MoM change indicators. Verify zero-crash on months with no data.

### Backend — US1

- [X] T015 [US1] Create `backend/src/repositories/budget_analysis.py` — implement `BudgetAnalysisRepository.__init__(db_context)` with connection assignment; add `get_monthly_category_breakdown(year, month)` method: SQL UNION of `bank_transactions` + `cash_transactions` grouped by `category_id`, returning amounts for the target month AND the prior month in a single query, joined with `budget_category_classifications` for `classification` field; return `list[dict]` raw rows
- [X] T016 [US1] Add `get_category_classification_seed(all_category_ids)` and `get_all_classifications()` methods to `backend/src/repositories/budget_analysis.py` — `get_all_classifications()` returns all rows from `budget_category_classifications`; `get_category_classification_seed` returns existing classifications plus auto-detected ones for missing categories using the keyword heuristic from `research.md`; add `upsert_classification(category_id, classification, is_user_override)` write method with `ON CONFLICT DO UPDATE`
- [X] T017 [US1] Create `backend/src/services/budget_analysis.py` — implement `BudgetAnalysisService.__init__(budget_analysis_repo, categories_repo)`; add `get_monthly_breakdown(year, month) -> BudgetMonthlyResponse`: calls repo, computes `pct_of_total`, `change_pct`, `month_over_month_change_pct`, income/expense totals from the unified transaction union; add `seed_and_get_classifications() -> list[CategoryClassificationItem]` which seeds missing categories on first call then returns all
- [X] T018 [US1] Add `update_category_classification(category_id, classification) -> CategoryClassificationItem` to `backend/src/services/budget_analysis.py`; raises `ValueError` if category not found (→ 404 in handler)
- [X] T019 [US1] Add `get_financial_focus()` and `set_financial_focus(label, description)` methods to `backend/src/repositories/budget_analysis.py` — `get_financial_focus` returns the active row or `None`; `set_financial_focus` deactivates all existing rows then inserts a new active one (in a single transaction)
- [X] T020 [US1] Add `get_financial_focus() -> FinancialFocusResponse` and `set_financial_focus(req) -> FinancialFocusResponse` methods to `backend/src/services/budget_analysis.py`
- [X] T021 [US1] Wire `BudgetAnalysisRepository` and `BudgetAnalysisService` into `backend/src/app.py`: add imports, instantiate repo in `__init__`, instantiate service (inject repo + categories_repo), expose `get_monthly_breakdown`, `seed_and_get_classifications`, `update_category_classification`, `get_financial_focus`, `set_financial_focus` as App methods; add `budget_analysis_repository.dispose()` and `budget_analysis_service.dispose()` in `dispose()`
- [X] T022 [US1] Add routes to `backend/src/main.py` under `# --- Budget Analysis ---`: `GET /budget/analysis/monthly` → `BudgetMonthlyResponse`; `GET /budget/category-classifications` → `list[CategoryClassificationItem]`; `PUT /budget/category-classifications/{category_id}` → `CategoryClassificationItem`; `GET /budget/financial-focus` → `FinancialFocusResponse`; `PUT /budget/financial-focus` → `FinancialFocusResponse`; each using the App lifecycle pattern with try/except/finally

### Frontend — US1

- [X] T023 [P] [US1] Create `frontend/app/api/budget/analysis/monthly/route.ts` — `GET` handler calling `proxyGet(req)` (forwards `year` + `month` searchParams)
- [X] T024 [P] [US1] Create `frontend/app/api/budget/category-classifications/route.ts` — `GET` handler calling `proxyGet(req)`; create `frontend/app/api/budget/category-classifications/[id]/route.ts` — `PUT` handler calling `proxyPut(_, { pathSuffix: params.id })`
- [X] T025 [P] [US1] Create `frontend/app/api/budget/financial-focus/route.ts` — `GET` handler calling `proxyGet(req)`; `PUT` handler calling `proxyPut(req)`
- [X] T026 [P] [US1] Create `frontend/components/budget/MonthlyBreakdownChart.tsx` — recharts `BarChart` showing spending by category (essential in blue, discretionary in orange); shows PLN amounts + MoM change badge (green/red arrow); props: `categories: BudgetCategoryMonthlyItem[]`; use design tokens (`text-accent`, `clsx`); Polish labels
- [X] T027 [P] [US1] Create `frontend/components/budget/TrendLineChart.tsx` — recharts `LineChart` showing multi-month income vs expenses trend; accepts `months: MonthlySummary[]` (reuse existing type); Polish axis labels and tooltip; responsive container
- [X] T028 [US1] Create `frontend/app/budget/page.tsx` — `"use client"` page; `useQuery` for `getBudgetMonthly` (with year/month state from `useState`, defaulting to current month); `useQuery` for `getBudgetCyclicalAlerts` (for alert banner); renders `PageHeader` (title: "Analiza budżetu"), month selector (`DateInput` or prev/next nav using `PrevNextNav`), `MonthlyBreakdownChart`, `TrendLineChart`; loading and empty states in Polish; financial focus label displayed as `SectionLabel`

**Checkpoint**: `/budget` page shows monthly category breakdown, MoM trend, and financial focus. US1 fully testable.

---

## Phase 4: User Story 2 — Recurring & Cyclical Expense Tracker (Priority: P2)

**Goal**: Auto-detect recurring monthly bills and annual cyclical expenses (insurance, etc.). Show upcoming cyclical alerts with a 90-day warning banner.

**Independent Test**: Open `/budget` → see a "Cykliczne wydatki" section listing recurring expenses with next expected dates. Verify the 90-day alert banner appears when a cyclical expense is within 90 days.

### Backend — US2

- [X] T029 [US2] Add `get_recurring_expenses() -> list[RecurringExpenseItem]` to `backend/src/repositories/budget_analysis.py` — SQL query groups transactions by `vendor_id` (falling back to `description` where `vendor_id IS NULL`), computes occurrence count, median interval, and amount stats; filters to monthly pattern (interval 25–35 days, ≥ 3 occurrences) and annual pattern (interval 300–400 days, ≥ 2 occurrences different years); returns raw rows with `next_expected_date` calculated as `last_occurrence + median_interval`
- [X] T030 [US2] Add `get_cyclical_alerts(days_ahead=90) -> list[CyclicalAlertItem]` to `backend/src/repositories/budget_analysis.py` — filters recurring expenses of type `annual` where `next_expected_date` is within `days_ahead` days; orders by `days_until` ascending
- [X] T031 [US2] Add `get_recurring_expenses()` and `get_cyclical_alerts()` methods to `backend/src/services/budget_analysis.py` — delegate to repo, return typed Pydantic objects
- [X] T032 [US2] Add App methods `get_recurring_expenses()` and `get_cyclical_alerts()` to `backend/src/app.py`
- [X] T033 [US2] Add routes to `backend/src/main.py`: `GET /budget/analysis/recurring-expenses` → `list[RecurringExpenseItem]`; `GET /budget/analysis/cyclical-alerts` → `list[CyclicalAlertItem]`

### Frontend — US2

- [X] T034 [P] [US2] Create `frontend/app/api/budget/analysis/recurring-expenses/route.ts` — `GET` calling `proxyGet(req)`; create `frontend/app/api/budget/analysis/cyclical-alerts/route.ts` — `GET` calling `proxyGet(req)`
- [X] T035 [P] [US2] Create `frontend/components/budget/RecurringExpensesList.tsx` — shows list of recurring expenses in a `Card`; each item shows vendor name, category, frequency badge (`CountBadge`), next expected date, average amount (`Amount`); empty state: "Brak wykrytych cyklicznych wydatków. Dodaj więcej transakcji."
- [X] T036 [P] [US2] Create `frontend/components/budget/CyclicalAlertBanner.tsx` — warning banner (amber) listing cyclical expenses within 90 days; shows vendor, days remaining, expected amount range; hidden when `alerts.length === 0`
- [X] T037 [US2] Update `frontend/app/budget/page.tsx` — add `useQuery` for `getBudgetRecurringExpenses` and `getBudgetCyclicalAlerts`; render `CyclicalAlertBanner` above the fold when alerts exist; add `RecurringExpensesList` section below the breakdown chart; Polish section headers using `SectionLabel`

**Checkpoint**: `/budget` page now shows recurring expense tracker and cyclical alerts. US2 independently testable.

---

## Phase 5: User Story 3 — "Can I Afford It?" Affordability Check (Priority: P3)

**Goal**: Inline affordability tool on the dashboard. User enters a purchase amount and instantly sees a GREEN/YELLOW/RED verdict with explanation referencing upcoming obligations and active goals.

**Independent Test**: Enter 500 PLN in the affordability checker → verify verdict is GREEN/YELLOW/RED based on current month data; verify Polish narrative references specific PLN amounts.

### Backend — US3

- [X] T038 [US3] Add `get_current_month_income_and_expenses() -> dict` to `backend/src/repositories/budget_analysis.py` — returns `income_pln`, `expenses_pln` for the current calendar month from the UNION of bank + cash transactions; also returns `upcoming_recurring_sum_30d` (sum of recurring monthly expenses expected in next 30 days based on next_expected_date)
- [X] T039 [US3] Add `check_affordability(amount_pln, financial_focus_label, goal_allocations_pln) -> AffordabilityCheckResponse` to `backend/src/services/budget_analysis.py` — applies the 3-factor formula from `research.md` (available_this_month = income − expenses; safely_reserved = upcoming_30d + goal_allocations; freely_available = available − reserved); computes `verdict` (green/yellow/red); generates Polish `narrative` string inline (no LLM needed for affordability check)
- [X] T040 [US3] Add `check_affordability(amount_pln) -> AffordabilityCheckResponse` App method to `backend/src/app.py` — orchestrates: calls `get_current_month_income_and_expenses`, calls `get_financial_focus` for label, calls `get_active_goal_allocations_total` from goals repo (or 0 if goals not yet implemented), passes all to service
- [X] T041 [US3] Add route to `backend/src/main.py`: `GET /budget/analysis/affordability?amount_pln=` → `AffordabilityCheckResponse`; validate `amount_pln > 0`

### Frontend — US3

- [X] T042 [P] [US3] Create `frontend/app/api/budget/analysis/affordability/route.ts` — `GET` calling `proxyGet(req)` (forwards `amount_pln` searchParam)
- [X] T043 [P] [US3] Create `frontend/components/budget/AffordabilityChecker.tsx` — controlled `Input` for amount (PLN); `useMutation` calling `checkAffordability`; result card showing verdict colored banner (green/amber/red with matching Tailwind bg token), Polish narrative, and breakdown of `available_this_month`, `upcoming_30d`, `goal_allocations`, `freely_available` using `Amount` component; financial focus label shown as context
- [X] T044 [US3] Update `frontend/app/budget/page.tsx` — add `AffordabilityChecker` as a collapsible/always-visible card section; `SectionLabel` header: "Czy mnie stać?"; position below cyclical alerts

**Checkpoint**: User can enter any amount and get an instant strategic affordability verdict. US3 independently testable.

---

## Phase 6: User Story 5 — Financial Goals & Surplus (Priority: P5)

**Goal**: Create and manage financial goals. View monthly surplus, allocate it across goals, track progress, and see projected completion dates.

**Note on ordering**: Placed before US4 (Simulation) so that simulation results can display meaningful goal impacts when US4 is implemented.

**Independent Test**: Navigate to `/budget/goals` → create a goal with name + target + monthly allocation → verify progress bar appears and months-to-completion is calculated correctly.

### Backend — US5

- [X] T045 [US5] Create `backend/src/repositories/budget_goals.py` — `BudgetGoalsRepository.__init__(db_context)`; implement: `get_all_goals() -> list[dict]`, `get_goal(id) -> dict | None`, `create_goal(name, target_amount, target_date, priority_rank, monthly_allocation) -> dict`, `update_goal(id, **fields) -> dict | None` (builds dynamic SET clause), `soft_delete_goal(id) -> bool`, `get_active_goal_allocations_total() -> float` (SUM of `monthly_allocation_amount` for active goals); `dispose() = pass`; all write methods with `conn.commit()` / `rollback()`
- [X] T046 [US5] Create `backend/src/services/budget_goals.py` — `BudgetGoalsService.__init__(budget_goals_repo, budget_analysis_repo)`; implement `get_monthly_surplus() -> MonthlySurplusResponse` (3-month rolling average from `budget_analysis_repo` + current month actuals); implement `get_goals() -> list[FinancialGoalListItem]` (enriches raw rows with computed `progress_pct`, `months_to_completion`, `projected_completion_date`); implement `create_goal`, `update_goal`, `delete_goal`; `dispose() = pass`
- [X] T047 [US5] Wire `BudgetGoalsRepository` and `BudgetGoalsService` into `backend/src/app.py` — add imports, instantiate repo and service; expose `get_monthly_surplus`, `get_goals`, `create_goal`, `update_goal`, `delete_goal` as App methods; add `dispose()` calls
- [X] T048 [US5] Add routes to `backend/src/main.py` under `# --- Budget Analysis ---`: `GET /budget/goals/surplus` → `MonthlySurplusResponse`; `GET /budget/goals` → `list[FinancialGoalListItem]`; `POST /budget/goals` → `FinancialGoalListItem` (status 201); `PUT /budget/goals/{id}` → `FinancialGoalListItem`; `DELETE /budget/goals/{id}` → 204; validate `target_amount_pln > 0`; 404 when goal not found
- [X] T049 [US5] Create `backend/src/tasks/advance_goal_progress.py` — Celery beat task `advance_goal_progress`: instantiates `App()`, calls `budget_goals_repository.advance_monthly_progress_for_all_active_goals()` (adds `monthly_allocation_amount` to `accumulated_progress` for each active goal), disposes, pushes no Pusher event (silent DB update); add `advance_monthly_progress_for_all_active_goals()` method to `BudgetGoalsRepository`

### Frontend — US5

- [X] T050 [P] [US5] Create `frontend/app/api/budget/goals/route.ts` — `GET` calling `proxyGet(req)`, `POST` calling `proxyPost(req)`; create `frontend/app/api/budget/goals/[id]/route.ts` — `PUT` calling `proxyPut`, `DELETE` calling `proxyDelete`; create `frontend/app/api/budget/goals/surplus/route.ts` — `GET` calling `proxyGet(req)`
- [X] T051 [P] [US5] Create `frontend/components/budget/GoalCard.tsx` — displays single goal: name, progress bar (`accumulated_progress / target_amount` %), PLN amounts via `Amount`, projected completion date, monthly allocation; action menu via `ThreeDotsMenu` (edit, delete with `ConfirmDeleteModal`); `useMutation` for delete calling `deleteGoal`; Polish labels
- [X] T052 [P] [US5] Create `frontend/components/budget/GoalForm.tsx` — controlled form (`useState`) for creating/editing a goal: `Input` for name, amount (PLN), monthly allocation; `DateInput` for target date (optional); priority rank number `Input`; submit via `useMutation` calling `createGoal` or `updateGoal`; `onSuccess` calls `queryClient.invalidateQueries(["budget-goals"])`; Polish labels and validation messages
- [X] T053 [US5] Create `frontend/app/budget/goals/page.tsx` — `"use client"`; `useQuery` for `getBudgetGoals` and `getBudgetSurplus`; renders `PageHeader` ("Cele finansowe"), surplus summary card (avg monthly surplus, total allocations, unallocated surplus using `Amount`), list of `GoalCard` components, `Button` to open `Modal` containing `GoalForm`; loading state; empty state: "Brak aktywnych celów. Dodaj swój pierwszy cel!"

**Checkpoint**: `/budget/goals` page fully functional. Goals CRUD, surplus display, progress tracking all work. US5 independently testable.

---

## Phase 7: User Story 4 — Budget Simulation (Priority: P4)

**Goal**: What-if tool — user enters a hypothetical expense (one-time or recurring), system projects month-by-month surplus + goal timeline impact, AI generates narrative and adjustment suggestions.

**Independent Test**: Create a simulation for a 20,000 PLN one-time expense → Celery task completes → result shows 12-month projection chart (baseline vs. simulated), goal impact table, AI narrative, and at least 2 suggestions.

### Backend — US4

- [X] T054 [US4] Create `backend/src/repositories/budget_simulations.py` — `BudgetSimulationsRepository.__init__(db_context)`; implement: `create_simulation(name, expense_name, amount, type, start_date) -> dict` (inserts with `status='pending'`, returns row); `get_simulation(id) -> dict | None`; `get_all_simulations() -> list[dict]`; `update_simulation_status(id, status, result_json=None, error=None)`; `delete_simulation(id) -> bool`; all writes with `commit()`/`rollback()`
- [X] T055 [US4] Create `backend/src/services/budget_simulation.py` — `BudgetSimulationService.__init__(budget_analysis_repo, budget_goals_repo, openai_client)`; implement `run_projection(simulation_row) -> SimulationResultPayload`: (1) compute `baseline_monthly_income` and `baseline_monthly_expenses` (3-month rolling avg via budget_analysis_repo); (2) iterate over projection horizon (12 months for one_time, 24 for recurring), compute `baseline_surplus_pln` and `simulated_surplus_pln` per month; (3) for each active goal, compute baseline vs. simulated `months_to_completion` and `delay_months`; (4) call `_generate_narrative()` with OpenAI function-call pattern (same as `backend/src/services/ocr.py`); returns `SimulationResultPayload`
- [X] T056 [US4] Add `_generate_narrative(projection_data, goal_impacts, expense_def) -> tuple[str, str, list[SimulationSuggestion]]` to `backend/src/services/budget_simulation.py` — builds OpenAI prompt with structured projection data; uses `model_json_schema()` on a `SimulationNarrative` Pydantic model (defined in `data.py`); calls `gpt-4o-mini`; parses tool call result into `ai_summary`, `ai_implications`, `ai_suggestions`; handles `None` tool call with a fallback message
- [X] T057 [US4] Add `SimulationNarrative` Pydantic model to `backend/src/data.py` — used as OpenAI function schema; fields: `summary: str`, `implications: str`, `suggestions: list[SimulationSuggestion]`
- [X] T058 [US4] Create `backend/src/tasks/run_budget_simulation.py` — Celery task `run_budget_simulation(simulation_id: int)`: instantiates `App()`; sets `status='processing'` via `budget_simulations_repository.update_simulation_status`; calls `budget_simulation_service.run_projection(simulation_row)`; stores result via `update_simulation_status(id, 'done', result_json=result.model_dump())`; pushes Pusher event `budget.simulation.done` on `budget-channel`; on any exception: sets `status='failed'`, pushes `budget.simulation.failed`; always calls `my_app.dispose()`
- [X] T059 [US4] Wire `BudgetSimulationsRepository` and `BudgetSimulationService` into `backend/src/app.py` — add imports, instantiate (inject `openai` client from existing imports or instantiate with `os.environ["OPENAI_API_KEY"]`); expose `create_simulation`, `get_simulation`, `get_all_simulations`, `delete_simulation` as App methods; add `dispose()` calls
- [X] T060 [US4] Add routes to `backend/src/main.py`: `POST /budget/simulations` → 202 `TaskResponse`; `GET /budget/simulations` → `list[BudgetSimulationListItem]`; `GET /budget/simulations/{id}` → `BudgetSimulationDetail`; `DELETE /budget/simulations/{id}` → 204; POST handler enqueues `run_budget_simulation.delay(simulation.id)` and returns `TaskResponse(task_id=str(task.id), simulation_id=simulation.id)` — add `simulation_id: int` field to `TaskResponse` in `data.py` (or create `SimulationTaskResponse`)

### Frontend — US4

- [X] T061 [P] [US4] Create `frontend/app/api/budget/simulations/route.ts` — `GET` calling `proxyGet(req)`, `POST` calling `proxyPost(req)`; create `frontend/app/api/budget/simulations/[id]/route.ts` — `GET` calling `proxyGet`, `DELETE` calling `proxyDelete`
- [X] T062 [P] [US4] Create `frontend/components/budget/SimulationForm.tsx` — controlled form: `Input` for simulation name and expense name; amount `Input` (PLN); expense type radio/toggle (Jednorazowy / Cykliczny); `DateInput` for start date; submit via `useMutation` calling `createBudgetSimulation`; `onSuccess` navigates to `/budget/simulations/{id}`; Polish labels and loading state
- [X] T063 [P] [US4] Create `frontend/components/budget/SimulationResultView.tsx` — shows `status` badge; when `status === 'done'`: recharts `ComposedChart` with two `Line` series (baseline surplus vs. simulated surplus) over projection months; goal impact table (`Card` with rows: goal name, baseline completion, simulated completion, delay in months highlighted in red if > 0); AI narrative sections (summary, implications, suggestions list); when `status === 'pending' | 'processing'`: Polish loading message "Obliczamy symulację..."; when `status === 'failed'`: error card
- [X] T064 [US4] Create `frontend/app/budget/simulations/page.tsx` — `"use client"`; `useQuery` for `getBudgetSimulations`; renders `PageHeader` ("Symulacje budżetu"), `Button` to open `Modal` with `SimulationForm`, list of simulation cards (name, expense name, amount, status badge, created date, link to detail); empty state: "Brak symulacji. Utwórz pierwszą, aby zobaczyć wpływ dużego wydatku na Twój budżet."
- [X] T065 [US4] Create `frontend/app/budget/simulations/[id]/page.tsx` — `"use client"`; `useQuery` for `getBudgetSimulation(id)` with `refetchInterval: (data) => data?.status === 'done' || data?.status === 'failed' ? false : 3000` (polls while processing); subscribes to `budget-channel` Pusher event `budget.simulation.done` in `useEffect` → calls `queryClient.invalidateQueries(["budget-simulation", id])` and stops polling; renders `PageHeader` with simulation name, `SimulationResultView`; Pusher cleanup in effect teardown

**Checkpoint**: `/budget/simulations` and `/budget/simulations/[id]` work end-to-end. Simulation Celery task runs, results appear via Pusher. US4 independently testable.

---

## Phase 8: User Story 6 — Emergency Expense Management (Priority: P6)

**Goal**: Given an unexpected expense amount, show which discretionary spending categories to cut and how that affects active goals, with recovery timeline.

**Independent Test**: Enter 4,000 PLN emergency amount → verify system lists discretionary categories with cut amounts and months-to-cover, and shows goal impact descriptions.

### Backend — US6

- [X] T066 [US6] Add `get_discretionary_category_averages() -> list[dict]` to `backend/src/repositories/budget_analysis.py` — returns average monthly spending per discretionary category (join `budget_category_classifications` where `classification='discretionary'` with last 3 months of transactions); includes `category_name`, `avg_monthly_spend_pln`
- [X] T067 [US6] Add `get_emergency_advice(amount_pln) -> EmergencyAdvisorResponse` to `backend/src/services/budget_analysis.py` — builds `EmergencyReductionOption` list from discretionary averages (each showing `suggested_cut_pln = avg_monthly_spend`, `months_to_cover = amount / avg`); computes `total_cuttable_pln`; builds `EmergencyGoalImpact` list from active goals (each showing how pausing the goal allocation helps); computes `recovery_months` and `fully_coverable_by_cuts` flag; generates Polish `narrative` inline
- [X] T068 [US6] Add `get_emergency_advice(amount_pln)` App method to `backend/src/app.py`
- [X] T069 [US6] Add route to `backend/src/main.py`: `POST /budget/emergency-advisor` → `EmergencyAdvisorResponse`; body: `EmergencyAdvisorRequest`; validate `amount_pln > 0`

### Frontend — US6

- [X] T070 [P] [US6] Create `frontend/app/api/budget/emergency-advisor/route.ts` — `POST` calling `proxyPost(req)`
- [X] T071 [P] [US6] Create `frontend/components/budget/EmergencyAdvisorPanel.tsx` — controlled `Input` for emergency amount and optional description; `useMutation` calling `getEmergencyAdvice`; result shows: fully-coverable badge (green/red), list of `EmergencyReductionOption` cards (category name, avg spending, suggested cut, months), goal impact section, recovery timeline, Polish narrative; empty initial state prompts "Podaj kwotę nieoczekiwanego wydatku"
- [X] T072 [US6] Update `frontend/app/budget/page.tsx` — add `EmergencyAdvisorPanel` as a dedicated card section; `SectionLabel`: "Nieoczekiwany wydatek"; positioned below AffordabilityChecker

**Checkpoint**: Emergency advisor fully functional. US6 independently testable.

---

## Phase 9: User Story 4b — AI Background Recommendations

**Goal**: Background-generated AI insights based on 3+ months of data. Displayed on a dedicated `/budget/ai-insights` page with "last updated" timestamp and manual refresh.

**Independent Test**: With 3+ months of transaction data and running Celery worker → trigger `POST /budget/ai-recommendations/refresh` → verify `GET /budget/ai-recommendations` returns `has_sufficient_data: true` and at least 3 insights each referencing PLN amounts.

### Backend — AI Recs

- [X] T073 Add `get_current_recommendations() -> dict | None` and `save_recommendations(insights_json, data_through_date, months_of_data)` to `backend/src/repositories/budget_simulations.py` — `get_current` selects the row where `is_current = true`; `save_recommendations` deactivates all existing (sets `is_current = false`) then inserts new row
- [X] T074 Add `_count_months_of_data() -> int` and `_build_context_summary() -> dict` helper methods to `backend/src/services/budget_simulation.py` — `count_months` counts distinct year-months with at least one transaction; `build_context_summary` collects last 3 months of category spending, monthly surplus trend, active goals list, and financial focus label (all as PLN amounts)
- [X] T075 Add `generate_ai_recommendations() -> AIRecommendationsResponse` to `backend/src/services/budget_simulation.py` — checks months_of_data ≥ 3 (returns `has_sufficient_data=false` otherwise); calls OpenAI with `AIRecommendationsPayload` function schema (add to `data.py`); parses result; calls `budget_simulations_repository.save_recommendations()`
- [X] T076 Add `AIRecommendationsPayload` Pydantic model to `backend/src/data.py` — OpenAI function schema; fields: `insights: list[AIInsightItem]`
- [X] T077 Create `backend/src/tasks/refresh_ai_recommendations.py` — Celery task `refresh_ai_recommendations()`: instantiates `App()`; calls `budget_simulation_service.generate_ai_recommendations()`; on success pushes Pusher event `budget.recommendations.done` on `budget-channel` with `{"generated_at": ISO timestamp}`; on exception logs and re-raises; always `my_app.dispose()`
- [X] T078 Add routes to `backend/src/main.py`: `GET /budget/ai-recommendations` → `AIRecommendationsResponse`; `POST /budget/ai-recommendations/refresh` → `TaskResponse` (202, enqueues `refresh_ai_recommendations.delay()`); add `get_ai_recommendations()` App method reading from DB via `budget_simulations_repository.get_current_recommendations()`

### Frontend — AI Recs

- [X] T079 [P] Create `frontend/app/api/budget/ai-recommendations/route.ts` — `GET` calling `proxyGet(req)`; create `frontend/app/api/budget/ai-recommendations/refresh/route.ts` — `POST` calling `proxyPost(req)`
- [X] T080 [P] Create `frontend/components/budget/AIRecommendationsList.tsx` — shows list of `AIInsightItem` cards: title (bold), body (paragraph), `amount_pln` shown via `Amount` when present, `insight_type` as `StatusBadge`; `has_sufficient_data = false` shows an info card: "Zbieramy dane. Potrzebujemy co najmniej 3 miesięcy transakcji."; "last updated" timestamp shown as muted text; `Button` to trigger manual refresh (calls `refreshAIRecommendations`, on success `invalidateQueries(["budget-ai-recommendations"])`, subscribes to Pusher `budget.recommendations.done`)
- [X] T081 Create `frontend/app/budget/ai-insights/page.tsx` — `"use client"`; `useQuery` for `getAIRecommendations`; subscribes to `budget-channel` Pusher event `budget.recommendations.done` in `useEffect` → `invalidateQueries(["budget-ai-recommendations"])`; Pusher cleanup in teardown; renders `PageHeader` ("Rekomendacje AI"), `AIRecommendationsList`; loading state in Polish

**Checkpoint**: `/budget/ai-insights` shows background AI recommendations with last-updated time. Manual refresh works. Pusher updates on completion.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Sidebar navigation, TypeScript/lint validation, empty states, Pusher channel consistency.

- [X] T082 [P] Verify the `NavLink` for `/budget` added in T008 renders correctly in `frontend/app/layout.tsx` sidebar with the correct active state; also add sub-nav links for `/budget/goals`, `/budget/simulations`, `/budget/ai-insights` if sidebar supports nested navigation
- [X] T083 [P] Audit all new `frontend/components/budget/*.tsx` and `frontend/app/budget/**/*.tsx` files for missing loading states and empty states — all queries must handle `isLoading` and `!data` cases with Polish placeholder text
- [X] T084 [P] Run `cd frontend && npx tsc --noEmit` — fix any TypeScript errors introduced by new types/components (zero errors required before merge)
- [X] T085 [P] Run `cd frontend && npm run lint` — fix any ESLint errors in new files (zero errors required)
- [X] T086 [P] Run `cd frontend && npm run build` — fix any build errors; verify no bundle-size regression > 10% on `/budget` route chunk
- [X] T087 Walk through `quickstart.md` end-to-end on a real dev environment — verify all 7 manual steps produce expected output; record any discrepancies and fix them

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately; T001–T005 fully parallel
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS all user stories; T011–T014 parallel with each other
- **Phase 3 (US1)**: Depends on Phase 2; T023–T025 parallel with T015–T022 frontend work (different files)
- **Phase 4 (US2)**: Depends on Phase 2 and Phase 3 backend (uses `BudgetAnalysisRepository`)
- **Phase 5 (US3)**: Depends on Phase 2; T038–T040 can start in parallel with US2
- **Phase 6 (US5)**: Depends on Phase 2; fully independent of US2 and US3
- **Phase 7 (US4)**: Depends on Phase 2; benefits from US5 being done first (goals data for impact display), but independently testable
- **Phase 8 (US6)**: Depends on Phase 3 backend (uses `BudgetAnalysisRepository.get_discretionary_category_averages`) and Phase 6 backend (uses goals)
- **Phase 9 (AI Recs)**: Depends on Phase 7 infrastructure (reuses `BudgetSimulationService` and `budget_simulations` repository)
- **Phase 10 (Polish)**: Depends on all story phases being complete

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational — 🎯 MVP
- **US2 (P2)**: Shares `BudgetAnalysisRepository` with US1 — implement US1 backend first
- **US3 (P3)**: Independent — uses `BudgetAnalysisRepository` (US1 backend) + goals total (US5 repo)
- **US5 (P5)**: Independent — new `BudgetGoalsRepository`; implement before US4 for best experience
- **US4 (P4)**: Depends on `BudgetGoalsRepository` existing (for goal_impacts); independently testable without goals data
- **US6 (P6)**: Depends on `BudgetAnalysisRepository` (US1 backend) and `BudgetGoalsRepository` (US5 backend)
- **AI Recs**: Depends on `BudgetSimulationService` infrastructure from US4

### Parallel Opportunities Within Stories

All tasks marked `[P]` within the same phase can be dispatched simultaneously:
- T001–T005: 5 migration files — fully parallel
- T011–T014: types.ts + api.ts additions — parallel (different file sections)
- T023–T025 (US1 proxy routes) run in parallel with T015–T022 (US1 backend)
- T029–T032 backend tasks parallel with T034–T036 frontend tasks within US2
- T045–T046 can be drafted in parallel (repo + service in different files)

---

## Parallel Example: User Story 1

```
Simultaneously dispatch:
  Backend thread:
    T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022
  Frontend thread:
    T023, T024, T025 (proxy routes — all parallel)
    T026, T027 (chart components — parallel)
    T028 (page — depends on T026, T027, T023–T025)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete **Phase 1** (Setup — migrations, skeleton)
2. Complete **Phase 2** (Foundational — models, types, api.ts)
3. Complete **Phase 3** (US1 — monthly breakdown, categories, financial focus)
4. **STOP and VALIDATE**: Open `/budget`, select a month, confirm category breakdown renders with correct data
5. Demo / deploy MVP

### Incremental Delivery

| Milestone | Stories Delivered | Value |
|-----------|------------------|-------|
| MVP | US1 | Monthly spending clarity |
| M2 | US1 + US2 | Recurring bills tracked, cyclical alerts |
| M3 | M2 + US3 | "Can I afford it?" answers |
| M4 | M3 + US5 | Goals with progress tracking |
| M5 | M4 + US4 | Budget simulation with AI narrative |
| M6 | M5 + US6 | Emergency expense advisor |
| M7 | M6 + AI Recs | Background AI recommendations |

---

## Notes

- `[P]` = different files, no shared dependency on an incomplete task — safe to run concurrently
- `[US1]`–`[US6]` labels trace each task to its user story for PR scoping
- Every story's backend and frontend tasks can run in parallel streams after Foundational is done
- The `advance_goal_progress` Celery beat task (T049) requires a Celery beat schedule entry — add to `backend/src/celery_app.py` beat_schedule
- All new routes follow the App lifecycle: `my_app = App()` → `try` → `finally: my_app.dispose()`
- Polish strings only in all frontend components
- All `useMutation` handlers call `queryClient.invalidateQueries()` on success
