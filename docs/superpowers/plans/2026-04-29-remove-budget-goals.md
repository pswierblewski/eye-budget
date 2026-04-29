# Remove Financial Goals (Cele finansowe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely remove the "Cele finansowe" (Financial Goals) sub-feature from the Budget tab — frontend pages/components, backend endpoints, service, repository, Celery task, and all related tests.

**Architecture:** Delete 5 standalone files, then surgically edit 10 files to remove goals-related code. The `BudgetSimulationService` will lose its `budget_goals_repo` dependency — `goal_impacts` will always be `[]`. `check_affordability` will pass `goal_allocations_pln=0.0`. `get_emergency_advice` will pass `active_goals=[]`.

**Tech Stack:** Next.js 14 / TypeScript (frontend), FastAPI / Python 3.11.7 / Celery (backend), pytest (tests)

---

## File Map

**Delete entirely:**
- `frontend/app/budget/goals/page.tsx`
- `frontend/components/budget/GoalCard.tsx`
- `frontend/components/budget/GoalForm.tsx`
- `backend/src/services/budget_goals.py`
- `backend/src/repositories/budget_goals.py`
- `backend/src/tasks/advance_goal_progress.py`
- `backend/tests/unit/test_budget_goals_repository.py`
- `backend/tests/unit/tasks/test_advance_goal_progress.py`

**Edit (remove goals sections):**
- `frontend/components/Sidebar.tsx` — remove "Cele finansowe" nav entry
- `frontend/lib/api.ts` — remove 5 goals functions + type imports
- `backend/src/services/budget_simulation.py` — remove `budget_goals_repo` dependency
- `backend/src/app.py` — remove goals repo/service init, goals methods, dispose calls
- `backend/src/main.py` — remove 5 endpoints + imports
- `backend/src/celery_app.py` — remove task registration
- `backend/src/data.py` — remove 4 goals Pydantic models
- `backend/tests/unit/conftest.py` — remove 2 entries from ALL_PARAMS
- `backend/tests/unit/test_budget.py` — remove goals tests, update affordability tests
- `backend/tests/unit/test_services_domain.py` — remove 2 goal service test classes
- `backend/tests/unit/test_delegation.py` — remove 2 delegation tests
- `backend/tests/unit/test_app_unified_budget.py` — update emergency advice test
- `backend/tests/unit/test_services_llm.py` — update simulation service tests

---

## Task 1: Delete frontend pages and components

**Files:**
- Delete: `frontend/app/budget/goals/page.tsx`
- Delete: `frontend/components/budget/GoalCard.tsx`
- Delete: `frontend/components/budget/GoalForm.tsx`

- [ ] **Step 1: Delete the three files**

```bash
rm frontend/app/budget/goals/page.tsx
rm frontend/components/budget/GoalCard.tsx
rm frontend/components/budget/GoalForm.tsx
```

- [ ] **Step 2: Verify deletion**

```bash
ls frontend/app/budget/ && ls frontend/components/budget/
```

Expected: no `goals/` directory, no `GoalCard.tsx` or `GoalForm.tsx`

- [ ] **Step 3: Commit**

```bash
git add -A frontend/app/budget/goals/ frontend/components/budget/GoalCard.tsx frontend/components/budget/GoalForm.tsx
git commit -m "feat: remove financial goals frontend pages and components"
```

---

## Task 2: Remove goals from Sidebar navigation

**Files:**
- Modify: `frontend/components/Sidebar.tsx`

- [ ] **Step 1: Remove "Cele finansowe" from `budgetSubItems`**

In `frontend/components/Sidebar.tsx`, remove this line from `budgetSubItems`:

```ts
// REMOVE:
  { href: "/budget/goals", label: "Cele finansowe", icon: Target },
```

Result — `budgetSubItems` becomes:

```ts
const budgetSubItems = [
  { href: "/budget/simulations", label: "Symulacje", icon: Sliders },
  { href: "/budget/ai-insights", label: "Rekomendacje AI", icon: Sparkles },
];
```

