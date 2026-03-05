import React from "react";
import { clsx } from "clsx";

type PillVariant = "tag" | "category-primary" | "category-secondary";
type PillSize = "sm" | "md";

interface PillProps {
  children: React.ReactNode;
  variant?: PillVariant;
  size?: PillSize;
  className?: string;
}

const variantClasses: Record<PillVariant, string> = {
  tag: "bg-indigo-50 text-indigo-700 border border-indigo-200",
  "category-primary": "bg-indigo-50 text-indigo-700 border border-indigo-200",
  "category-secondary": "bg-gray-50 text-gray-600 border border-gray-200",
};

const sizeClasses: Record<PillSize, string> = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-3 py-1",
};

export function Pill({
  children,
  variant = "tag",
  size = "sm",
  className,
}: PillProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full font-medium",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {children}
    </span>
  );
}
