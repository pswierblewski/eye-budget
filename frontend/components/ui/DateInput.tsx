"use client";

import { useState } from "react";
import { DayPicker } from "react-day-picker";
import { pl } from "react-day-picker/locale";
import * as Popover from "@radix-ui/react-popover";
import { isoToDisplay, displayToIso } from "@/lib/utils";

// ── helpers ────────────────────────────────────────────────────────
function isoToDate(iso: string): Date | undefined {
  if (!iso) return undefined;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return undefined;
  return new Date(y, m - 1, d);
}

function dateToIso(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// ── size map (mirrors Input component) ────────────────────────────
const sizeClasses = {
  xs: "h-7 px-2 text-xs",
  sm: "h-8 px-2.5 text-sm",
  md: "h-9 px-3 text-sm",
} as const;

type InputSize = keyof typeof sizeClasses;

// ── DayPicker v9 classNames ────────────────────────────────────────
const calendarClassNames = {
  root: "p-3 bg-white rounded-xl shadow-lg border border-gray-200 text-sm select-none",
  months: "flex flex-col gap-4",
  month: "flex flex-col gap-2",
  month_caption: "flex items-center justify-between px-1",
  caption_label: "font-semibold text-gray-800 capitalize",
  nav: "flex items-center gap-1",
  button_previous:
    "p-1 rounded-md text-gray-500 hover:bg-gray-100 transition-colors",
  button_next:
    "p-1 rounded-md text-gray-500 hover:bg-gray-100 transition-colors",
  weeks: "flex flex-col gap-0.5",
  week: "flex gap-0.5",
  weekdays: "flex gap-0.5 mb-1",
  weekday: "w-8 text-center text-xs font-medium text-gray-400 uppercase py-1",
  day: "flex items-center justify-center w-8",
  day_button:
    "w-8 h-8 rounded-md text-sm text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer",
  selected:
    "bg-accent text-white rounded-md [&_button]:bg-accent [&_button]:text-white [&_button]:hover:bg-accent-hover",
  today: "[&_button]:font-bold [&_button]:text-accent",
  outside: "opacity-40",
  disabled: "opacity-30 cursor-not-allowed",
  hidden: "invisible",
};

// ── component ──────────────────────────────────────────────────────
interface DateInputProps {
  value: string; // ISO yyyy-mm-dd or ""
  onChange: (iso: string) => void;
  inputSize?: InputSize;
  className?: string;
  placeholder?: string;
}

export function DateInput({
  value,
  onChange,
  inputSize = "md",
  className = "",
  placeholder = "dd-mm-yyyy",
}: DateInputProps) {
  const [open, setOpen] = useState(false);
  const selected = isoToDate(value);

  function handleSelect(date: Date | undefined) {
    if (date) {
      onChange(dateToIso(date));
      setOpen(false);
    }
  }

  const displayValue = value ? isoToDisplay(value) : "";

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={[
            "inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white font-mono",
            "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
            "hover:border-gray-400 transition-colors text-left",
            sizeClasses[inputSize],
            !displayValue ? "text-gray-400" : "text-gray-800",
            className,
          ].join(" ")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-3.5 w-3.5 text-gray-400 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span>{displayValue || placeholder}</span>
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          sideOffset={4}
          align="start"
          className="z-50 outline-none"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <DayPicker
            mode="single"
            selected={selected}
            onSelect={handleSelect}
            locale={pl}
            weekStartsOn={1}
            classNames={calendarClassNames}
          />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
