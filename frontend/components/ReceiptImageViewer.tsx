"use client";

import { useState, useEffect } from "react";

interface ReceiptImageViewerProps {
  scanId: number;
  refreshKey?: number;
  onReuploadImage?: () => Promise<void>;
}

export function ReceiptImageViewer({ scanId, refreshKey = 0, onReuploadImage }: ReceiptImageViewerProps) {
  const [error, setError] = useState(false);
  const [reuploading, setReuploading] = useState(false);

  // Reset error state when refreshKey changes (triggered after successful reupload)
  useEffect(() => {
    if (refreshKey > 0) setError(false);
  }, [refreshKey]);

  const handleReupload = async () => {
    if (!onReuploadImage) return;
    setReuploading(true);
    try {
      await onReuploadImage();
    } finally {
      setReuploading(false);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-gray-300 bg-gray-50 h-96 text-gray-400 text-sm">
        <span>Zdjęcie niedostępne</span>
        {onReuploadImage && (
          <button
            onClick={handleReupload}
            disabled={reuploading}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {reuploading ? "Wgrywam…" : "Ponów wgrywanie zdjęcia"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative rounded-xl border border-gray-200 overflow-hidden bg-gray-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/receipts/${scanId}/image${refreshKey > 0 ? `?t=${refreshKey}` : ""}`}
        alt={`Receipt ${scanId}`}
        className="w-full object-contain max-h-[70vh]"
        onError={() => setError(true)}
      />
    </div>
  );
}
