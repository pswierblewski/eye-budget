import React from "react";
import { clsx } from "clsx";

interface FilterTab<T extends string> {
  value: T;
  label: React.ReactNode;
}

interface FilterTabsProps<T extends string> {
  tabs: FilterTab<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function FilterTabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
}: FilterTabsProps<T>) {
  return (
    <div
      className={clsx(
        "inline-flex border border-gray-200 rounded-lg overflow-hidden divide-x divide-gray-200 bg-white",
        className
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={clsx(
            "px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap",
            value === tab.value
              ? "bg-accent text-white"
              : "text-gray-600 hover:bg-gray-50"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
