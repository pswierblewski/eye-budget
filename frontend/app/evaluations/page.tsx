"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listEvaluations, runEvaluation } from "@/lib/api";
import { EvaluationRunListItem } from "@/lib/types";
import { DataTable, Column } from "@/components/DataTable";
import { getPusher } from "@/lib/pusher";
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
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);

  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["evaluations"],
    queryFn: listEvaluations,
  });

  const runMutation = useMutation({
    mutationFn: runEvaluation,
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
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", sortValue: (r) => r.id },
    {
      header: "Timestamp",
      accessor: (r) =>
        new Date(r.run_timestamp).toLocaleString("en-GB", {
          dateStyle: "short",
          timeStyle: "short",
        }),
      sortValue: (r) => r.run_timestamp,
    },
    { header: "Model", accessor: "model_used", sortValue: (r) => r.model_used },
    { header: "Files", accessor: "total_files", className: "text-right", sortValue: (r) => r.total_files },
    {
      header: "Success rate",
      accessor: (r) => r.success_rate != null ? `${(r.success_rate * 100).toFixed(1)}%` : "—",
      className: "text-right",
      sortValue: (r) => r.success_rate ?? -1,
    },
    {
      header: "Avg completeness",
      accessor: (r) => r.avg_field_completeness != null ? `${(r.avg_field_completeness * 100).toFixed(1)}%` : "—",
      className: "text-right",
      sortValue: (r) => r.avg_field_completeness ?? -1,
    },
    {
      header: "Avg consistency",
      accessor: (r) => r.avg_consistency_rate != null ? `${(r.avg_consistency_rate * 100).toFixed(1)}%` : "—",
      className: "text-right",
      sortValue: (r) => r.avg_consistency_rate ?? -1,
    },
    {
      header: "Avg time (ms)",
      accessor: (r) => r.avg_processing_time_ms != null ? Math.round(r.avg_processing_time_ms).toString() : "—",
      className: "text-right",
      sortValue: (r) => r.avg_processing_time_ms ?? -1,
    },
    {
      header: "",
      accessor: (r) => (
        <Link
          href={`/evaluations/${r.id}`}
          className="text-xs text-[#635bff] hover:underline"
        >
          Details →
        </Link>
      ),
    },
  ];

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evaluations</h1>
          <p className="text-sm text-gray-500 mt-1">
            OCR quality evaluation runs against ground truth.
          </p>
        </div>
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending || progress?.status === "running"}
          className="px-4 py-2 rounded-md bg-[#635bff] text-white text-sm font-medium hover:bg-[#5248db] disabled:opacity-50 transition-colors"
        >
          {runMutation.isPending || progress?.status === "running" ? "Running…" : "Run evaluation"}
        </button>
      </div>

      {/* Live progress bar */}
      {progress && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm">
          {progress.status === "running" && (
            <>
              <div className="flex justify-between mb-1 text-gray-600">
                <span>
                  {progress.total > 0
                    ? `Evaluating ${progress.index} / ${progress.total} — ${progress.filename}`
                    : "Starting…"}
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
            <p className="text-green-600 font-medium">✓ Evaluation complete.</p>
          )}
          {progress.status === "error" && (
            <p className="text-red-600 font-medium">✗ Error: {progress.errorMsg}</p>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={runs}
          emptyMessage="No evaluation runs yet."
          className="flex-1 min-h-0"
        />
      )}
    </div>
  );
}
