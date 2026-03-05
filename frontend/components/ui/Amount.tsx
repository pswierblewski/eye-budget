import React from "react";
import { clsx } from "clsx";

interface AmountProps {
  value: number;
  currency?: string;
  className?: string;
  /** If true, always show sign regardless of value */
  showSign?: boolean;
}

export function formatAmount(value: number, currency = "PLN"): string {
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(value);
}

export function Amount({
  value,
  currency = "PLN",
  className,
}: AmountProps) {
  const isNegative = value < 0;
  return (
    <span
      className={clsx(
        "font-semibold tabular-nums",
        isNegative ? "text-red-600" : "text-green-600",
        className
      )}
    >
      {formatAmount(value, currency)}
    </span>
  );
}
