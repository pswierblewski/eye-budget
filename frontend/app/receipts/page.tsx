"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listReceipts, processReceipts, deleteReceipt, retryReceipt, getReceiptCounts } from "@/lib/api";
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
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkPending, setBulkPending] = useState<"delete" | "retry" | null>(null);
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);
  const bulkMenuRef = useRef<HTMLDivElement>(null);

  // Cleanup Pusher subscription on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!bulkMenuOpen) return;
    function handleClick(e: MouseEvent) {
      if (bulkMenuRef.current && !bulkMenuRef.current.contains(e.target as Node)) {
        setBulkMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [bulkMenuOpen]);

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
        queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
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

  const bulkDelete = async () => {
    if (!window.confirm(`Czy na pewno usunąć ${selectedIds.size} paragon${selectedIds.size !== 1 ? "ów" : ""}? Tej operacji nie można cofnąć.`)) return;
    setBulkPending("delete");
    await Promise.allSettled(Array.from(selectedIds).map((id) => deleteReceipt(id)));
    setSelectedIds(new Set());
    setBulkPending(null);
    queryClient.invalidateQueries({ queryKey: ["receipts"] });
    queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
  };

  const bulkRetry = async () => {
    setBulkPending("retry");
    await Promise.allSettled(Array.from(selectedIds).map((id) => retryReceipt(id)));
    setSelectedIds(new Set());
    setBulkPending(null);
    queryClient.invalidateQueries({ queryKey: ["receipts"] });
    queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
  };

  const { data, isLoading } = useQuery({
    queryKey: ["receipts", page, statusFilter, sortBy, sortDir],
    queryFn: () => listReceipts({
      page,
      limit: PAGE_SIZE,
      status: statusFilter !== "all" ? statusFilter : undefined,
      sort_by: sortBy,
      sort_dir: sortDir,
    }),
    staleTime: 30_000,
  });
  const receipts = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: statusCounts = {} } = useQuery({
    queryKey: ["receipts-counts"],
    queryFn: getReceiptCounts,
    staleTime: 30_000,
  });
  const totalAll = Object.values(statusCounts).reduce<number>((sum, v) => sum + v, 0);

  const filtered = receipts;

  const allFilteredSelected = filtered.length > 0 && filtered.every((r) => selectedIds.has(r.id));

  const toggleAll = () => {
    if (allFilteredSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filtered.forEach((r) => next.delete(r.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filtered.forEach((r) => next.add(r.id));
        return next;
      });
    }
  };

  const columns: Column<ReceiptScanListItem>[] = [
    {
      header: "",
      headerNode: (
        <input
          type="checkbox"
          checked={allFilteredSelected}
          onChange={toggleAll}
          className="rounded border-gray-300 text-[#635bff] focus:ring-[#635bff] cursor-pointer"
          onClick={(e) => e.stopPropagation()}
        />
      ),
      accessor: (r) => (
        <input
          type="checkbox"
          checked={selectedIds.has(r.id)}
          onChange={() =>
            setSelectedIds((prev) => {
              const next = new Set(prev);
              if (next.has(r.id)) next.delete(r.id); else next.add(r.id);
              return next;
            })
          }
          onClick={(e) => e.stopPropagation()}
          className="rounded border-gray-300 text-[#635bff] focus:ring-[#635bff] cursor-pointer"
        />
      ),
      className: "w-10",
    },
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", serverSortKey: "id" },
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
      serverSortKey: "filename",
    },
    {
      header: "Sklep",
      accessor: (r) => r.vendor ?? <span className="text-gray-400">—</span>,
      serverSortKey: "vendor",
    },
    {
      header: "Data",
      accessor: (r) => r.date ?? <span className="text-gray-400">—</span>,
      serverSortKey: "date",
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
      serverSortKey: "total",
    },
    {
      header: "Status",
      accessor: (r) => <StatusBadge status={r.status} />,
      serverSortKey: "status",
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

      {/* Filter tabs + bulk actions — same row */}
      <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(1); setSelectedIds(new Set()); }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              statusFilter === s
                ? "bg-[#635bff] text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s === "all"
              ? `Wszystkie (${totalAll})`
              : `${s} (${statusCounts[s] ?? 0})`}
          </button>
        ))}

        {selectedIds.size > 0 && (
          <>
            <div className="w-px h-5 bg-gray-300 mx-1" />
            <span className="text-xs text-gray-500 font-medium">
              Zaznaczono: {selectedIds.size}
            </span>
            <button
              onClick={bulkRetry}
              disabled={bulkPending !== null}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {bulkPending === "retry" ? "Ponawiam…" : "Ponów przetwarzanie"}
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              disabled={bulkPending !== null}
              className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
            >
              Odznacz
            </button>
            <div className="relative" ref={bulkMenuRef}>
              <button
                onClick={() => setBulkMenuOpen((o) => !o)}
                disabled={bulkPending !== null}
                className="text-xs px-2 py-1.5 rounded-full border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors leading-none"
                title="Więcej akcji"
              >
                ⋯
              </button>
              {bulkMenuOpen && (
                <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[160px]">
                  <button
                    type="button"
                    onClick={() => { setBulkMenuOpen(false); bulkDelete(); }}
                    disabled={bulkPending !== null}
                    className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                  >
                    {bulkPending === "delete" ? "Usuwam…" : "Usuń zaznaczone"}
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={filtered}
          emptyMessage="Brak paragonów spełniających filtr."
          className="flex-1 min-h-0"
          pagination={{
            page, pageSize: PAGE_SIZE, total, onPageChange: setPage,
            sortBy, sortDir,
            onSortChange: (key, dir) => { setSortBy(key); setSortDir(dir); setPage(1); },
          }}
        />
      )}
    </div>
  );
}
