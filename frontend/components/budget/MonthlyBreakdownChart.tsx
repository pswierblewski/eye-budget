"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { BudgetCategoryMonthlyItem } from "@/lib/types";
import { formatAmount } from "@/components/ui";
import clsx from "clsx";

interface Props {
  categories: BudgetCategoryMonthlyItem[];
}

function MoMBadge({ pct }: { pct: number }) {
  const up = pct > 0;
  const zero = pct === 0;
  return (
    <span
      className={clsx(
        "text-xs font-medium px-1.5 py-0.5 rounded",
        zero
          ? "text-gray-400 bg-gray-100"
          : up
          ? "text-red-600 bg-red-50"
          : "text-green-600 bg-green-50"
      )}
    >
      {up ? "+" : ""}
      {pct.toFixed(1)}%
    </span>
  );
}

const ESSENTIAL_COLOR = "#635bff";
const DISCRETIONARY_COLOR = "#f59e0b";

export function MonthlyBreakdownChart({ categories }: Props) {
  if (categories.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Brak danych dla wybranego miesiąca
      </div>
    );
  }

  const chartData = categories.slice(0, 12).map((c) => ({
    name: c.category_name.length > 14 ? c.category_name.slice(0, 12) + "…" : c.category_name,
    fullName: c.category_name,
    total: c.total_pln,
    classification: c.classification,
    change_pct: c.change_pct,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 40 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            angle={-35}
            textAnchor="end"
            interval={0}
          />
          <YAxis
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
            tick={{ fontSize: 11, fill: "#6b7280" }}
          />
          <Tooltip
            formatter={(value: number | string | undefined) => [
              formatAmount(Number(value ?? 0)),
              "",
            ]}
          />
          <Bar dataKey="total" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, idx) => (
              <Cell
                key={idx}
                fill={
                  entry.classification === "essential"
                    ? ESSENTIAL_COLOR
                    : DISCRETIONARY_COLOR
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-1 justify-center text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: ESSENTIAL_COLOR }} />
          Niezbędne
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm inline-block" style={{ background: DISCRETIONARY_COLOR }} />
          Uznaniowe
        </span>
      </div>
      <div className="mt-3 space-y-1 max-h-40 overflow-y-auto">
        {categories.map((c) => (
          <div key={c.category_name} className="flex items-center justify-between text-xs px-1">
            <span className="text-gray-600 truncate max-w-[180px]">{c.category_name}</span>
            <div className="flex items-center gap-2">
              <span className="font-medium">{formatAmount(c.total_pln)}</span>
              <MoMBadge pct={c.change_pct} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
