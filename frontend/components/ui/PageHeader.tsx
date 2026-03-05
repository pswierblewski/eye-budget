import React from "react";
import { clsx } from "clsx";

interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  /** "list" uses text-2xl (default), "detail" uses text-xl */
  variant?: "list" | "detail";
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  actions,
  variant = "list",
  className,
}: PageHeaderProps) {
  return (
    <div className={clsx("flex items-start justify-between gap-4", className)}>
      <div className="min-w-0">
        <h1
          className={clsx(
            "font-bold text-gray-900",
            variant === "list" ? "text-2xl" : "text-xl"
          )}
        >
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
