"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { formatAmount } from "@/components/ui";

interface MonthlySummary {
  year: number;
  month: number;
  income_pln: number;
  expenses_pln: number;
  surplus_pln: number;
}

interface Props {
  months: MonthlySummary[];
}

const MONTH_NAMES = [
  "", "Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
  "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru",
];

export function TrendLineChart({ months }: Props) {
  if (months.length === 0) {
    return (
      <div className="flex items-center justify-center h-36 text-gray-400 text-sm">
        Brak historycznych danych do wyświetlenia trendu
      </div>
    );
  }

  const data = [...months].reverse().map((m) => ({
    label: `${MONTH_NAMES[m.month]} ${m.year}`,
    Dochody: m.income_pln,
    Wydatki: m.expenses_pln,
    Nadwyżka: m.surplus_pln,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6b7280" }} />
        <YAxis
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          tick={{ fontSize: 11, fill: "#6b7280" }}
        />
        <Tooltip formatter={(value: number | string | undefined) => formatAmount(Number(value ?? 0))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="Dochody"
          stroke="#22c55e"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="Wydatki"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="Nadwyżka"
          stroke="#635bff"
          strokeWidth={2}
          dot={false}
          strokeDasharray="4 4"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
