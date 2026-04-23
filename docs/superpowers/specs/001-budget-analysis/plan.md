# Implementation Plan: Budget Analysis & Insights

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-budget-analysis/spec.md`

## Summary

Build a household budget analysis suite on top of the existing transaction data (bank, cash, receipt). The feature adds: monthly per-category spending dashboards with trend charts, automatic recurring/cyclical expense detection with 90-day alerts, an affordability check ("can I buy this now?"), a Budget Simulation (what-if projections for significant purchases), financial goals with monthly surplus allocation, an emergency expense advisor, and background AI recommendations powered by OpenAI. All new compute-heavy work (simulation, AI recs) runs as Celery tasks pushing results via Pusher/Soketi. The frontend adds a `/budget` section with 4 pages. No new top-level infrastructure is required.

## Technical Context

**Language/Version**: Python 3.x (backend) · TypeScript strict / Next.js 14 App Router (frontend)  
**Primary Dependencies**: FastAPI · Pydantic v2 · psycopg2 · Celery + Redis · OpenAI · recharts (already installed) · @tanstack/react-query v5 · Zod v3  
**Storage**: PostgreSQL — 5 new tables; no new services required  
**Testing**: pytest (backend unit + integration) · `npx tsc --noEmit` + `npm run lint` (frontend)  
**Target Platform**: Web — Linux server (Docker Compose) + browser  
**Performance Goals**: All synchronous read endpoints ≤ 200 ms p95; frontend LCP ≤ 2.5 s; simulation results delivered async via Pusher (Celery task, no UI blocking)  
**Constraints**: Long-running AI operations (simulation, AI recommendations) MUST return HTTP 202 immediately and push final results via Pusher — never block synchronously  
**Scale/Scope**: Single household user; transaction volume ~100–500/month; simulation projections span 12–24 months

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Code Quality & Separation | ✅ PASS | Python stays in `backend/`, TypeScript in `frontend/`; all Pydantic models in `data.py`; no hardcoded values |
| II. Testing Standards | ✅ PASS (with obligation) | New services in `services/`, repositories in `repositories/`, and utilities in `frontend/lib/` **must** have unit tests. New endpoints **must** have integration tests. Existing test-gap acknowledged as debt. |
| III. UX Consistency | ✅ PASS | All UI strings in Polish; design-system primitives only; React Query mutations; simulation uses HTTP 202 + Pusher (same as OCR pattern) |
| IV. Performance | ✅ PASS | Read endpoints (monthly breakdown, recurring, affordability) return pre-aggregated SQL; AI simulation runs in Celery; indexes added for all new tables queried by date/category |
| V. Frontend Architecture | ✅ PASS | App Router only; thin proxy handlers; `apiFetch` + Zod; `useState` controlled forms; recharts already installed |
| VI. Backend Conventions | ✅ PASS | All routes in `main.py` under `# --- Budget Analysis ---`; App per-request; Pydantic naming convention respected; parameterized SQL; Yoyo migrations |

**Post-design re-check**: Confirmed after writing data-model.md and contracts — no violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-budget-analysis/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── budget-analysis.md
│   ├── budget-goals.md
│   └── budget-simulations.md
└── tasks.md             # Phase 2 output (not yet created)
```

### Source Code (repository root)

```text
backend/
├── migrations/
│   ├── 20260313_01_budget-category-classifications.sql
│   ├── 20260313_02_budget-financial-focus.sql
│   ├── 20260313_03_budget-financial-goals.sql
│   ├── 20260313_04_budget-simulations.sql
│   └── 20260313_05_budget-ai-recommendations.sql
└── src/
    ├── main.py                                  # add # --- Budget Analysis --- section
    ├── app.py                                   # wire 3 new repos + 3 new services
    ├── data.py                                  # add ~25 new Pydantic models
    ├── repositories/
    │   ├── budget_analysis.py                   # NEW: monthly breakdown, recurring detection
    │   ├── budget_goals.py                      # NEW: CRUD goals + financial focus
    │   └── budget_simulations.py                # NEW: CRUD simulations + AI recs
    ├── services/
    │   ├── budget_analysis.py                   # NEW: affordability, classification logic
    │   ├── budget_goals.py                      # NEW: surplus calc, allocation logic
    │   └── budget_simulation.py                 # NEW: projection math + OpenAI narrative
    └── tasks/
        ├── run_budget_simulation.py             # NEW: Celery task (simulation)
        └── refresh_ai_recommendations.py        # NEW: Celery task (background AI recs)

frontend/
├── app/
│   ├── budget/
│   │   ├── page.tsx                             # NEW: main dashboard
│   │   ├── goals/
│   │   │   └── page.tsx                         # NEW: goals management
│   │   ├── simulations/
│   │   │   ├── page.tsx                         # NEW: simulations list
│   │   │   └── [id]/
│   │   │       └── page.tsx                     # NEW: simulation results
│   │   └── ai-insights/
│   │       └── page.tsx                         # NEW: AI recommendations
│   └── api/
│       └── budget/
│           ├── analysis/
│           │   ├── monthly/route.ts             # NEW proxy
│           │   ├── recurring-expenses/route.ts  # NEW proxy
│           │   ├── cyclical-alerts/route.ts     # NEW proxy
│           │   └── affordability/route.ts       # NEW proxy
│           ├── category-classifications/
│           │   ├── route.ts                     # NEW proxy (GET)
│           │   └── [id]/route.ts                # NEW proxy (PUT)
│           ├── financial-focus/route.ts         # NEW proxy (GET + PUT)
│           ├── goals/
│           │   ├── route.ts                     # NEW proxy (GET + POST)
│           │   ├── surplus/route.ts             # NEW proxy (GET)
│           │   └── [id]/route.ts                # NEW proxy (PUT + DELETE)
│           ├── simulations/
│           │   ├── route.ts                     # NEW proxy (GET + POST)
│           │   └── [id]/route.ts                # NEW proxy (GET + DELETE)
│           ├── ai-recommendations/
│           │   ├── route.ts                     # NEW proxy (GET)
│           │   └── refresh/route.ts             # NEW proxy (POST)
│           └── emergency-advisor/route.ts       # NEW proxy (POST)
├── components/
│   └── budget/
│       ├── MonthlyBreakdownChart.tsx            # NEW: bar/pie chart via recharts
│       ├── TrendLineChart.tsx                   # NEW: monthly total trend
│       ├── RecurringExpensesList.tsx            # NEW
│       ├── CyclicalAlertBanner.tsx              # NEW
│       ├── AffordabilityChecker.tsx             # NEW: inline form + result
│       ├── GoalCard.tsx                         # NEW
│       ├── GoalForm.tsx                         # NEW: controlled form
│       ├── SimulationForm.tsx                   # NEW: controlled form
│       ├── SimulationResultView.tsx             # NEW: charts + AI narrative
│       ├── EmergencyAdvisorPanel.tsx            # NEW
│       └── AIRecommendationsList.tsx            # NEW
└── lib/
    ├── api.ts                                   # add budget domain functions
    └── types.ts                                 # add budget Zod schemas
```

**Structure Decision**: Web application (Option 2) — existing `backend/` + `frontend/` monorepo layout. All new backend code follows existing patterns exactly. New frontend pages live under `app/budget/`. New components live under `components/budget/` to keep feature-level components separate from UI primitives.

## Complexity Tracking

No constitution violations. All patterns fit within existing established conventions.
