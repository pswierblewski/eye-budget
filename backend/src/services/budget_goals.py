"""
Service for financial goals and monthly surplus.
"""
from __future__ import annotations

import datetime
import math
from typing import Optional

from ..data import (
    FinancialGoalListItem,
    MonthlySurplusResponse,
    CreateFinancialGoalRequest,
    UpdateFinancialGoalRequest,
)
from ..repositories.budget_goals import BudgetGoalsRepository
from ..repositories.budget_analysis import BudgetAnalysisRepository


class BudgetGoalsService:
    def __init__(
        self,
        budget_goals_repo: BudgetGoalsRepository,
        budget_analysis_repo: BudgetAnalysisRepository,
    ):
        self.goals_repo = budget_goals_repo
        self.analysis_repo = budget_analysis_repo

    def dispose(self):
        pass

    def get_monthly_surplus(self) -> MonthlySurplusResponse:
        rolling = self.analysis_repo.get_rolling_3month_averages()
        current = self.analysis_repo.get_current_month_income_and_expenses()
        total_allocations = self.goals_repo.get_active_goal_allocations_total()

        avg_income = rolling["avg_income"]
        avg_expenses = rolling["avg_expenses"]
        avg_surplus = avg_income - avg_expenses

        current_income = current["income_pln"]
        current_expenses = current["expenses_pln"]
        current_surplus = current_income - current_expenses

        unallocated = current_surplus - total_allocations

        return MonthlySurplusResponse(
            avg_income_3m_pln=round(avg_income, 2),
            avg_expenses_3m_pln=round(avg_expenses, 2),
            avg_surplus_3m_pln=round(avg_surplus, 2),
            current_month_income_pln=round(current_income, 2),
            current_month_expenses_pln=round(current_expenses, 2),
            current_month_surplus_pln=round(current_surplus, 2),
            total_monthly_goal_allocations_pln=round(total_allocations, 2),
            unallocated_surplus_pln=round(unallocated, 2),
        )

    def _enrich_goal(self, row: dict) -> FinancialGoalListItem:
        target = float(row["target_amount"])
        progress = float(row["accumulated_progress"])
        alloc = float(row["monthly_allocation_amount"])
        remaining = max(0.0, target - progress)

        progress_pct = (progress / target * 100) if target > 0 else 0.0

        months_to_completion: Optional[int] = None
        projected_completion_date: Optional[str] = None
        if alloc > 0 and remaining > 0:
            months_to_completion = math.ceil(remaining / alloc)
            today = datetime.date.today()
            completion_date = today + datetime.timedelta(days=months_to_completion * 30)
            projected_completion_date = completion_date.isoformat()
        elif remaining <= 0:
            months_to_completion = 0
            projected_completion_date = datetime.date.today().isoformat()

        target_date = row.get("target_date")
        if isinstance(target_date, datetime.date):
            target_date = target_date.isoformat()

        created_at = row.get("created_at")
        if isinstance(created_at, datetime.datetime):
            created_at = created_at.isoformat()

        return FinancialGoalListItem(
            id=row["id"],
            name=row["name"],
            target_amount_pln=target,
            target_date=target_date,
            priority_rank=row["priority_rank"],
            monthly_allocation_amount_pln=alloc,
            accumulated_progress_pln=progress,
            progress_pct=round(progress_pct, 2),
            months_to_completion=months_to_completion,
            projected_completion_date=projected_completion_date,
            is_active=row["is_active"],
        )

    def get_goals(self) -> list[FinancialGoalListItem]:
        rows = self.goals_repo.get_all_goals()
        return [self._enrich_goal(r) for r in rows]

    def create_goal(self, req: CreateFinancialGoalRequest) -> FinancialGoalListItem:
        row = self.goals_repo.create_goal(
            name=req.name,
            target_amount=req.target_amount_pln,
            target_date=req.target_date,
            priority_rank=req.priority_rank,
            monthly_allocation=req.monthly_allocation_amount_pln,
        )
        if row is None:
            raise ValueError("Failed to create goal")
        return self._enrich_goal(row)

    def update_goal(self, goal_id: int, req: UpdateFinancialGoalRequest) -> Optional[FinancialGoalListItem]:
        fields = req.model_dump(exclude_none=True)
        row = self.goals_repo.update_goal(goal_id, **fields)
        if row is None:
            return None
        return self._enrich_goal(row)

    def delete_goal(self, goal_id: int) -> bool:
        return self.goals_repo.soft_delete_goal(goal_id)
