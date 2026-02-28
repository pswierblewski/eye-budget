"use client";

import { useQuery } from "@tanstack/react-query";
import { getEvaluation } from "@/lib/api";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";
import { z } from "zod";
import { EvaluationResultSchema } from "@/lib/types";

type EvaluationResult = z.infer<typeof EvaluationResultSchema>;
type ResultRow = EvaluationResult & { id: number };

function pct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function num(v: number | null | undefined, decimals = 2) {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function boolCell(v: boolean | null | undefined, trueIcon = "✓", falseIcon = "—") {
  if (v == null) return <span className="text-gray-300">—</span>;
  return v
    ? <span className="text-green-600">{trueIcon}</span>
    : <span className="text-red-500">{falseIcon}</span>;
}

export default function EvaluationDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const runId = Number(params.id);

  const { data: run, isLoading } = useQuery({
    queryKey: ["evaluation", runId],
    queryFn: () => getEvaluation(runId),
  });

  if (isLoading) {
    return (
      <div className="text-sm text-gray-400 py-16 text-center">Ładowanie…</div>
    );
  }
  if (!run) {
    return (
      <div className="text-sm text-red-500 py-16 text-center">
        Nie znaleziono ewaluacji.{" "}
        <Link href="/evaluations" className="underline">
          Wróć
        </Link>
      </div>
    );
  }

  const resultsWithId: ResultRow[] = run.results.map((r, i) => ({ ...r, id: i }));

  const hasGtMetrics = run.results.some(
    (r) => r.metrics?.vendor_correct != null || r.metrics?.products_accuracy != null
  );

  const summaryCards = [
    { label: "Pliki", value: run.total_files },
    { label: "Udane", value: run.successful },
    { label: "Błędy", value: run.failed },
    { label: "Trafność", value: pct(run.success_rate) },
    { label: "Śr. kompletność", value: pct(run.avg_field_completeness) },
    { label: "Śr. spójność", value: pct(run.avg_consistency_rate) },
    { label: "Śr. czas (ms)", value: run.avg_processing_time_ms != null ? Math.round(run.avg_processing_time_ms) : "—" },
  ];

  const columns: Column<ResultRow>[] = [
    {
      header: "Plik",
      accessor: (r) => (
        <span className="font-mono text-xs text-gray-700 max-w-[180px] block truncate" title={r.filename}>
          {r.filename}
        </span>
      ),
      sortValue: (r) => r.filename,
    },
    {
      header: "Status",
      accessor: (r) => (
        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${r.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
          {r.success ? "OK" : "Błąd"}
        </span>
      ),
      sortValue: (r) => (r.success ? 1 : 0),
    },
    {
      header: "Czas (ms)",
      accessor: (r) => r.metrics?.processing_time_ms ?? "—",
      className: "text-right",
      sortValue: (r) => r.metrics?.processing_time_ms ?? -1,
    },
    {
      header: "Pola",
      accessor: (r) => r.metrics?.fields_extracted ?? "—",
      className: "text-right",
      sortValue: (r) => r.metrics?.fields_extracted ?? -1,
    },
    {
      header: "Kompletność",
      accessor: (r) => pct(r.metrics?.field_completeness),
      className: "text-right",
      sortValue: (r) => r.metrics?.field_completeness ?? -1,
    },
    {
      header: "Produkty",
      accessor: (r) => r.metrics?.product_count ?? "—",
      className: "text-right",
      sortValue: (r) => r.metrics?.product_count ?? -1,
    },
    {
      header: "Sklep",
      accessor: (r) => boolCell(r.metrics?.has_vendor),
      sortValue: (r) => (r.metrics?.has_vendor ? 1 : 0),
    },
    {
      header: "Data",
      accessor: (r) => boolCell(r.metrics?.has_date),
      sortValue: (r) => (r.metrics?.has_date ? 1 : 0),
    },
    {
      header: "Suma",
      accessor: (r) => boolCell(r.metrics?.has_total),
      sortValue: (r) => (r.metrics?.has_total ? 1 : 0),
    },
    {
      header: "Suma prod.",
      accessor: (r) => num(r.metrics?.products_sum),
      className: "text-right",
      sortValue: (r) => r.metrics?.products_sum ?? -1,
    },
    {
      header: "Suma OCR",
      accessor: (r) => num(r.metrics?.extracted_total),
      className: "text-right",
      sortValue: (r) => r.metrics?.extracted_total ?? -1,
    },
    {
      header: "Δ Suma",
      accessor: (r) => num(r.metrics?.total_difference),
      className: "text-right",
      sortValue: (r) => r.metrics?.total_difference ?? -1,
    },
    {
      header: "Spójny",
      accessor: (r) => boolCell(r.metrics?.is_consistent, "✓", "✗"),
      sortValue: (r) => (r.metrics?.is_consistent ? 1 : 0),
    },
    ...(hasGtMetrics
      ? [
          {
            header: "Sklep ✓",
            accessor: (r: ResultRow) => boolCell(r.metrics?.vendor_correct, "✓", "✗"),
            sortValue: (r: ResultRow) => (r.metrics?.vendor_correct ? 1 : 0),
          },
          {
            header: "Data ✓",
            accessor: (r: ResultRow) => boolCell(r.metrics?.date_correct, "✓", "✗"),
            sortValue: (r: ResultRow) => (r.metrics?.date_correct ? 1 : 0),
          },
          {
            header: "Dokł. sumy",
            accessor: (r: ResultRow) => pct(r.metrics?.total_accuracy),
            className: "text-right",
            sortValue: (r: ResultRow) => r.metrics?.total_accuracy ?? -1,
          },
          {
            header: "Dokł. prod.",
            accessor: (r: ResultRow) => pct(r.metrics?.products_accuracy),
            className: "text-right",
            sortValue: (r: ResultRow) => r.metrics?.products_accuracy ?? -1,
          },
        ]
      : []),
    {
      header: "Błąd",
      accessor: (r) => (
        <span className="text-red-500 text-xs max-w-[200px] block truncate" title={r.error_message ?? ""}>
          {r.error_message ?? ""}
        </span>
      ),
      sortValue: (r) => r.error_message ?? "",
    },
  ];

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center gap-4">
        <Link href="/evaluations" className="text-sm text-gray-500 hover:text-gray-700">
          ← Ewaluacje
        </Link>
        <h1 className="text-xl font-bold text-gray-900">
          Run #{run.id} — {run.model_used}
        </h1>
        <span className="text-sm text-gray-400">
          {new Date(run.run_timestamp).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-3 lg:grid-cols-7 shrink-0">
        {summaryCards.map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-3">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
            <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
          </div>
        ))}
      </div>

      {run.config && Object.keys(run.config).length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-[#f6f9fc] px-4 py-3 shrink-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Konfiguracja</p>
          <dl className="flex flex-wrap gap-x-6 gap-y-1">
            {Object.entries(run.config).map(([k, v]) => (
              <div key={k} className="flex items-center gap-1.5 text-sm">
                <dt className="text-gray-500 font-medium">{k}:</dt>
                <dd className="text-gray-800 font-mono">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="flex flex-col flex-1 min-h-0 gap-2">
        <h2 className="text-base font-semibold text-gray-900 shrink-0">Wyniki per plik</h2>
        <DataTable
          columns={columns}
          rows={resultsWithId}
          emptyMessage="Brak wyników."
          className="flex-1 min-h-0"
        />
      </div>
    </div>
  );
}
