"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listReceipts, processReceipts } from "@/lib/api";
import { ReceiptScanListItem } from "@/lib/types";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { getPusher } from "@/lib/pusher";
import Link from "next/link";

const STATUS_FILTERS = [
  "all",
  "pending",
  "processing",
  "to_confirm",
  "done",
  "failed",
] as const;

type ProgressState = {
  index: number;
  total: number;
  filename: string;
  status: "running" | "done" | "error";
  errorMsg?: string;
};

const STATUS_LEGEND = [
  { status: "new", description: "Paragon dodany do systemu, oczekuje na przetworzenie." },
  { status: "processing", description: "Trwa rozpoznawanie tekstu (OCR) i analiza paragonu." },
  { status: "processed", description: "Analiza zakończona, oczekuje na weryfikację kategorii." },
  { status: "to_confirm", description: "Wymaga ręcznego potwierdzenia lub poprawienia kategorii." },
  { status: "done", description: "Paragon zweryfikowany i w pełni przetworzony." },
  { status: "failed", description: "Przetwarzanie nie powiodło się — sprawdź plik i spróbuj ponownie." },
] as const;

export default function ReceiptsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);

  // Cleanup Pusher subscription on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const processMutation = useMutation({
    mutationFn: processReceipts,
    onSuccess: ({ task_id }) => {
      setProgress({ index: 0, total: 0, filename: "", status: "running" });

      const pusher = getPusher();
      const channel = pusher.subscribe("receipts");
      channelRef.current = channel;

      channel.bind("receipt.progress", (data: { task_id: string; index: number; total: number; filename: string; status: string }) => {
        if (data.task_id !== task_id) return;
        setProgress({ index: data.index, total: data.total, filename: data.filename, status: "running" });
      });

      channel.bind("receipt.done", (data: { task_id: string }) => {
        if (data.task_id !== task_id) return;
        setProgress((p) => p ? { ...p, status: "done" } : null);
        queryClient.invalidateQueries({ queryKey: ["receipts"] });
        channel.unbind_all();
        channel.unsubscribe();
      });

      channel.bind("receipt.error", (data: { task_id: string; error: string }) => {
        if (data.task_id !== task_id) return;
        setProgress((p) => p ? { ...p, status: "error", errorMsg: data.error } : null);
        channel.unbind_all();
        channel.unsubscribe();
      });
    },
  });

  const { data: receipts = [], isLoading } = useQuery({
    queryKey: ["receipts"],
    queryFn: listReceipts,
  });

  const filtered =
    statusFilter === "all"
      ? receipts
      : receipts.filter((r) => r.status === statusFilter);

  const columns: Column<ReceiptScanListItem>[] = [
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", sortValue: (r) => r.id },
    {
      header: "Plik",
      accessor: (r) => (
        <Link
          href={`/receipts/${r.id}`}
          className="text-[#635bff] hover:underline font-medium"
        >
          {r.filename}
        </Link>
      ),
      sortValue: (r) => r.filename,
    },
    {
      header: "Sklep",
      accessor: (r) => r.vendor ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.vendor ?? "",
    },
    {
      header: "Data",
      accessor: (r) => r.date ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.date ?? "",
    },
    {
      header: "Suma",
      accessor: (r) =>
        r.total != null ? (
          `${r.total.toFixed(2)} PLN`
        ) : (
          <span className="text-gray-400">—</span>
        ),
      className: "text-right",
      sortValue: (r) => r.total ?? -Infinity,
    },
    {
      header: "Status",
      accessor: (r) => <StatusBadge status={r.status} />,
      sortValue: (r) => r.status,
    },
    {
      header: "",
      accessor: (r) =>
        r.status === "to_confirm" ? (
          <Link
            href={`/receipts/${r.id}`}
            className="text-xs font-medium text-[#635bff] hover:underline"
          >
            Przejrzyj →
          </Link>
        ) : null,
    },
  ];

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-6">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Paragony</h1>
          <p className="text-sm text-gray-500 mt-1">
            Wszystkie zeskanowane paragony i ich status przetwarzania.
          </p>
        </div>
        <button
          onClick={() => processMutation.mutate()}
          disabled={processMutation.isPending || progress?.status === "running"}
          className="px-4 py-2 rounded-md bg-[#635bff] text-white text-sm font-medium hover:bg-[#5248db] disabled:opacity-50 transition-colors"
        >
          {processMutation.isPending || progress?.status === "running" ? "Przetwarzanie…" : "Przetwórz paragony"}
        </button>
      </div>

      {/* Status legend */}
      <div className="flex-shrink-0 rounded-lg border border-gray-200 bg-white overflow-hidden">
        <button
          onClick={() => setLegendOpen((o) => !o)}
          className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <span>Legenda statusów</span>
          <span className={`transition-transform duration-200 ${legendOpen ? "rotate-180" : ""}`}>▾</span>
        </button>
        {legendOpen && (
          <div className="border-t border-gray-100 px-4 py-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
            {STATUS_LEGEND.map(({ status, description }) => (
              <div key={status} className="flex items-start gap-2.5 py-1">
                <StatusBadge status={status} />
                <span className="text-xs text-gray-500 leading-5">{description}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Live progress bar */}
      {progress && (
        <div className="flex-shrink-0 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm">
          {progress.status === "running" && (
            <>
              <div className="flex justify-between mb-1 text-gray-600">
                <span>
                  {progress.total > 0
                    ? `Przetwarzanie ${progress.index} / ${progress.total} — ${progress.filename}`
                    : "Uruchamianie…"}
                </span>
                <span>{progress.total > 0 ? `${Math.round((progress.index / progress.total) * 100)}%` : ""}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-[#635bff] h-1.5 rounded-full transition-all duration-300"
                  style={{ width: progress.total > 0 ? `${(progress.index / progress.total) * 100}%` : "0%" }}
                />
              </div>
            </>
          )}
          {progress.status === "done" && (
            <p className="text-green-600 font-medium">✓ Przetwarzanie zakończone — przetworzono {progress.total} paragon{progress.total !== 1 ? "ów" : ""}.</p>
          )}
          {progress.status === "error" && (
            <p className="text-red-600 font-medium">✗ Error: {progress.errorMsg}</p>
          )}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2 flex-shrink-0">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              statusFilter === s
                ? "bg-[#635bff] text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s === "all"
              ? `Wszystkie (${receipts.length})`
              : `${s} (${receipts.filter((r) => r.status === s).length})`}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={filtered}
          emptyMessage="Brak paragonów spełniających filtr."
          className="flex-1 min-h-0"
        />
      )}
    </div>
  );
}
