"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { ChevronDown, ChevronUp, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { AnalyticsSummary } from "@/lib/types";

// ─── colour palette for the pie chart ──────────────────────────────
const PIE_COLORS = [
  "#635bff", "#36b9cc", "#f6c23e", "#e74a3b", "#1cc88a",
  "#858796", "#5a5c69", "#f8f9fc", "#4e73df", "#2e59d9",
];

function fmt(n: number): string {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function shortFmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toFixed(0);
}

// ─── Custom Tooltip for BarChart ─────────────────────────────────────
function BarTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
      <p className="mb-1 font-semibold text-gray-700">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {fmt(p.value)} PLN
        </p>
      ))}
    </div>
  );
}

export function AnalyticsPanel({
  data,
  isLoading,
}: {
  data: AnalyticsSummary | undefined;
  isLoading: boolean;
}) {
  const [expanded, setExpanded] = useState(true);
  const [showExtra, setShowExtra] = useState(false);

  const mom = data?.month_over_month;
  const changePct = mom?.change_pct ?? 0;
  const MomIcon =
    changePct > 0 ? TrendingUp : changePct < 0 ? TrendingDown : Minus;
  const momColor =
    changePct > 0
      ? "text-red-500"
      : changePct < 0
      ? "text-green-600"
      : "text-gray-500";

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <span className="font-semibold text-gray-700 text-sm">Podsumowanie wydatków</span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-6 pb-6 space-y-6">
          {isLoading ? (
            <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
              Ładowanie danych…
            </div>
          ) : (
            <>
              {/* ── KPI row ──────────────────────────────────────────── */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard
                  label="Wydatki (zakres)"
                  value={`${fmt(data?.total_expense ?? 0)} PLN`}
                  color="text-red-600"
                />
                <KpiCard
                  label="Przychody (zakres)"
                  value={`${fmt(data?.total_income ?? 0)} PLN`}
                  color="text-green-600"
                />
                <KpiCard
                  label="Wydatki ten miesiąc"
                  value={`${fmt(mom?.current ?? 0)} PLN`}
                  color="text-gray-900"
                />
                {/* Month-over-month card */}
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 flex flex-col gap-1">
                  <span className="text-xs font-medium text-gray-500">Zmiana m/m</span>
                  <div className={`flex items-center gap-1 ${momColor}`}>
                    <MomIcon className="h-5 w-5" />
                    <span className="text-2xl font-bold">
                      {changePct > 0 ? "+" : ""}
                      {changePct.toFixed(1)}%
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">
                    poprz. miesiąc: {fmt(mom?.previous ?? 0)} PLN
                  </span>
                </div>
              </div>

              {/* ── Charts row ───────────────────────────────────────── */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Bar chart – monthly income / expense */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">
                    Wydatki vs przychody miesięcznie
                  </p>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart
                      data={data?.monthly_totals ?? []}
                      margin={{ top: 4, right: 8, left: 0, bottom: 4 }}
                      barCategoryGap="30%"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis
                        dataKey="month"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v) => v.slice(5)} // show only MM
                      />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={shortFmt}
                        width={45}
                      />
                      <Tooltip content={<BarTooltip />} />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        wrapperStyle={{ fontSize: 12 }}
                      />
                      <Bar
                        dataKey="expense"
                        name="Wydatki"
                        fill="#e74a3b"
                        radius={[3, 3, 0, 0]}
                      />
                      <Bar
                        dataKey="income"
                        name="Przychody"
                        fill="#1cc88a"
                        radius={[3, 3, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Pie chart – by category group */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">
                    Wydatki wg grupy kategorii
                  </p>
                  {(data?.by_category_group?.length ?? 0) === 0 ? (
                    <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">
                      Brak danych
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie
                          data={data?.by_category_group}
                          dataKey="total"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          label={({ name, percent }: { name?: string; percent?: number }) =>
                            (percent ?? 0) > 0.04
                              ? `${((name ?? "").length > 14 ? (name ?? "").slice(0, 13) + "…" : (name ?? ""))} ${((percent ?? 0) * 100).toFixed(0)}%`
                              : ""
                          }
                          labelLine={false}
                        >
                          {data?.by_category_group.map((_, i) => (
                            <Cell
                              key={i}
                              fill={PIE_COLORS[i % PIE_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(v: number | undefined) => [`${fmt(v ?? 0)} PLN`, "Wydatki"]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>

              {/* ── Extra charts toggle ────────────────────────────── */}
              <div>
                <button
                  onClick={() => setShowExtra((v) => !v)}
                  className="text-xs text-[#635bff] hover:underline flex items-center gap-1"
                >
                  {showExtra ? (
                    <>
                      <ChevronUp className="h-3 w-3" /> Ukryj szczegóły
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3 w-3" /> Top sklepy i
                      kategorie
                    </>
                  )}
                </button>

                {showExtra && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                    {/* Vendor top-10 */}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">
                        Top 10 sklepów (wg wydatków)
                      </p>
                      <ResponsiveContainer width="100%" height={240}>
                        <BarChart
                          data={[...(data?.by_vendor ?? [])].reverse()}
                          layout="vertical"
                          margin={{ top: 4, right: 40, left: 4, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                          <XAxis
                            type="number"
                            tick={{ fontSize: 11 }}
                            tickFormatter={shortFmt}
                          />
                          <YAxis
                            type="category"
                            dataKey="vendor_name"
                            tick={{ fontSize: 11 }}
                            width={110}
                          />
                          <Tooltip
                            formatter={(v: number | undefined) => [`${fmt(v ?? 0)} PLN`, "Wydatki"]}
                          />
                          <Bar
                            dataKey="total"
                            name="Wydatki"
                            fill="#635bff"
                            radius={[0, 3, 3, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Category top-15 */}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">
                        Top 15 kategorii
                      </p>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                          data={[...(data?.by_category ?? [])].reverse()}
                          layout="vertical"
                          margin={{ top: 4, right: 40, left: 4, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                          <XAxis
                            type="number"
                            tick={{ fontSize: 11 }}
                            tickFormatter={shortFmt}
                          />
                          <YAxis
                            type="category"
                            dataKey="name"
                            tick={{ fontSize: 11 }}
                            width={130}
                          />
                          <Tooltip
                            formatter={(v: number | undefined) => [`${fmt(v ?? 0)} PLN`, "Wydatki"]}
                            labelFormatter={(label, payload) => {
                              const group = payload?.[0]?.payload?.group_name;
                              return group ? `${label} (${group})` : label;
                            }}
                          />
                          <Bar
                            dataKey="total"
                            name="Wydatki"
                            fill="#36b9cc"
                            radius={[0, 3, 3, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  color = "text-gray-900",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      <span className={`text-2xl font-bold ${color}`}>{value}</span>
    </div>
  );
}
