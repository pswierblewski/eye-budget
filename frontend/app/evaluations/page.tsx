"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listEvaluations, runEvaluation, listGroundTruth } from "@/lib/api";
import { EvaluationRunListItem, GroundTruthEntry } from "@/lib/types";
import { DataTable, Column } from "@/components/DataTable";
import { Modal } from "@/components/ui";
import { getPusher } from "@/lib/pusher";
import { isoToDisplay } from "@/lib/utils";
import Link from "next/link";

type ProgressState = {
  index: number;
  total: number;
  filename: string;
  status: "running" | "done" | "error";
  errorMsg?: string;
};

export default function EvaluationsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);
  const [showSelectModal, setShowSelectModal] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["evaluations", page, sortBy, sortDir],
    queryFn: () => listEvaluations({ page, limit: PAGE_SIZE, sort_by: sortBy, sort_dir: sortDir }),
    staleTime: 30_000,
  });
  const runs = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: groundTruthData, isLoading: isLoadingGT } = useQuery({
    queryKey: ["ground-truth-all"],
    queryFn: () => listGroundTruth({ limit: 500, sort_by: "filename", sort_dir: "asc" }),
    enabled: showSelectModal,
    staleTime: 60_000,
  });
  const gtEntries: GroundTruthEntry[] = groundTruthData?.items ?? [];

  function toggleEntry(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selectedIds.size === gtEntries.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(gtEntries.map((e) => e.id)));
    }
  }

  function openSelectModal() {
    setSelectedIds(new Set());
    setShowSelectModal(true);
  }

  const runMutation = useMutation({
    mutationFn: (entryIds: number[]) => runEvaluation(entryIds.length > 0 ? entryIds : undefined),
    onSuccess: ({ task_id }) => {
      setProgress({ index: 0, total: 0, filename: "", status: "running" });

      const pusher = getPusher();
      const channel = pusher.subscribe(`evaluation-${task_id}`);
      channelRef.current = channel;

      channel.bind("evaluation.progress", (data: { task_id: string; index: number; total: number; filename: string; success: boolean }) => {
        setProgress({ index: data.index, total: data.total, filename: data.filename, status: "running" });
      });

      channel.bind("evaluation.done", () => {
        setProgress((p) => p ? { ...p, status: "done" } : null);
        queryClient.invalidateQueries({ queryKey: ["evaluations"] });
        channel.unbind_all();
        channel.unsubscribe();
      });

      channel.bind("evaluation.error", (data: { error: string }) => {
        setProgress((p) => p ? { ...p, status: "error", errorMsg: data.error } : null);
        channel.unbind_all();
        channel.unsubscribe();
      });
    },
  });

  const columns: Column<EvaluationRunListItem>[] = [
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", serverSortKey: "id" },
    {
      header: "Data",
      accessor: (r) =>
        new Date(r.run_timestamp).toLocaleString("en-GB", {
          dateStyle: "short",
          timeStyle: "short",
        }),
      serverSortKey: "run_timestamp",
    },
    { header: "Model", accessor: "model_used", serverSortKey: "model_used" },
    { header: "Pliki", accessor: "total_files", className: "text-right", serverSortKey: "total_files" },
    {
      header: "Trafność",
      accessor: (r) => r.success_rate != null ? `${(r.success_rate * 100).toFixed(1)}%` : "—",
      className: "text-right",
      serverSortKey: "success_rate",
    },
    {
      header: "Śr. kompletność",
      accessor: (r) => r.avg_field_completeness != null ? `${(r.avg_field_completeness * 100).toFixed(1)}%` : "—",
      className: "text-right",
      serverSortKey: "avg_field_completeness",
    },
    {
      header: "Śr. spójność",
      accessor: (r) => r.avg_consistency_rate != null ? `${(r.avg_consistency_rate * 100).toFixed(1)}%` : "—",
      className: "text-right",
      serverSortKey: "avg_consistency_rate",
    },
    {
      header: "Śr. czas (ms)",
      accessor: (r) => r.avg_processing_time_ms != null ? Math.round(r.avg_processing_time_ms).toString() : "—",
      className: "text-right",
      serverSortKey: "avg_processing_time_ms",
    },
    {
      header: "",
      accessor: (r) => (
        <Link
          href={`/evaluations/${r.id}`}
          className="text-xs text-accent hover:underline"
        >
          Szczegóły →
        </Link>
      ),
    },
  ];

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ewaluacje</h1>
          <p className="text-sm text-gray-500 mt-1">
            Przebiegi oceny jakości OCR na danych wzorcowych.
          </p>
        </div>
        <button
          onClick={openSelectModal}
          disabled={runMutation.isPending || progress?.status === "running"}
          className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
        >
          {runMutation.isPending || progress?.status === "running" ? "Trwa ocena…" : "Uruchom ocenę"}
        </button>
      </div>

      {/* Ground truth selection modal */}
      <Modal
        open={showSelectModal}
        onClose={() => setShowSelectModal(false)}
        maxWidth="lg"
        className="!max-w-2xl flex flex-col max-h-[80vh]"
      >
        <div className="px-6 pt-5 pb-4 flex flex-col gap-4 min-h-0">
          <div className="flex items-center justify-between shrink-0">
            <h2 className="text-lg font-bold text-gray-900">Wybierz dane wzorcowe</h2>
            <button onClick={() => setShowSelectModal(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
          </div>

          {isLoadingGT ? (
            <p className="text-sm text-gray-400 py-4 text-center">Ładowanie…</p>
          ) : (
            <>
              <div className="flex items-center justify-between shrink-0 border-b border-gray-100 pb-3">
                <span className="text-sm text-gray-500">
                  {selectedIds.size} / {gtEntries.length} zaznaczonych
                </span>
                <button
                  onClick={toggleAll}
                  className="text-sm text-accent hover:underline"
                >
                  {selectedIds.size === gtEntries.length ? "Odznacz wszystkie" : "Zaznacz wszystkie"}
                </button>
              </div>
              <div className="overflow-y-auto flex-1 min-h-0">
                <ul className="divide-y divide-gray-100">
                  {gtEntries.map((entry) => (
                    <li
                      key={entry.id}
                      onClick={() => toggleEntry(entry.id)}
                      className="flex items-center gap-3 px-1 py-2.5 cursor-pointer hover:bg-gray-50 rounded"
                    >
                      <input
                        type="checkbox"
                        readOnly
                        checked={selectedIds.has(entry.id)}
                        className="h-4 w-4 rounded border-gray-300 accent-[#635bff] cursor-pointer shrink-0"
                      />
                      <span className="font-mono text-xs text-gray-700 flex-1 min-w-0 truncate" title={entry.filename}>
                        {entry.filename}
                      </span>
                      <span className="text-xs text-gray-500 shrink-0 hidden sm:inline">
                        {entry.ground_truth.vendor ?? "—"}
                      </span>
                      <span className="text-xs text-gray-400 font-mono shrink-0 hidden sm:inline">
                        {entry.ground_truth.date ? isoToDisplay(entry.ground_truth.date) : "—"}
                      </span>
                      <span className="text-xs text-gray-500 shrink-0 w-20 text-right hidden sm:inline">
                        {entry.ground_truth.total != null ? `${entry.ground_truth.total.toFixed(2)} PLN` : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 shrink-0">
            <button
              onClick={() => setShowSelectModal(false)}
              className="px-4 py-2 rounded-md border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Anuluj
            </button>
            <button
              onClick={() => {
                setShowSelectModal(false);
                runMutation.mutate(Array.from(selectedIds));
              }}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              Uruchom ocenę ({selectedIds.size})
            </button>
          </div>
        </div>
      </Modal>

      {/* Live progress bar */}
      {progress && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm">
          {progress.status === "running" && (
            <>
              <div className="flex justify-between mb-1 text-gray-600">
                <span>
                  {progress.total > 0
                    ? `Ocenianie ${progress.index} / ${progress.total} — ${progress.filename}`
                    : "Uruchamianie…"}
                </span>
                <span>{progress.total > 0 ? `${Math.round((progress.index / progress.total) * 100)}%` : ""}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-accent h-1.5 rounded-full transition-all duration-300"
                  style={{ width: progress.total > 0 ? `${(progress.index / progress.total) * 100}%` : "0%" }}
                />
              </div>
            </>
          )}
          {progress.status === "done" && (
            <p className="text-green-600 font-medium">✓ Ocena zakończona.</p>
          )}
          {progress.status === "error" && (
            <p className="text-red-600 font-medium">✗ Error: {progress.errorMsg}</p>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={runs}
          emptyMessage="Brak przebiegów ewaluacji."
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
