"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listReceipts,
  processReceipts,
  runEvaluation,
} from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { DataTable, Column } from "@/components/DataTable";
import { ReceiptScanListItem } from "@/lib/types";
import Link from "next/link";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: receipts = [], isLoading } = useQuery({
    queryKey: ["receipts"],
    queryFn: listReceipts,
  });

  const processMutation = useMutation({
    mutationFn: processReceipts,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["receipts"] }),
  });

  const evalMutation = useMutation({
    mutationFn: runEvaluation,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["evaluations"] }),
  });

  const total = receipts.length;
  const toConfirm = receipts.filter((r) => r.status === "to_confirm").length;
  const done = receipts.filter((r) => r.status === "done").length;
  const failed = receipts.filter((r) => r.status === "failed").length;

  const recent = receipts.slice(0, 10);

  const columns: Column<ReceiptScanListItem>[] = [
    {
      header: "ID",
      accessor: "id",
      className: "w-16 text-gray-400 font-mono",
      sortValue: (r) => r.id,
    },
    {
      header: "File",
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
      header: "Vendor",
      accessor: (r) => r.vendor ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.vendor ?? "",
    },
    {
      header: "Date",
      accessor: (r) => r.date ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.date ?? "",
    },
    {
      header: "Total",
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
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Receipt processing overview
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => evalMutation.mutate()}
            disabled={evalMutation.isPending}
            className="px-4 py-2 rounded-md border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {evalMutation.isPending ? "Running…" : "Run evaluation"}
          </button>
          <button
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending}
            className="px-4 py-2 rounded-md bg-[#635bff] text-white text-sm font-medium hover:bg-[#5248db] disabled:opacity-50 transition-colors"
          >
            {processMutation.isPending ? "Processing…" : "Process receipts"}
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total receipts" value={total} />
        <StatCard label="To confirm" value={toConfirm} accent />
        <StatCard label="Done" value={done} />
        <StatCard label="Failed" value={failed} />
      </div>

      {/* Recent receipts */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            Recent receipts
          </h2>
          <Link
            href="/receipts"
            className="text-sm text-[#635bff] hover:underline"
          >
            View all →
          </Link>
        </div>
        {isLoading ? (
          <div className="text-sm text-gray-400 py-8 text-center">
            Loading…
          </div>
        ) : (
          <DataTable
            columns={columns}
            rows={recent}
            emptyMessage="No receipts yet. Click 'Process receipts' to start."
          />
        )}
      </div>
    </div>
  );
}
