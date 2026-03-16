"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getBudgetMonthly,
  getBudgetCyclicalAlerts,
  getBudgetRecurringExpenses,
  getFinancialFocus,
} from "@/lib/api";
import {
  PageHeader,
  SectionLabel,
  Card,
  PrevNextNav,
} from "@/components/ui";
import { MonthlyBreakdownChart } from "@/components/budget/MonthlyBreakdownChart";
import { TrendLineChart } from "@/components/budget/TrendLineChart";
import { CyclicalAlertBanner } from "@/components/budget/CyclicalAlertBanner";
import { RecurringExpensesList } from "@/components/budget/RecurringExpensesList";
import { AffordabilityChecker } from "@/components/budget/AffordabilityChecker";
import { EmergencyAdvisorPanel } from "@/components/budget/EmergencyAdvisorPanel";
import { Amount } from "@/components/ui";

function getCurrentYearMonth() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

const MONTH_NAMES = [
  "", "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
  "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
];

export default function BudgetPage() {
  const { year: currentYear, month: currentMonth } = getCurrentYearMonth();
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);

  const { data: monthly, isLoading: loadingMonthly } = useQuery({
    queryKey: ["budget-monthly", year, month],
    queryFn: () => getBudgetMonthly(year, month),
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["budget-cyclical-alerts"],
    queryFn: getBudgetCyclicalAlerts,
  });

  const { data: recurring = [], isLoading: loadingRecurring } = useQuery({
    queryKey: ["budget-recurring-expenses"],
    queryFn: getBudgetRecurringExpenses,
  });

  const { data: focus } = useQuery({
    queryKey: ["financial-focus"],
    queryFn: getFinancialFocus,
  });

  function prevMonth() {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else {
      setMonth((m) => m + 1);
    }
  }

  const trendMonths = monthly
    ? [
        {
          year,
          month,
          income_pln: monthly.total_income_pln,
          expenses_pln: monthly.total_expenses_pln,
          surplus_pln: monthly.surplus_pln,
        },
      ]
    : [];

  return (
    <div className="max-w-4xl mx-auto w-full space-y-6">
      <PageHeader title="Analiza budżetu" />

      {focus?.id != null && focus.label && (
        <div className="text-xs text-[#635bff] font-medium">
          Priorytet finansowy: {focus.label}
          {focus.description && (
            <span className="text-gray-400 ml-2">— {focus.description}</span>
          )}
        </div>
      )}

      {alerts.length > 0 && <CyclicalAlertBanner alerts={alerts} />}

      {/* Month selector */}
      <div className="flex items-center gap-4">
        <PrevNextNav onPrev={prevMonth} onNext={nextMonth} hasPrev={true} hasNext={true} />
        <span className="text-sm font-semibold text-gray-700">
          {MONTH_NAMES[month]} {year}
        </span>
      </div>

      {/* Summary cards */}
      {loadingMonthly ? (
        <div className="text-sm text-gray-400">Ładowanie danych…</div>
      ) : monthly ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-xs text-gray-400 mb-1">Dochody</p>
              <Amount value={monthly.total_income_pln} className="text-lg font-bold text-green-600" />
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-xs text-gray-400 mb-1">Wydatki</p>
              <Amount value={monthly.total_expenses_pln} className="text-lg font-bold text-red-500" />
              <p className="text-xs text-gray-400 mt-1">
                {monthly.month_over_month_change_pct > 0 ? "+" : ""}
                {monthly.month_over_month_change_pct.toFixed(1)}% vs poprzedni miesiąc
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-xs text-gray-400 mb-1">Nadwyżka</p>
              <Amount
                value={monthly.surplus_pln}
                className={`text-lg font-bold ${monthly.surplus_pln >= 0 ? "text-[#635bff]" : "text-red-500"}`}
              />
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 p-5">
            <SectionLabel>Wydatki według kategorii</SectionLabel>
            <MonthlyBreakdownChart categories={monthly.categories} />
          </div>

          <div className="rounded-lg border border-gray-200 p-5">
            <SectionLabel>Trend miesięczny</SectionLabel>
            <TrendLineChart months={trendMonths} />
          </div>
        </>
      ) : (
        <div className="text-sm text-gray-400">Brak danych dla wybranego miesiąca.</div>
      )}

      {/* Recurring expenses */}
      <div className="rounded-lg border border-gray-200 p-5">
        <SectionLabel>Cykliczne wydatki</SectionLabel>
        {loadingRecurring ? (
          <p className="text-sm text-gray-400">Ładowanie…</p>
        ) : (
          <RecurringExpensesList expenses={recurring} />
        )}
      </div>

      {/* Affordability checker */}
      <div className="rounded-lg border border-gray-200 p-5">
        <SectionLabel>Czy mnie stać?</SectionLabel>
        <AffordabilityChecker />
      </div>

      {/* Emergency advisor */}
      <div className="rounded-lg border border-gray-200 p-5">
        <SectionLabel>Nieoczekiwany wydatek</SectionLabel>
        <EmergencyAdvisorPanel />
      </div>
    </div>
  );
}
