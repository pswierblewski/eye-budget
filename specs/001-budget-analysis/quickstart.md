# Quickstart: Budget Analysis & Insights

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13

---

## Prerequisites

All existing services must be running:
```bash
docker compose up          # Redis + Soketi + backend + celery-worker
cd frontend && npm run dev  # http://localhost:3000
```

---

## Step 1: Apply Database Migrations

Run from the `backend/` directory (requires `yoyo.ini` with DB credentials):

```bash
cd backend
yoyo apply
```

Expected output — 5 new migrations applied:
```
Applying 20260313_01_budget-category-classifications
Applying 20260313_02_budget-financial-focus
Applying 20260313_03_budget-financial-goals
Applying 20260313_04_budget-simulations
Applying 20260313_05_budget-ai-recommendations
```

---

## Step 2: Verify New Endpoints

After starting the backend (`uvicorn src.main:app --reload --port 8000`), confirm the new routes are registered:

```bash
curl http://localhost:8000/budget/analysis/monthly
curl http://localhost:8000/budget/goals
curl http://localhost:8000/budget/category-classifications
```

The monthly analysis endpoint returns an empty or populated result depending on existing transaction data. The category classifications endpoint auto-seeds on first call.

---

## Step 3: Seed Category Classifications

On first call to `GET /budget/category-classifications`, the backend auto-seeds all existing categories with essential/discretionary classifications using the keyword heuristic. Check the result:

```bash
curl http://localhost:8000/budget/category-classifications | python3 -m json.tool
```

Expected: all categories listed with `classification: "essential"` or `"discretionary"`. Override any wrong classification:

```bash
curl -X PUT http://localhost:8000/budget/category-classifications/5 \
  -H "Content-Type: application/json" \
  -d '{"classification": "essential"}'
```

---

## Step 4: Set a Financial Focus

```bash
curl -X PUT http://localhost:8000/budget/financial-focus \
  -H "Content-Type: application/json" \
  -d '{"label": "Nadpłata kredytu hipotecznego", "description": "Min. 1000 zł/miesiąc"}'
```

---

## Step 5: Create a Goal

```bash
curl -X POST http://localhost:8000/budget/goals \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wyjazd w góry",
    "target_amount_pln": 3000.00,
    "target_date": "2026-07-01",
    "priority_rank": 1,
    "monthly_allocation_amount_pln": 750.00
  }'
```

---

## Step 6: Run a Budget Simulation

```bash
curl -X POST http://localhost:8000/budget/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test okna",
    "expense_name": "Wymiana okien",
    "expense_amount_pln": 20000.00,
    "expense_type": "one_time",
    "expense_start_date": "2026-06-01"
  }'
```

Returns `202` with `simulation_id`. Poll the result:

```bash
# Replace 1 with actual simulation_id
curl http://localhost:8000/budget/simulations/1 | python3 -m json.tool
```

Wait for `"status": "done"`. If the Celery worker is not running, status stays `pending`.

---

## Step 7: Trigger AI Recommendations

Requires ≥ 3 months of transaction data AND a running Celery worker:

```bash
curl -X POST http://localhost:8000/budget/ai-recommendations/refresh
# Returns 202

# Check result after ~10-30 seconds
curl http://localhost:8000/budget/ai-recommendations | python3 -m json.tool
```

---

## Frontend Navigation

After `npm run dev`, the new pages are at:

| URL | Page |
|-----|------|
| `http://localhost:3000/budget` | Monthly spending dashboard |
| `http://localhost:3000/budget/goals` | Goals management |
| `http://localhost:3000/budget/simulations` | Saved simulations |
| `http://localhost:3000/budget/simulations/1` | Simulation results |
| `http://localhost:3000/budget/ai-insights` | AI recommendations |

Add a `NavLink` for `/budget` in `frontend/app/layout.tsx` sidebar to make the section accessible.

---

## Running Tests

### Backend unit tests

```bash
cd backend
python -m pytest tests/unit/services/test_budget_analysis.py -v
python -m pytest tests/unit/services/test_budget_goals.py -v
python -m pytest tests/unit/services/test_budget_simulation.py -v
python -m pytest tests/unit/repositories/test_budget_analysis_repo.py -v
```

### Backend integration tests

```bash
python -m pytest tests/integration/test_budget_endpoints.py -v
```

Integration tests require a running PostgreSQL instance (test DB). The test DB is seeded with:
- 4 months of synthetic bank transactions (income + various expense categories)
- Known recurring patterns for detection testing

### Frontend type check + lint

```bash
cd frontend
npx tsc --noEmit    # must report zero errors
npm run lint        # must report zero errors
npm run build       # must complete without errors
```

---

## Key Test Scenarios

| Scenario | How to verify |
|----------|--------------|
| Monthly breakdown with no data | `GET /budget/analysis/monthly?year=2020&month=1` → all zeros, no crash |
| Recurring detection needs 3+ occurrences | Use test DB with 2 occurrences → not detected; 3+ → detected |
| Affordability: GREEN verdict | Amount well below `freely_available_pln` |
| Affordability: YELLOW verdict | Amount fits in `available_this_month` but > `freely_available` |
| Affordability: RED verdict | Amount > `available_this_month` |
| Simulation task failure | Stop Celery worker; create simulation → stays `pending`; restart → completes |
| AI recs with < 3 months data | `has_sufficient_data: false`, `insights: []` |
| Category classification override | PUT classification → `is_user_override: true`; GET returns new value |
| Goal progress accumulation | Celery beat fires `advance_goal_progress` → `accumulated_progress` increases by allocation |

---

## Environment Variables (no new vars required)

All existing env vars cover this feature:
- `OPENAI_API_KEY` — used by simulation and AI recommendations tasks
- `REDIS_URL` — used by Celery task queue
- `SOKETI_*` — used by Pusher events
- `POSTGRESQL_*` — used by all new repositories

No new environment variables are introduced.
