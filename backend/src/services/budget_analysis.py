"""
Service for budget analysis: monthly breakdown, category classification,
financial focus, recurring expenses, cyclical alerts, affordability check,
and emergency advisor.
"""
from __future__ import annotations

import datetime
import math
from typing import Optional

from ..data import (
    BudgetMonthlyResponse,
    BudgetCategoryMonthlyItem,
    CategoryClassificationItem,
    FinancialFocusResponse,
    RecurringExpenseItem,
    CyclicalAlertItem,
    AffordabilityCheckResponse,
    EmergencyAdvisorResponse,
    EmergencyReductionOption,
    EmergencyGoalImpact,
)
from ..repositories.budget_analysis import BudgetAnalysisRepository, _classify_by_keyword


class BudgetAnalysisService:
    def __init__(self, budget_analysis_repo: BudgetAnalysisRepository, categories_repo):
        self.repo = budget_analysis_repo
        self.categories_repo = categories_repo

    def dispose(self):
        pass

    # ------------------------------------------------------------------
    # Monthly breakdown
    # ------------------------------------------------------------------

    def get_monthly_breakdown(self, year: int, month: int) -> BudgetMonthlyResponse:
        rows = self.repo.get_monthly_category_breakdown(year, month)
        totals = self.repo.get_monthly_totals(year, month)

        total_expenses = totals["expenses_pln"]
        total_income = totals["income_pln"]
        prev_total = totals["prev_expenses_pln"]

        categories = []
        for row in rows:
            total_pln = float(row["total_pln"])
            prev_pln = float(row["prev_month_pln"])
            pct_of_total = (total_pln / total_expenses * 100) if total_expenses > 0 else 0.0
            change_pct = ((total_pln - prev_pln) / prev_pln * 100) if prev_pln > 0 else 0.0
            categories.append(
                BudgetCategoryMonthlyItem(
                    category_id=row["category_id"],
                    category_name=row["category_name"],
                    classification=row["classification"],
                    total_pln=total_pln,
                    pct_of_total=round(pct_of_total, 2),
                    prev_month_pln=prev_pln,
                    change_pct=round(change_pct, 2),
                )
            )

        mom_change = ((total_expenses - prev_total) / prev_total * 100) if prev_total > 0 else 0.0

        return BudgetMonthlyResponse(
            year=year,
            month=month,
            total_expenses_pln=total_expenses,
            total_income_pln=total_income,
            surplus_pln=total_income - total_expenses,
            categories=categories,
            prev_month_total_pln=prev_total,
            month_over_month_change_pct=round(mom_change, 2),
        )

    # ------------------------------------------------------------------
    # Category classifications
    # ------------------------------------------------------------------

    def seed_and_get_classifications(self) -> list[CategoryClassificationItem]:
        """Seed missing classifications on first call, then return all."""
        all_categories = self.repo.get_all_category_ids()
        classified_ids = self.repo.get_classified_category_ids()

        for cat in all_categories:
            if cat["id"] not in classified_ids:
                classification = _classify_by_keyword(cat["name"])
                self.repo.upsert_classification(cat["id"], classification, False)

        rows = self.repo.get_all_classifications()
        return [
            CategoryClassificationItem(
                category_id=r["category_id"],
                category_name=r["category_name"],
                classification=r["classification"],
                is_user_override=r["is_user_override"],
            )
            for r in rows
        ]

    def update_category_classification(
        self, category_id: int, classification: str
    ) -> CategoryClassificationItem:
        ok = self.repo.upsert_classification(category_id, classification, True)
        if not ok:
            raise ValueError(f"Category {category_id} not found or update failed")
        row = self.repo.get_classification_by_category(category_id)
        if row is None:
            raise ValueError(f"Category {category_id} not found")
        return CategoryClassificationItem(
            category_id=row["category_id"],
            category_name=row["category_name"],
            classification=row["classification"],
            is_user_override=row["is_user_override"],
        )

    # ------------------------------------------------------------------
    # Financial focus
    # ------------------------------------------------------------------

    def get_financial_focus(self) -> FinancialFocusResponse:
        row = self.repo.get_financial_focus()
        if row is None:
            return FinancialFocusResponse(id=None, label="", description=None, is_active=False)
        return FinancialFocusResponse(
            id=row["id"],
            label=row["label"],
            description=row["description"],
            is_active=row["is_active"],
        )

    def set_financial_focus(self, label: str, description: Optional[str]) -> FinancialFocusResponse:
        row = self.repo.set_financial_focus(label, description)
        if row is None:
            raise ValueError("Failed to set financial focus")
        return FinancialFocusResponse(
            id=row["id"],
            label=row["label"],
            description=row["description"],
            is_active=row["is_active"],
        )

    # ------------------------------------------------------------------
    # Recurring expenses & cyclical alerts
    # ------------------------------------------------------------------

    def get_recurring_expenses(self) -> list[RecurringExpenseItem]:
        rows = self.repo.get_recurring_expenses()
        return [
            RecurringExpenseItem(
                vendor_name=r["vendor_name"],
                category_name=r["category_name"],
                frequency=r["frequency"],
                avg_amount_pln=r["avg_amount_pln"],
                last_occurrence_date=r["last_occurrence_date"],
                next_expected_date=r["next_expected_date"],
                amount_min_pln=r["amount_min_pln"],
                amount_max_pln=r["amount_max_pln"],
                occurrence_count=r["occurrence_count"],
            )
            for r in rows
        ]

    def get_cyclical_alerts(self) -> list[CyclicalAlertItem]:
        rows = self.repo.get_cyclical_alerts()
        return [
            CyclicalAlertItem(
                vendor_name=r["vendor_name"],
                category_name=r["category_name"],
                next_expected_date=r["next_expected_date"],
                days_until=r["days_until"],
                expected_amount_pln=r["expected_amount_pln"],
                amount_range_pln=r["amount_range_pln"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Affordability check
    # ------------------------------------------------------------------

    def check_affordability(
        self,
        amount_pln: float,
        financial_focus_label: Optional[str],
        goal_allocations_pln: float,
    ) -> AffordabilityCheckResponse:
        data = self.repo.get_current_month_income_and_expenses()
        income = data["income_pln"]
        expenses = data["expenses_pln"]
        upcoming_30d = data["upcoming_recurring_sum_30d"]

        available_this_month = income - expenses
        safety_buffer = max(0.0, upcoming_30d + goal_allocations_pln)
        freely_available = available_this_month - safety_buffer

        if amount_pln <= freely_available:
            verdict = "green"
            narrative = (
                f"Możesz spokojnie wydać {amount_pln:.2f} PLN. "
                f"Masz {freely_available:.2f} PLN swobodnych środków po uwzględnieniu "
                f"nadchodzących zobowiązań ({upcoming_30d:.2f} PLN) i celów finansowych ({goal_allocations_pln:.2f} PLN)."
            )
        elif amount_pln <= available_this_month:
            verdict = "yellow"
            narrative = (
                f"Technicznie możesz wydać {amount_pln:.2f} PLN, ale naruszysz bufor bezpieczeństwa. "
                f"Masz {available_this_month:.2f} PLN dostępnych w tym miesiącu, ale nadchodzące zobowiązania "
                f"({upcoming_30d:.2f} PLN) i cele ({goal_allocations_pln:.2f} PLN) ograniczają swobodne {freely_available:.2f} PLN."
            )
        else:
            verdict = "red"
            narrative = (
                f"Nie stać Cię na {amount_pln:.2f} PLN w tym miesiącu. "
                f"Dostępne środki to {available_this_month:.2f} PLN (dochód {income:.2f} PLN minus wydatki {expenses:.2f} PLN)."
            )

        if financial_focus_label:
            narrative += f" Pamiętaj o priorytecie: {financial_focus_label}."

        return AffordabilityCheckResponse(
            verdict=verdict,
            amount_pln=amount_pln,
            available_this_month_pln=available_this_month,
            upcoming_obligations_30d_pln=upcoming_30d,
            active_goal_allocations_pln=goal_allocations_pln,
            freely_available_pln=freely_available,
            financial_focus_label=financial_focus_label,
            narrative=narrative,
        )

    # ------------------------------------------------------------------
    # Emergency advisor
    # ------------------------------------------------------------------

    def get_emergency_advice(
        self,
        amount_pln: float,
        active_goals: list[dict],
    ) -> EmergencyAdvisorResponse:
        averages = self.repo.get_discretionary_category_averages()

        cuts = []
        total_cuttable = 0.0
        for avg in averages:
            avg_spend = float(avg["avg_monthly_spend_pln"])
            months_to_cover = amount_pln / avg_spend if avg_spend > 0 else float("inf")
            cuts.append(
                EmergencyReductionOption(
                    category_name=avg["category_name"],
                    classification="discretionary",
                    avg_monthly_spend_pln=avg_spend,
                    suggested_cut_pln=avg_spend,
                    months_to_cover=round(months_to_cover, 1),
                )
            )
            total_cuttable += avg_spend

        fully_coverable = total_cuttable >= amount_pln

        goal_impacts = []
        for goal in active_goals:
            alloc = float(goal.get("monthly_allocation_amount", 0))
            if alloc <= 0:
                continue
            months_pause = math.ceil(amount_pln / alloc) if alloc > 0 else 0
            goal_impacts.append(
                EmergencyGoalImpact(
                    goal_id=goal["id"],
                    goal_name=goal["name"],
                    monthly_allocation_pln=alloc,
                    impact_description=(
                        f"Wstrzymanie alokacji {alloc:.2f} PLN/mies. przez {months_pause} mies. "
                        f"pokryłoby wydatek. Cel zostanie opóźniony o {months_pause} mies."
                    ),
                )
            )

        recovery_months = (
            math.ceil(amount_pln / total_cuttable) if total_cuttable > 0 else None
        )

        if fully_coverable:
            narrative = (
                f"Kwotę {amount_pln:.2f} PLN możesz pokryć przez ograniczenie wydatków uznaniowych. "
                f"Łącznie masz {total_cuttable:.2f} PLN/mies. w kategoriach uznaniowych. "
                f"Potrzeba około {recovery_months} {'miesiąca' if recovery_months == 1 else 'miesięcy'} oszczędzania."
            )
        else:
            narrative = (
                f"Wydatki uznaniowe ({total_cuttable:.2f} PLN/mies.) nie pokrywają w pełni {amount_pln:.2f} PLN. "
                f"Rozważ wstrzymanie celów finansowych lub rozłożenie wydatku na raty."
            )

        return EmergencyAdvisorResponse(
            amount_pln=amount_pln,
            fully_coverable_by_cuts=fully_coverable,
            discretionary_cuts=cuts,
            total_cuttable_pln=total_cuttable,
            goal_impacts=goal_impacts,
            recovery_months=recovery_months,
            narrative=narrative,
        )
