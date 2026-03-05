"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listGroundTruth } from "@/lib/api";
import { GroundTruthEntry } from "@/lib/types";
import { isoToDisplay } from "@/lib/utils";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";

export default function GroundTruthPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ground-truth", page, sortBy, sortDir],
    queryFn: () => listGroundTruth({ page, limit: PAGE_SIZE, sort_by: sortBy, sort_dir: sortDir }),
    staleTime: 30_000,
  });
  const entries = data?.items ?? [];
  const total = data?.total ?? 0;

  const columns: Column<GroundTruthEntry>[] = [
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", serverSortKey: "id" },
    {
      header: "Plik",
      accessor: (r) => (
        <Link
          href={`/ground-truth/${r.id}`}
          className="text-accent hover:underline font-medium"
        >
          {r.filename}
        </Link>
      ),
      serverSortKey: "filename",
    },
    {
      header: "Sklep",
      accessor: (r) =>
        r.ground_truth.vendor ?? <span className="text-gray-400">—</span>,
      serverSortKey: "vendor",
    },
    {
      header: "Data",
      accessor: (r) =>
        r.ground_truth.date
          ? <span className="font-mono text-xs text-gray-600">{isoToDisplay(r.ground_truth.date)}</span>
          : <span className="text-gray-400">—</span>,
      serverSortKey: "date",
    },
    {
      header: "Suma",
      accessor: (r) =>
        r.ground_truth.total != null
          ? `${r.ground_truth.total.toFixed(2)} PLN`
          : "—",
      className: "text-right",
      serverSortKey: "total",
    },
    {
      header: "Dodano",
      accessor: (r) => r.created_at.slice(0, 10),
      serverSortKey: "created_at",
    },
  ];

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/ground-truth", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      await queryClient.invalidateQueries({ queryKey: ["ground-truth"] });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dane wzorcowe</h1>
          <p className="text-sm text-gray-500 mt-1">
            Zweryfikowane paragony używane do oceny OCR.
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
              e.target.value = "";
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {uploading ? "Przesyłanie…" : "Prześlij obraz paragonu"}
          </button>
        </div>
      </div>

      {uploadError && (
        <p className="text-sm text-red-500">{uploadError}</p>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={entries}
          emptyMessage="Brak danych wzorcowych."
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