- [ ] **Step 2: Remove unused `Target` import**

In the same file, remove `Target,` from the lucide-react import block:

```ts
// REMOVE this line from the import:
  Target,
```

- [ ] **Step 3: Verify lint passes**

```bash
cd frontend && npm run lint
```

Expected: no errors about `Target` or missing components.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/Sidebar.tsx
git commit -m "feat: remove Cele finansowe from sidebar navigation"
```

---

## Task 3: Remove goals API client functions from `api.ts`

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Remove type imports for goals**

In `frontend/lib/api.ts`, remove these lines from the import block (around lines 69–72):

```ts
// REMOVE:
  FinancialGoalListItem,
  FinancialGoalListItemSchema,
  MonthlySurplusResponse,
  MonthlySurplusResponseSchema,
```

- [ ] **Step 2: Remove the five goals functions**

Remove the following functions entirely (lines ~882–926):

```ts
// REMOVE all of these:
export async function getBudgetGoals(): Promise<FinancialGoalListItem[]> {
  return apiFetch("/api/budget/goals", FinancialGoalListItemSchema.array());
}

export async function getBudgetSurplus(): Promise<MonthlySurplusResponse> {
  return apiFetch("/api/budget/goals/surplus", MonthlySurplusResponseSchema);
}

export async function createGoal(data: {
  name: string;
  target_amount_pln: number;
  target_date?: string;
  priority_rank?: number;
  monthly_allocation_amount_pln?: number;
}): Promise<FinancialGoalListItem> {
  return apiFetch("/api/budget/goals", FinancialGoalListItemSchema, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateGoal(
  id: number,
  data: Partial<{
    name: string;
    target_amount_pln: number;
    target_date: string;
    priority_rank: number;
    monthly_allocation_amount_pln: number;
    is_active: boolean;
  }>
): Promise<FinancialGoalListItem> {
  return apiFetch(`/api/budget/goals/${id}`, FinancialGoalListItemSchema, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteGoal(id: number): Promise<void> {
  const res = await fetch(`/api/budget/goals/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}
```

- [ ] **Step 3: Verify lint passes**

```bash
cd frontend && npm run lint
```

Expected: no errors related to removed types or functions.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: remove financial goals API client functions"
```

---

## Task 4: Delete backend standalone files

**Files:**
- Delete: `backend/src/services/budget_goals.py`
- Delete: `backend/src/repositories/budget_goals.py`
- Delete: `backend/src/tasks/advance_goal_progress.py`
- Delete: `backend/tests/unit/test_budget_goals_repository.py`
- Delete: `backend/tests/unit/tasks/test_advance_goal_progress.py`

- [ ] **Step 1: Delete files**

```bash
rm backend/src/services/budget_goals.py
rm backend/src/repositories/budget_goals.py
rm backend/src/tasks/advance_goal_progress.py
rm backend/tests/unit/test_budget_goals_repository.py
rm backend/tests/unit/tasks/test_advance_goal_progress.py
```

- [ ] **Step 2: Verify**

```bash
ls backend/src/services/ && ls backend/src/repositories/ && ls backend/src/tasks/
```

Expected: no `budget_goals.py` in services or repositories, no `advance_goal_progress.py` in tasks.

- [ ] **Step 3: Commit**

```bash
git add -A backend/src/services/budget_goals.py backend/src/repositories/budget_goals.py backend/src/tasks/advance_goal_progress.py backend/tests/unit/test_budget_goals_repository.py backend/tests/unit/tasks/test_advance_goal_progress.py
git commit -m "feat: delete budget goals service, repository, task, and pure unit tests"
```

---

## Task 5: Remove goals dependency from `BudgetSimulationService`

**Files:**
- Modify: `backend/src/services/budget_simulation.py`

- [ ] **Step 1: Remove `BudgetGoalsRepository` import**

Remove this line:

```python
# REMOVE:
from ..repositories.budget_goals import BudgetGoalsRepository
```

- [ ] **Step 2: Remove `budget_goals_repo` param from `__init__`**

Change `__init__` from:

```python
    def __init__(
        self,
        budget_analysis_repo: BudgetAnalysisRepository,
        budget_goals_repo: BudgetGoalsRepository,
        budget_simulations_repo: BudgetSimulationsRepository,
        openai_client: Optional[OpenAI] = None,
    ):
        self.analysis_repo = budget_analysis_repo
        self.goals_repo = budget_goals_repo
        self.simulations_repo = budget_simulations_repo
        self.openai_client = openai_client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
```

to:

```python
    def __init__(
        self,
        budget_analysis_repo: BudgetAnalysisRepository,
        budget_simulations_repo: BudgetSimulationsRepository,
        openai_client: Optional[OpenAI] = None,
    ):
        self.analysis_repo = budget_analysis_repo
        self.simulations_repo = budget_simulations_repo
        self.openai_client = openai_client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
```

- [ ] **Step 3: Replace goals lookup in `run_projection` with empty list**

In `run_projection`, replace:

```python
        # Goal impact calculation
        goals = self.goals_repo.get_all_goals()
        goal_impacts: list[SimulationGoalImpact] = []

        for goal in goals:
            alloc = float(goal["monthly_allocation_amount"])
            if alloc <= 0:
                continue
            target = float(goal["target_amount"])
            progress = float(goal["accumulated_progress"])
            remaining = max(0.0, target - progress)

            baseline_months = math.ceil(remaining / alloc) if alloc > 0 and remaining > 0 else 0
            baseline_completion = (
                (datetime.date.today() + datetime.timedelta(days=baseline_months * 30)).isoformat()
                if baseline_months > 0 else None
            )

            # Simulated: count months where simulated_surplus >= alloc
            can_allocate_months = sum(
                1 for p in projection if p.simulated_surplus_pln >= alloc
            )
            if can_allocate_months == 0 and remaining > 0:
                simulated_months = None
                simulated_completion = None
                delay = 99
            else:
                total_months = horizon
                simulated_months = math.ceil(remaining / alloc) if alloc > 0 and remaining > 0 else 0
                # Add delay for months where we couldn't allocate
                months_blocked = sum(
                    1 for p in projection if p.simulated_surplus_pln < alloc
                )
                simulated_months_total = simulated_months + months_blocked if simulated_months else 0
                simulated_completion = (
                    (datetime.date.today() + datetime.timedelta(days=simulated_months_total * 30)).isoformat()
                    if simulated_months_total > 0 else None
                )
                delay = simulated_months_total - baseline_months if simulated_months_total else 0

            goal_impacts.append(
                SimulationGoalImpact(
                    goal_id=goal["id"],
                    goal_name=goal["name"],
                    baseline_completion_date=baseline_completion,
                    simulated_completion_date=simulated_completion,
                    delay_months=max(0, delay),
                )
            )
```

with:

```python
        goal_impacts: list[SimulationGoalImpact] = []
```

- [ ] **Step 4: Replace goals lookup in `_build_context_summary` with empty list**

In `_build_context_summary`, change:

```python
    def _build_context_summary(self) -> dict:
        history = self.analysis_repo.get_monthly_history(3)
        goals = self.goals_repo.get_all_goals()
        focus = self.analysis_repo.get_financial_focus()

        return {
            "monthly_history": history,
            "active_goals": [
                {
                    "name": g["name"],
                    "target": float(g["target_amount"]),
                    "progress": float(g["accumulated_progress"]),
                    "monthly_allocation": float(g["monthly_allocation_amount"]),
                }
                for g in goals
            ],
            "financial_focus": focus["label"] if focus else None,
        }
```

to:

```python
    def _build_context_summary(self) -> dict:
        history = self.analysis_repo.get_monthly_history(3)
        focus = self.analysis_repo.get_financial_focus()

        return {
            "monthly_history": history,
            "active_goals": [],
            "financial_focus": focus["label"] if focus else None,
        }
```

- [ ] **Step 5: Check for any remaining `goals_repo` references**

```bash
grep -n "goals_repo" backend/src/services/budget_simulation.py
```

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/budget_simulation.py
git commit -m "feat: remove budget goals dependency from BudgetSimulationService"
```

---

## Task 6: Remove goals wiring from `app.py`

**Files:**
- Modify: `backend/src/app.py`

- [ ] **Step 1: Remove `BudgetGoalsRepository` and `BudgetGoalsService` imports**

Remove these two lines from the imports at the top of `app.py`:

```python
# REMOVE:
from .repositories.budget_goals import BudgetGoalsRepository
from .services.budget_goals import BudgetGoalsService
```

- [ ] **Step 2: Remove goals data model imports**

In the `from .data import (...)` block, remove:

```python
# REMOVE these four lines:
    FinancialGoalListItem,
    CreateFinancialGoalRequest,
    UpdateFinancialGoalRequest,
    MonthlySurplusResponse,
```

- [ ] **Step 3: Remove `budget_goals_repository` and `budget_goals_service` from `__init__` params**

Remove these two lines from the `__init__` parameter list (around lines 142, 157):

```python
# REMOVE:
        budget_goals_repository=None,
# REMOVE:
        budget_goals_service=None,
```

- [ ] **Step 4: Remove goals repository and service initialization**

Remove these lines from the `__init__` body (around lines 204, 213–219):

```python
# REMOVE:
        self.budget_goals_repository = budget_goals_repository or BudgetGoalsRepository(self.eye_budget_db_context)
```

```python
# REMOVE:
        self.budget_goals_service = budget_goals_service or BudgetGoalsService(
            budget_goals_repo=self.budget_goals_repository,
            budget_analysis_repo=self.budget_analysis_repository,
        )
```

Also remove `budget_goals_repo` kwarg from `BudgetSimulationService` init — change:

```python
        self.budget_simulation_service = budget_simulation_service or BudgetSimulationService(
            budget_analysis_repo=self.budget_analysis_repository,
            budget_goals_repo=self.budget_goals_repository,
            budget_simulations_repo=self.budget_simulations_repository,
        )
```

to:

```python
        self.budget_simulation_service = budget_simulation_service or BudgetSimulationService(
            budget_analysis_repo=self.budget_analysis_repository,
            budget_simulations_repo=self.budget_simulations_repository,
        )
```

- [ ] **Step 5: Update `check_affordability` to hardcode `goal_allocations_pln=0.0`**

Change:

```python
    def check_affordability(self, amount_pln: float) -> AffordabilityCheckResponse:
        focus = self.budget_analysis_service.get_financial_focus()
        focus_label = focus.label if focus.id is not None else None
        goal_allocations = self.budget_goals_repository.get_active_goal_allocations_total()
        return self.budget_analysis_service.check_affordability(
            amount_pln=amount_pln,
            financial_focus_label=focus_label,
            goal_allocations_pln=goal_allocations,
        )
```

to:

```python
    def check_affordability(self, amount_pln: float) -> AffordabilityCheckResponse:
        focus = self.budget_analysis_service.get_financial_focus()
        focus_label = focus.label if focus.id is not None else None
        return self.budget_analysis_service.check_affordability(
            amount_pln=amount_pln,
            financial_focus_label=focus_label,
            goal_allocations_pln=0.0,
        )
```

- [ ] **Step 6: Update `get_emergency_advice` to pass empty goals list**

Change:

```python
    def get_emergency_advice(self, amount_pln: float) -> EmergencyAdvisorResponse:
        active_goals = self.budget_goals_repository.get_all_goals()
        return self.budget_analysis_service.get_emergency_advice(amount_pln, active_goals)
```

to:

```python
    def get_emergency_advice(self, amount_pln: float) -> EmergencyAdvisorResponse:
        return self.budget_analysis_service.get_emergency_advice(amount_pln, [])
```

- [ ] **Step 7: Remove "Budget Goals methods" section**

Remove this entire block (lines ~1511–1528):

```python
    # ------------------------------------------------------------------
    # Budget Goals methods
    # ------------------------------------------------------------------

    def get_monthly_surplus(self) -> MonthlySurplusResponse:
        return self.budget_goals_service.get_monthly_surplus()

    def get_goals(self) -> list[FinancialGoalListItem]:
        return self.budget_goals_service.get_goals()

    def create_goal(self, req: CreateFinancialGoalRequest) -> FinancialGoalListItem:
        return self.budget_goals_service.create_goal(req)

    def update_goal(self, goal_id: int, req: UpdateFinancialGoalRequest):
        return self.budget_goals_service.update_goal(goal_id, req)

    def delete_goal(self, goal_id: int) -> bool:
        return self.budget_goals_service.delete_goal(goal_id)
```

- [ ] **Step 8: Remove goals dispose calls**

In the `dispose()` method, remove these two lines:

```python
# REMOVE:
        self.budget_goals_repository.dispose()
# REMOVE:
        self.budget_goals_service.dispose()
```

- [ ] **Step 9: Verify no remaining goals references**

```bash
grep -n "budget_goals\|BudgetGoals" backend/src/app.py
```

Expected: no output.

- [ ] **Step 10: Commit**

```bash
git add backend/src/app.py
git commit -m "feat: remove budget goals wiring from App class"
```

---

## Task 7: Remove goals endpoints from `main.py`

**Files:**
- Modify: `backend/src/main.py`

- [ ] **Step 1: Remove `advance_goal_progress_task` import**

Remove line 20:

```python
# REMOVE:
from src.tasks.advance_goal_progress import advance_goal_progress_task
```

- [ ] **Step 2: Remove goals data model imports**

Remove these four lines from the `from src.data import (...)` block:

```python
# REMOVE:
    FinancialGoalListItem,
    CreateFinancialGoalRequest,
    UpdateFinancialGoalRequest,
    MonthlySurplusResponse,
```

- [ ] **Step 3: Remove the five goals endpoint functions**

Remove lines ~1400–1456 — all five endpoint functions:

```python
# REMOVE all five functions:
@app.get("/budget/goals/surplus", response_model=MonthlySurplusResponse)
def get_budget_surplus() -> MonthlySurplusResponse:
    ...

@app.get("/budget/goals", response_model=list[FinancialGoalListItem])
def list_goals() -> list[FinancialGoalListItem]:
    ...

@app.post("/budget/goals", response_model=FinancialGoalListItem, status_code=201)
def create_goal(request: CreateFinancialGoalRequest) -> FinancialGoalListItem:
    ...

@app.put("/budget/goals/{goal_id}", response_model=FinancialGoalListItem)
def update_goal(goal_id: int, request: UpdateFinancialGoalRequest) -> FinancialGoalListItem:
    ...

@app.delete("/budget/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int) -> None:
    ...
```

- [ ] **Step 4: Verify no remaining goals references**

```bash
grep -n "goal\|Goal\|surplus\|MonthlySurplus" backend/src/main.py | grep -v "emergency\|EmergencyGoal\|SimulationGoal"
```

Expected: no output (emergency and simulation goal-impact references are intentionally kept).

- [ ] **Step 5: Commit**

```bash
git add backend/src/main.py
git commit -m "feat: remove /api/budget/goals/* endpoints from FastAPI app"
```

---

## Task 8: Remove goals task from `celery_app.py`

**Files:**
- Modify: `backend/src/celery_app.py`

- [ ] **Step 1: Remove task from includes list**

Remove this line from the `include` list:

```python
# REMOVE:
        "src.tasks.advance_goal_progress",
```

- [ ] **Step 2: Remove beat schedule entry**

Remove these lines from the `beat_schedule` dict:

```python
# REMOVE:
            "advance-goal-progress-monthly": {
                "task": "tasks.advance_goal_progress",
                ...
            },
```

(Remove the entire `"advance-goal-progress-monthly"` key/value block.)

- [ ] **Step 3: Verify**

```bash
grep -n "goal" backend/src/celery_app.py
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add backend/src/celery_app.py
git commit -m "feat: remove advance_goal_progress Celery task registration"
```

---

## Task 9: Remove goals models from `data.py`

**Files:**
- Modify: `backend/src/data.py`

- [ ] **Step 1: Remove four Pydantic model classes**

Remove these four classes entirely (lines ~834–873):

```python
# REMOVE:
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

**Note:** Keep `AffordabilityCheckResponse.active_goal_allocations_pln` — it stays at 0.0 in responses. Keep `SimulationGoalImpact` and `EmergencyGoalImpact` — they remain in simulation/emergency results as empty lists.

- [ ] **Step 2: Verify**

```bash
grep -n "FinancialGoal\|MonthlySurplus\|CreateFinancialGoal\|UpdateFinancialGoal" backend/src/data.py
```

Expected: no output.

- [ ] **Step 3: Run backend tests to check for import errors**

```bash
cd backend && python -m pytest -x -q 2>&1 | head -30
```

Expected: tests run (some may fail due to test files not yet updated — that is expected). No `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 4: Commit**

```bash
git add backend/src/data.py
git commit -m "feat: remove FinancialGoal and MonthlySurplus Pydantic models from data.py"
```

---

## Task 10: Clean up `conftest.py` and test files

**Files:**
- Modify: `backend/tests/unit/conftest.py`
- Modify: `backend/tests/unit/test_budget.py`
- Modify: `backend/tests/unit/test_services_domain.py`
- Modify: `backend/tests/unit/test_delegation.py`
- Modify: `backend/tests/unit/test_app_unified_budget.py`
- Modify: `backend/tests/unit/test_services_llm.py`

### conftest.py

- [ ] **Step 1: Remove `budget_goals_repository` and `budget_goals_service` from `ALL_PARAMS`**

Remove these two entries:

```python
# REMOVE:
    "budget_goals_repository",
# REMOVE:
    "budget_goals_service",
```

### test_budget.py

- [ ] **Step 2: Remove the `CreateFinancialGoalRequest` import**

Remove line 3:

```python
# REMOVE:
from src.data import CreateFinancialGoalRequest
```

- [ ] **Step 3: Update `test_check_affordability_fetches_focus_and_allocations`**

This test checked that `goal_allocations_pln` was fetched from the repo. After removing goals, `goal_allocations_pln` is always 0.0. Replace the test:

```python
# REMOVE the old test:
@pytest.mark.unit
def test_check_affordability_fetches_focus_and_allocations():
    # Arrange
    app = make_app()
    focus = MagicMock()
    focus.id = 1
    focus.label = "savings"
    app.budget_analysis_service.get_financial_focus.return_value = focus
    app.budget_goals_repository.get_active_goal_allocations_total.return_value = 500.0

    # Act
    app.check_affordability(1000.0)

    # Assert
    app.budget_analysis_service.check_affordability.assert_called_once_with(
        amount_pln=1000.0,
        financial_focus_label="savings",
        goal_allocations_pln=500.0,
    )
```

Replace with:

```python
@pytest.mark.unit
def test_check_affordability_passes_zero_goal_allocations():
    # Arrange
    app = make_app()
    focus = MagicMock()
    focus.id = 1
    focus.label = "savings"
    app.budget_analysis_service.get_financial_focus.return_value = focus

    # Act
    app.check_affordability(1000.0)

    # Assert
    app.budget_analysis_service.check_affordability.assert_called_once_with(
        amount_pln=1000.0,
        financial_focus_label="savings",
        goal_allocations_pln=0.0,
    )
```

- [ ] **Step 4: Update `test_check_affordability_uses_none_focus_when_no_focus_set`**

Remove the unused `budget_goals_repository` line:

```python
# REMOVE this line from the test:
    app.budget_goals_repository.get_active_goal_allocations_total.return_value = 0.0
```

- [ ] **Step 5: Remove three goals delegation tests**

Remove these three test functions entirely:

```python
# REMOVE:
@pytest.mark.unit
def test_get_goals_delegates():
    ...

@pytest.mark.unit
def test_create_goal_delegates_request():
    ...

@pytest.mark.unit
def test_delete_goal_delegates_goal_id():
    ...
```

### test_services_domain.py

- [ ] **Step 6: Remove goals imports**

Remove from imports:

```python
# REMOVE:
    CreateFinancialGoalRequest,
# REMOVE:
    UpdateFinancialGoalRequest,
```

```python
# REMOVE:
from src.services.budget_goals import BudgetGoalsService
```

- [ ] **Step 7: Remove `TestBudgetGoalsService` class (lines ~78–138)**

Remove the entire class:

```python
# REMOVE:
class TestBudgetGoalsService:
    def _make_service(self) ...
    def test_get_monthly_surplus_calculates_correctly(self): ...
    def test_create_goal_calls_repo(self): ...
```

- [ ] **Step 8: Remove `_make_goal_row` helper and `TestBudgetGoalsServiceExtended` class (lines ~350–470)**

Remove:
- `def _make_goal_row(...) -> dict:` function
- `class TestBudgetGoalsServiceExtended:` class (all methods)

### test_delegation.py

- [ ] **Step 9: Remove two goals delegation tests**

Remove these two test functions:

```python
# REMOVE:
@pytest.mark.unit
def test_get_monthly_surplus_delegates():
    # Arrange
    app = make_app()

    # Act
    app.get_monthly_surplus()

    # Assert
    app.budget_goals_service.get_monthly_surplus.assert_called_once()


@pytest.mark.unit
def test_update_goal_delegates():
    # Arrange
    app = make_app()
    req = MagicMock()

    # Act
    app.update_goal(1, req)

    # Assert
    app.budget_goals_service.update_goal.assert_called_once_with(1, req)
```

### test_app_unified_budget.py

- [ ] **Step 10: Update `test_get_emergency_advice_passes_goals_and_returns_service_value`**

Replace:

```python
@pytest.mark.unit
def test_get_emergency_advice_passes_goals_and_returns_service_value():
    # Arrange
    app = make_app()
    goals = [MagicMock()]
    app.budget_goals_repository.get_all_goals.return_value = goals
    expected = MagicMock()
    app.budget_analysis_service.get_emergency_advice.return_value = expected

    # Act
    result = app.get_emergency_advice(500.0)

    # Assert
    assert result is expected
    app.budget_analysis_service.get_emergency_advice.assert_called_once_with(500.0, goals)
```

with:

```python
@pytest.mark.unit
def test_get_emergency_advice_passes_empty_goals_list():
    # Arrange
    app = make_app()
    expected = MagicMock()
    app.budget_analysis_service.get_emergency_advice.return_value = expected

    # Act
    result = app.get_emergency_advice(500.0)

    # Assert
    assert result is expected
    app.budget_analysis_service.get_emergency_advice.assert_called_once_with(500.0, [])
```

### test_services_llm.py — `TestBudgetSimulationService`

- [ ] **Step 11: Update `_make_service` to remove `mock_goals_repo`**

Replace:

```python
    def _make_service(self):
        mock_analysis_repo = MagicMock()
        mock_goals_repo = MagicMock()
        mock_simulations_repo = MagicMock()
        mock_client = MagicMock()
        svc = BudgetSimulationService(
            budget_analysis_repo=mock_analysis_repo,
            budget_goals_repo=mock_goals_repo,
            budget_simulations_repo=mock_simulations_repo,
            openai_client=mock_client,
        )
        return svc, mock_analysis_repo, mock_goals_repo, mock_simulations_repo, mock_client
```

with:

```python
    def _make_service(self):
        mock_analysis_repo = MagicMock()
        mock_simulations_repo = MagicMock()
        mock_client = MagicMock()
        svc = BudgetSimulationService(
            budget_analysis_repo=mock_analysis_repo,
            budget_simulations_repo=mock_simulations_repo,
            openai_client=mock_client,
        )
        return svc, mock_analysis_repo, mock_simulations_repo, mock_client
```

- [ ] **Step 12: Update all tests in `TestBudgetSimulationService` that unpack 5 values or use `mock_goals_repo`**

After the change, `_make_service()` returns 4 values: `(svc, mock_analysis_repo, mock_simulations_repo, mock_client)`. Update every call-site in the class:

```python
# Pattern A — used goals_repo and client:
# OLD: svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
# NEW: svc, mock_analysis_repo, _, mock_client = self._make_service()

# Pattern B — used goals_repo and simulations_repo:
# OLD: svc, mock_analysis_repo, mock_goals_repo, mock_simulations_repo, _ = self._make_service()
# NEW: svc, mock_analysis_repo, mock_simulations_repo, _ = self._make_service()

# Pattern C — ignored goals_repo and simulations_repo:
# OLD: svc, mock_analysis_repo, _, mock_simulations_repo, _ = self._make_service()
# NEW: svc, mock_analysis_repo, mock_simulations_repo, _ = self._make_service()

# Pattern D — ignored all three extra:
# OLD: svc, mock_analysis_repo, _, _, _ = self._make_service()
# NEW: svc, mock_analysis_repo, _, _ = self._make_service()
```

Also remove any line of the form:
```python
mock_goals_repo.get_all_goals.return_value = []
```
from all tests (these lines are now unreachable).

- [ ] **Step 13: Delete `test_run_projection_with_goal_impact`**

Remove this entire test method (goals are always `[]`, so goal_impacts is always empty):

```python
# REMOVE:
    def test_run_projection_with_goal_impact(self):
        # Arrange — goal exists with allocation, triggers goal_impacts loop
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        ...
        # Assert — goal_impacts populated
        assert len(result.goal_impacts) == 1
        assert result.goal_impacts[0].goal_name == "Wakacje"
```

- [ ] **Step 14: Update `test_build_context_summary_returns_dict`**

Replace:

```python
    def test_build_context_summary_returns_dict(self):
        # Arrange
        svc, mock_analysis_repo, mock_goals_repo, _, _ = self._make_service()
        mock_analysis_repo.get_monthly_history.return_value = []
        mock_analysis_repo.get_financial_focus.return_value = {"label": "Oszczędności"}
        mock_goals_repo.get_all_goals.return_value = [
            {"name": "Dom", "target_amount": "200000.00",
             "accumulated_progress": "10000.00", "monthly_allocation_amount": "2000.00"},
        ]

        # Act
        result = svc._build_context_summary()

        # Assert
        assert "active_goals" in result
        assert result["financial_focus"] == "Oszczędności"
        assert len(result["active_goals"]) == 1
```

with:

```python
    def test_build_context_summary_returns_dict(self):
        # Arrange
        svc, mock_analysis_repo, _, _ = self._make_service()
        mock_analysis_repo.get_monthly_history.return_value = []
        mock_analysis_repo.get_financial_focus.return_value = {"label": "Oszczędności"}

        # Act
        result = svc._build_context_summary()

        # Assert
        assert "active_goals" in result
        assert result["financial_focus"] == "Oszczędności"
        assert result["active_goals"] == []
```

- [ ] **Step 15: Commit all test changes**

```bash
git add backend/tests/unit/conftest.py backend/tests/unit/test_budget.py backend/tests/unit/test_services_domain.py backend/tests/unit/test_delegation.py backend/tests/unit/test_app_unified_budget.py backend/tests/unit/test_services_llm.py
git commit -m "feat: remove financial goals from test files"
```

---

## Task 11: Full verification and final commit

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -q
```

Expected: all tests pass, 0 failures. If any fail with `AttributeError: ... budget_goals` or `ImportError`, check the file listed in the traceback for a missed reference.

- [ ] **Step 2: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Verify `/budget/goals` route no longer exists in frontend**

```bash
find frontend/app/budget -type f | sort
```

Expected: no `goals/` directory.

- [ ] **Step 4: Verify no remaining goals references in backend src**

```bash
grep -rn "budget_goals\|BudgetGoals\|advance_goal" backend/src/ --include="*.py"
```

Expected: no output.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete removal of financial goals (Cele finansowe) feature"
```
