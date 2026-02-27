"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listGroundTruth } from "@/lib/api";
import { GroundTruthEntry } from "@/lib/types";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";

export default function GroundTruthPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["ground-truth"],
    queryFn: listGroundTruth,
  });

  const columns: Column<GroundTruthEntry>[] = [
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", sortValue: (r) => r.id },
    {
      header: "File",
      accessor: (r) => (
        <Link
          href={`/ground-truth/${r.id}`}
          className="text-[#635bff] hover:underline font-medium"
        >
          {r.filename}
        </Link>
      ),
      sortValue: (r) => r.filename,
    },
    {
      header: "Vendor",
      accessor: (r) =>
        r.ground_truth.vendor ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.ground_truth.vendor ?? "",
    },
    {
      header: "Date",
      accessor: (r) =>
        r.ground_truth.date ?? <span className="text-gray-400">—</span>,
      sortValue: (r) => r.ground_truth.date ?? "",
    },
    {
      header: "Total",
      accessor: (r) =>
        r.ground_truth.total != null
          ? `${r.ground_truth.total.toFixed(2)} PLN`
          : "—",
      className: "text-right",
      sortValue: (r) => r.ground_truth.total ?? -Infinity,
    },
    {
      header: "Added",
      accessor: (r) => r.created_at.slice(0, 10),
      sortValue: (r) => r.created_at,
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
          <h1 className="text-2xl font-bold text-gray-900">Ground Truth</h1>
          <p className="text-sm text-gray-500 mt-1">
            Verified receipts used for OCR evaluation.
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
            className="px-4 py-2 rounded-md bg-[#635bff] text-white text-sm font-medium hover:bg-[#5248db] disabled:opacity-50 transition-colors"
          >
            {uploading ? "Uploading…" : "Upload receipt image"}
          </button>
        </div>
      </div>

      {uploadError && (
        <p className="text-sm text-red-500">{uploadError}</p>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={entries}
          emptyMessage="No ground truth entries yet."
          className="flex-1 min-h-0"
        />
      )}
    </div>
  );
}
