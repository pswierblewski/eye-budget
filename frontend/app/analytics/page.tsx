"use client";

import { useQuery } from "@tanstack/react-query";
import { getPromptAnalytics } from "@/lib/api";
import { PromptAnalyticsRow } from "@/lib/types";
import { PageHeader, Card } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";
import Link from "next/link";

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <Card className="p-5 flex flex-col gap-1">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </Card>
  );
}

function pct(count: number, total: number): string {
  if (total === 0) return "0%";
  return `${Math.round((count / total) * 100)}%`;
}

export default function PromptAnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["prompt-analytics"],
    queryFn: getPromptAnalytics,
    staleTime: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="p-8 text-sm text-gray-500">
        {isLoading ? "Ładowanie danych analitycznych..." : "Brak danych."}
      </div>
    );
  }

  const {
    total_receipts,
    total_category_corrections,
    total_product_name_corrections,
    receipts_with_product_count_mismatch,
    avg_category_corrections,
    avg_product_name_corrections,
    avg_ocr_product_count,
    top_category_confusions,
    top_product_name_corrections,
    recent,
  } = data;

  return (
    <div className="max-w-5xl mx-auto py-8 px-6 space-y-8">
      <PageHeader title="Analityka promptów AI" />

      {/* Summary cards */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Potwierdzonych paragonów" value={total_receipts} />
        <StatCard
          label="Poprawki kategorii"
          value={total_category_corrections}
          sub={`${pct(receipts_with_product_count_mismatch, total_receipts)} paragonów z błędną kategorią`}
        />
        <StatCard
          label="Poprawki nazw produktów"
          value={total_product_name_corrections}
          sub={`śr. ${avg_product_name_corrections.toFixed(1)} na paragon`}
        />
        <StatCard
          label="Niezgodna liczba produktów"
          value={receipts_with_product_count_mismatch}
          sub={`${pct(receipts_with_product_count_mismatch, total_receipts)} paragonów`}
        />
      </section>

      {/* Second row */}
      <section className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          label="Śr. poprawek kategorii / paragon"
          value={avg_category_corrections.toFixed(2)}
        />
        <StatCard
          label="Śr. poprawek nazw / paragon"
          value={avg_product_name_corrections.toFixed(2)}
        />
        <StatCard
          label="Śr. produktów OCR / paragon"
          value={avg_ocr_product_count.toFixed(1)}
        />
      </section>

      {/* Top category confusions */}
      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
          Najczęstsze pomyłki kategorii AI
        </h2>
        {top_category_confusions.length === 0 ? (
          <p className="text-sm text-gray-400">Brak danych.</p>
        ) : (
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">AI zaproponował</th>
                  <th className="px-4 py-2 text-left font-medium">Użytkownik wybrał</th>
                  <th className="px-4 py-2 text-right font-medium">Liczba</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {top_category_confusions.map((item, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-700">{item.ai_category_name}</td>
                    <td className="px-4 py-2 text-gray-900 font-medium">{item.user_category_name}</td>
                    <td className="px-4 py-2 text-right tabular-nums font-semibold text-[#635bff]">
                      {item.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Top product name corrections */}
      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
          Najczęstsze poprawki nazw produktów
        </h2>
        {top_product_name_corrections.length === 0 ? (
          <p className="text-sm text-gray-400">Brak danych.</p>
        ) : (
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">AI zaproponował</th>
                  <th className="px-4 py-2 text-left font-medium">Użytkownik zmienił na</th>
                  <th className="px-4 py-2 text-right font-medium">Liczba</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {top_product_name_corrections.map((item, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500 line-through">{item.ai_normalized_name}</td>
                    <td className="px-4 py-2 text-gray-900 font-medium">{item.user_normalized_name}</td>
                    <td className="px-4 py-2 text-right tabular-nums font-semibold text-[#635bff]">
                      {item.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Recent receipts */}
      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
          Ostatnie paragony
        </h2>
        {recent.length === 0 ? (
          <p className="text-sm text-gray-400">Brak danych.</p>
        ) : (
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Paragon</th>
                  <th className="px-4 py-2 text-left font-medium">Sprzedawca</th>
                  <th className="px-4 py-2 text-right font-medium">Poprawki kat.</th>
                  <th className="px-4 py-2 text-right font-medium">Poprawki nazw</th>
                  <th className="px-4 py-2 text-right font-medium">Prod. OCR</th>
                  <th className="px-4 py-2 text-right font-medium">Prod. końcowe</th>
                  <th className="px-4 py-2 text-right font-medium">Data</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recent.map((row: PromptAnalyticsRow) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <Link
                        href={`/receipts/${row.scan_id}`}
                        className="text-[#635bff] hover:underline font-medium"
                      >
                        #{row.scan_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-gray-700">{row.vendor_name ?? "—"}</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      <span
                        className={
                          row.category_corrections_count > 0
                            ? "text-orange-600 font-semibold"
                            : "text-gray-400"
                        }
                      >
                        {row.category_corrections_count}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      <span
                        className={
                          row.product_name_corrections_count > 0
                            ? "text-orange-600 font-semibold"
                            : "text-gray-400"
                        }
                      >
                        {row.product_name_corrections_count}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-gray-600">
                      {row.ocr_product_count}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      <span
                        className={
                          row.confirmed_product_count !== row.ocr_product_count
                            ? "text-orange-600 font-semibold"
                            : "text-gray-600"
                        }
                      >
                        {row.confirmed_product_count}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500 whitespace-nowrap">
                      {row.created_at ? isoToDisplay(row.created_at.slice(0, 10)) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
