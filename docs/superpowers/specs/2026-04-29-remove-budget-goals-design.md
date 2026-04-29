# Design: Remove Financial Goals (Cele finansowe)

**Date**: 2026-04-29  
**Type**: Removal / cleanup  
**Scope**: Full removal — frontend, backend, no DB migration rollback

## Context

The "Cele finansowe" (Financial Goals) sub-feature of the Budget tab was implemented as part of `001-budget-analysis` but is no longer needed. This design covers its complete removal from the codebase.

## Files to Delete

| File | Reason |
|------|--------|
| `frontend/app/budget/goals/page.tsx` | Goals page |
| `frontend/components/budget/GoalCard.tsx` | Goal display component |
| `frontend/components/budget/GoalForm.tsx` | Goal create/edit form |
| `backend/src/services/budget_goals.py` | Goals business logic |
| `backend/src/repositories/budget_goals.py` | Goals DB access layer |
| `backend/src/tasks/advance_goal_progress.py` | Celery task for monthly goal progress |
| `backend/tests/unit/test_budget_goals_repository.py` | Repository unit tests |
| `backend/tests/unit/tasks/test_advance_goal_progress.py` | Task unit tests |

## Files to Edit

| File | Change |
|------|--------|
| `frontend/components/Sidebar.tsx` | Remove `{ href: '/budget/goals', label: 'Cele finansowe' }` submenu entry |
| `frontend/lib/api.ts` | Remove all goals-related API client functions |
| `backend/src/main.py` | Remove all `/api/budget/goals/*` endpoints and import of `advance_goal_progress_task`, `BudgetGoalsService`, `BudgetGoalsRepository` |
| `backend/src/data.py` | Remove Pydantic models related to goals |
| `backend/src/celery_app.py` | Remove `src.tasks.advance_goal_progress` from task list and beat schedule |
| `backend/tests/unit/test_budget.py` | Remove goals-related test cases |
| `backend/tests/unit/test_services_domain.py` | Remove goals-related test cases |
| `backend/tests/unit/test_delegation.py` | Remove goals-related test cases |
| `backend/tests/unit/test_app_unified_budget.py` | Remove goals-related test cases |
| `backend/tests/unit/conftest.py` | Remove goals-related fixtures |
| `backend/tests/unit/test_services_llm.py` | Remove goals-related test cases |

## Out of Scope

- Database migration rollback — `budget_financial_goals` table stays in DB; rollback is a separate operation if ever needed
- Removing any other Budget sub-features (Symulacje, Rekomendacje AI, monthly analysis)

## Verification

After removal:
- `npm run lint` passes in `frontend/`
- `python -m pytest` passes in `backend/`
- No broken imports referencing deleted files
- `/budget/goals` route returns 404
- Sidebar no longer shows "Cele finansowe" entry
