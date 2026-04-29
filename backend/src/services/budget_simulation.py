"""
Service for budget simulations and AI recommendations.
"""
from __future__ import annotations

import datetime
import json
import math
import os
from typing import Optional

from openai import OpenAI

from ..data import (
    SimulationResultPayload,
    SimulationMonthlyPoint,
    SimulationGoalImpact,
    SimulationSuggestion,
    SimulationNarrative,
    AIRecommendationsResponse,
    AIInsightItem,
    AIRecommendationsPayload,
)
from ..repositories.budget_analysis import BudgetAnalysisRepository
from ..repositories.budget_simulations import BudgetSimulationsRepository


class BudgetSimulationService:
    def __init__(
        self,
        budget_analysis_repo: BudgetAnalysisRepository,
        budget_simulations_repo: BudgetSimulationsRepository,
        openai_client: Optional[OpenAI] = None,
    ):
        self.analysis_repo = budget_analysis_repo
        self.simulations_repo = budget_simulations_repo
        self.openai_client = openai_client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def dispose(self):
        pass

    # ------------------------------------------------------------------
    # Simulation projection
    # ------------------------------------------------------------------

    def run_projection(self, simulation_row: dict) -> SimulationResultPayload:
        rolling = self.analysis_repo.get_rolling_3month_averages()
        baseline_income = rolling["avg_income"]
        baseline_expenses = rolling["avg_expenses"]
        baseline_surplus = baseline_income - baseline_expenses

        expense_amount = float(simulation_row["expense_amount"])
        expense_type = simulation_row["expense_type"]
        start_date_str = simulation_row.get("expense_start_date", "")
        try:
            if isinstance(start_date_str, datetime.date):
                start_date = start_date_str
            else:
                start_date = datetime.date.fromisoformat(str(start_date_str))
        except Exception:
            start_date = datetime.date.today()

        horizon = 12 if expense_type == "one_time" else 24

        today = datetime.date.today()
        projection: list[SimulationMonthlyPoint] = []

        for i in range(horizon):
            month_offset = i
            proj_year = today.year + (today.month - 1 + month_offset) // 12
            proj_month = (today.month - 1 + month_offset) % 12 + 1
            proj_date = datetime.date(proj_year, proj_month, 1)
            month_str = proj_date.strftime("%Y-%m")

            simulated_expenses = baseline_expenses
            if expense_type == "one_time":
                if proj_year == start_date.year and proj_month == start_date.month:
                    simulated_expenses += expense_amount
            elif expense_type == "recurring":
                if proj_date >= datetime.date(start_date.year, start_date.month, 1):
                    simulated_expenses += expense_amount

            simulated_surplus = baseline_income - simulated_expenses

            projection.append(
                SimulationMonthlyPoint(
                    month=month_str,
                    baseline_surplus_pln=round(baseline_surplus, 2),
                    simulated_surplus_pln=round(simulated_surplus, 2),
                )
            )

        goal_impacts: list[SimulationGoalImpact] = []

        ai_summary, ai_implications, ai_suggestions = self._generate_narrative(
            projection, goal_impacts, simulation_row
        )

        return SimulationResultPayload(
            projection=projection,
            goal_impacts=goal_impacts,
            ai_summary=ai_summary,
            ai_implications=ai_implications,
            ai_suggestions=ai_suggestions,
        )

    def _generate_narrative(
        self,
        projection: list[SimulationMonthlyPoint],
        goal_impacts: list[SimulationGoalImpact],
        simulation_row: dict,
    ) -> tuple[str, str, list[SimulationSuggestion]]:
        tool_name = "generate_simulation_narrative"
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "Generate a Polish narrative for a budget simulation",
                    "parameters": SimulationNarrative.model_json_schema(),
                },
            }
        ]

        projection_data = [p.model_dump() for p in projection[:6]]
        goal_data = [g.model_dump() for g in goal_impacts]

        prompt = (
            f"Jesteś doradcą finansowym. Przeanalizuj symulację budżetową i napisz krótkie podsumowanie po polsku.\n\n"
            f"Wydatek: {simulation_row.get('expense_name', '')} — {simulation_row.get('expense_amount', 0)} PLN "
            f"({'jednorazowy' if simulation_row.get('expense_type') == 'one_time' else 'cykliczny'})\n\n"
            f"Projekcja nadwyżki (pierwsze 6 miesięcy): {json.dumps(projection_data, ensure_ascii=False)}\n\n"
            f"Wpływ na cele: {json.dumps(goal_data, ensure_ascii=False)}\n\n"
            f"Napisz: 1) krótkie podsumowanie (summary), 2) implikacje (implications), "
            f"3) 2-3 sugestie oszczędnościowe z kwotami PLN (suggestions)."
        )

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                tools=tools,
                tool_choice={"type": "function", "function": {"name": tool_name}},
                messages=[{"role": "user", "content": prompt}],
            )
            tool_call = response.choices[0].message.tool_calls
            if tool_call:
                args = json.loads(tool_call[0].function.arguments)
                narrative = SimulationNarrative(**args)
                return narrative.summary, narrative.implications, narrative.suggestions
        except Exception as e:
            print(f"BudgetSimulationService._generate_narrative error: {e}")

        fallback_summary = (
            f"Wydatek {simulation_row.get('expense_name', '')} wpłynie na Twój budżet. "
            f"Przeanalizuj szczegółowe dane projekcji poniżej."
        )
        return fallback_summary, "Sprawdź szczegóły projekcji.", []

    # ------------------------------------------------------------------
    # Context helpers for AI recommendations
    # ------------------------------------------------------------------

    def _count_months_of_data(self) -> int:
        return self.analysis_repo.count_distinct_months()

    def _build_context_summary(self) -> dict:
        history = self.analysis_repo.get_monthly_history(3)
        focus = self.analysis_repo.get_financial_focus()

        return {
            "monthly_history": history,
            "active_goals": [],
            "financial_focus": focus["label"] if focus else None,
        }

    def generate_ai_recommendations(self) -> AIRecommendationsResponse:
        months_of_data = self._count_months_of_data()

        if months_of_data < 3:
            return AIRecommendationsResponse(
                insights=[],
                generated_at=None,
                data_through_date=None,
                months_of_data=months_of_data,
                has_sufficient_data=False,
            )

        context = self._build_context_summary()
        tool_name = "generate_ai_recommendations"
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "Generate AI budget recommendations in Polish",
                    "parameters": AIRecommendationsPayload.model_json_schema(),
                },
            }
        ]

        prompt = (
            f"Jesteś doradcą finansowym. Na podstawie poniższych danych wygeneruj 3-5 konkretnych rekomendacji "
            f"finansowych po polsku z konkretnymi kwotami PLN.\n\n"
            f"Dane: {json.dumps(context, ensure_ascii=False, default=str)}\n\n"
            f"Typy rekomendacji: saving_opportunity, goal_advice, warning, general"
        )

        insights = []
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                tools=tools,
                tool_choice={"type": "function", "function": {"name": tool_name}},
                messages=[{"role": "user", "content": prompt}],
            )
            tool_call = response.choices[0].message.tool_calls
            if tool_call:
                args = json.loads(tool_call[0].function.arguments)
                payload = AIRecommendationsPayload(**args)
                insights = payload.insights
        except Exception as e:
            print(f"BudgetSimulationService.generate_ai_recommendations error: {e}")

        today = datetime.date.today()
        insights_dicts = [i.model_dump() for i in insights]
        self.simulations_repo.save_recommendations(
            insights_json=insights_dicts,
            data_through_date=today.isoformat(),
            months_of_data=months_of_data,
        )

        return AIRecommendationsResponse(
            insights=insights,
            generated_at=datetime.datetime.now().isoformat(),
            data_through_date=today.isoformat(),
            months_of_data=months_of_data,
            has_sufficient_data=True,
        )

    def get_ai_recommendations_from_db(self) -> AIRecommendationsResponse:
        row = self.simulations_repo.get_current_recommendations()
        months_of_data = self._count_months_of_data()

        if row is None:
            return AIRecommendationsResponse(
                insights=[],
                generated_at=None,
                data_through_date=None,
                months_of_data=months_of_data,
                has_sufficient_data=months_of_data >= 3,
            )

        insights_raw = row.get("recommendations_json", [])
        insights = []
        for item in (insights_raw if isinstance(insights_raw, list) else []):
            try:
                insights.append(AIInsightItem(**item))
            except Exception:
                pass

        return AIRecommendationsResponse(
            insights=insights,
            generated_at=row.get("generated_at"),
            data_through_date=row.get("data_through_date"),
            months_of_data=row.get("months_of_data", months_of_data),
            has_sufficient_data=row.get("months_of_data", 0) >= 3,
        )
