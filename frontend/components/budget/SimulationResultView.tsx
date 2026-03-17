"use client";

import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { BudgetSimulationDetail } from "@/lib/types";
import { Amount, StatusBadge } from "@/components/ui";
import { formatAmount } from "@/components/ui";

interface Props {
  simulation: BudgetSimulationDetail;
}

export function SimulationResultView({ simulation }: Props) {
  const { status, result, error_message } = simulation;

  if (status === "pending" || status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
        <div className="animate-spin h-8 w-8 rounded-full border-2 border-[#635bff] border-t-transparent" />
        <p className="text-sm">Obliczamy symulację…</p>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <h3 className="font-semibold mb-1">Symulacja nie powiodła się</h3>
        <p className="text-sm">{error_message ?? "Nieznany błąd."}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-gray-400 text-sm py-8 text-center">
        Brak wyników symulacji.
      </div>
    );
  }

  const chartData = result.projection.map((p) => ({
    month: p.month,
    "Baseline nadwyżka": p.baseline_surplus_pln,
    "Symulowana nadwyżka": p.simulated_surplus_pln,
  }));

  return (
    <div className="space-y-6">
      {/* Projection chart */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Projekcja nadwyżki</h3>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
            <XAxis
              dataKey="month"
              tick={{ fontSize: 10, fill: "#6b7280" }}
              interval={Math.floor(chartData.length / 6)}
            />
            <YAxis
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 10, fill: "#6b7280" }}
            />
            <Tooltip formatter={(v: number | string | undefined) => formatAmount(Number(v ?? 0))} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="Baseline nadwyżka"
              stroke="#635bff"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="Symulowana nadwyżka"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              strokeDasharray="4 4"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Goal impacts */}
      {result.goal_impacts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Wpływ na cele finansowe</h3>
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2 text-gray-500">Cel</th>
                  <th className="text-left px-3 py-2 text-gray-500">Baseline</th>
                  <th className="text-left px-3 py-2 text-gray-500">Symulowany</th>
                  <th className="text-right px-3 py-2 text-gray-500">Opóźnienie</th>
                </tr>
              </thead>
              <tbody>
                {result.goal_impacts.map((gi) => (
                  <tr key={gi.goal_id} className="border-t border-gray-100">
                    <td className="px-3 py-2 font-medium text-gray-700">{gi.goal_name}</td>
                    <td className="px-3 py-2 text-gray-500">{gi.baseline_completion_date ?? "—"}</td>
                    <td className="px-3 py-2 text-gray-500">{gi.simulated_completion_date ?? "—"}</td>
                    <td className="px-3 py-2 text-right">
                      {gi.delay_months > 0 ? (
                        <span className="text-red-600 font-medium">+{gi.delay_months} mies.</span>
                      ) : (
                        <span className="text-green-600">bez zmian</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI narrative */}
      <div className="space-y-3">
        <div className="rounded-lg bg-purple-50 border border-purple-100 p-4">
          <p className="text-xs font-semibold text-purple-700 mb-1">Podsumowanie AI</p>
          <p className="text-sm text-purple-900">{result.ai_summary}</p>
        </div>
        {result.ai_implications && (
          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
            <p className="text-xs font-semibold text-blue-700 mb-1">Implikacje</p>
            <p className="text-sm text-blue-900">{result.ai_implications}</p>
          </div>
        )}
        {result.ai_suggestions.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-600 mb-2">Sugestie</p>
            <div className="space-y-2">
              {result.ai_suggestions.map((s, i) => (
                <div key={i} className="flex items-start gap-3 text-sm border-l-2 border-[#635bff]/30 pl-3">
                  <div className="flex-1">
                    <p className="text-gray-800">{s.description}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {formatAmount(s.monthly_saving_pln)}/mies. · {s.months_required} mies.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
