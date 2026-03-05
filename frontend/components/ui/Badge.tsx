import React from "react";
import { clsx } from "clsx";
import { SOURCE_CONFIG, SOURCE_FALLBACK } from "@/lib/sourceConfig";

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
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${style}`}
    >
      {label}
    </span>
  );
}

// ---- Source Badge ----

export function SourceBadge({ source, showLabel = false }: { source: string; showLabel?: boolean }) {
  const cfg = SOURCE_CONFIG[source as keyof typeof SOURCE_CONFIG];
  const style = cfg?.style ?? SOURCE_FALLBACK.style;
  const label = cfg?.label ?? source;
  const Icon = cfg?.icon;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full",
        showLabel ? "px-2 py-0.5" : "p-1 justify-center",
        style
      )}
      title={!showLabel ? label : undefined}
    >
      {Icon ? <Icon size={12} /> : null}
      {showLabel && <span className="text-[10px] font-semibold">{label}</span>}
      {!Icon && !showLabel && label}
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
