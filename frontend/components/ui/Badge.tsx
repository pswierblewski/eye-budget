import React from "react";
import { clsx } from "clsx";

// ---- Status Badge ----

const STATUS_STYLES: Record<string, string> = {
  new: "bg-gray-100 text-gray-600",
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
  processed: "bg-yellow-100 text-yellow-700",
  to_confirm: "bg-orange-100 text-orange-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  new: "Nowy",
  pending: "Oczekujący",
  processing: "Przetwarzanie",
  processed: "Przetworzony",
  to_confirm: "Do potwierdzenia",
  done: "Gotowe",
  failed: "Błąd",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-500";
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}
    >
      {label}
    </span>
  );
}

// ---- Source Badge ----

const SOURCE_STYLES: Record<string, string> = {
  bank: "bg-blue-50 text-blue-700",
  cash: "bg-green-50 text-green-700",
  receipt: "bg-orange-50 text-orange-700",
};

const SOURCE_LABELS: Record<string, string> = {
  bank: "Bank",
  cash: "Gotówka",
  receipt: "Paragon",
};

export function SourceBadge({ source }: { source: string }) {
  const style = SOURCE_STYLES[source] ?? "bg-gray-100 text-gray-500";
  const label = SOURCE_LABELS[source] ?? source;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold",
        style
      )}
    >
      {label}
    </span>
  );
}

// ---- Match Badge (receipt scanning score) ----

const MATCH_STYLES: Record<number, string> = {
  2: "bg-yellow-100 text-yellow-700",
  3: "bg-green-100 text-green-700",
};

const MATCH_LABELS: Record<number, string> = {
  2: "kwota + data",
  3: "kwota + data + sklep",
};

export function MatchBadge({ score }: { score: number }) {
  return (
    <span
      className={clsx(
        "text-[10px] font-medium px-1.5 py-0.5 rounded-full",
        MATCH_STYLES[score] ?? "bg-gray-100 text-gray-500"
      )}
    >
      {MATCH_LABELS[score] ?? `score ${score}`}
    </span>
  );
}

// ---- Count Badge (e.g. +3 categories) ----

export function CountBadge({
  count,
  className,
}: {
  count: number;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium",
        className
      )}
    >
      +{count}
    </span>
  );
}
