"use client";

import { useState } from "react";

export function ReceiptImageViewer({ scanId }: { scanId: number }) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 h-96 text-gray-400 text-sm">
        Image not available
      </div>
    );
  }

  return (
    <div className="relative rounded-xl border border-gray-200 overflow-hidden bg-gray-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/receipts/${scanId}/image`}
        alt={`Receipt ${scanId}`}
        className="w-full object-contain max-h-[70vh]"
        onError={() => setError(true)}
      />
    </div>
  );
}
