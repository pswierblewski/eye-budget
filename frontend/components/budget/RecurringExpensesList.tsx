"use client";

import { RecurringExpenseItem } from "@/lib/types";
import { Card, Amount, CountBadge } from "@/components/ui";

interface Props {
  expenses: RecurringExpenseItem[];
}

const FREQ_LABEL: Record<string, string> = {
  monthly: "Miesięczny",
  annual: "Roczny",
};

export function RecurringExpensesList({ expenses }: Props) {
  if (expenses.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4">
        Brak wykrytych cyklicznych wydatków. Dodaj więcej transakcji.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {expenses.map((exp, i) => (
        <div
          key={i}
          className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-gray-800 truncate">
                {exp.vendor_name}
              </span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  exp.frequency === "monthly"
                    ? "bg-blue-50 text-blue-600"
                    : "bg-purple-50 text-purple-600"
                }`}
              >
                {FREQ_LABEL[exp.frequency] ?? exp.frequency}
              </span>
            </div>
            {exp.category_name && (
              <p className="text-xs text-gray-400 mt-0.5">{exp.category_name}</p>
            )}
          </div>
          <div className="text-right ml-4 shrink-0">
            <Amount value={exp.avg_amount_pln} className="text-sm font-medium text-gray-800" />
            <p className="text-xs text-gray-400 mt-0.5">
              następny: {exp.next_expected_date}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
