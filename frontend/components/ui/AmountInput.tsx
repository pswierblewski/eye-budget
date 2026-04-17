"use client";

import { useEffect, useRef, useState } from "react";
import { twMerge } from "tailwind-merge";
import { parseAmountInput } from "@/lib/amounts";

interface AmountInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>,
    "type" | "value" | "onChange"> {
  value: number | null;
  onChange: (value: number | null) => void;
}

function formatForInput(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

export function AmountInput({
  value,
  onChange,
  onFocus,
  onBlur,
  className,
  ...props
}: AmountInputProps) {
  const [inputValue, setInputValue] = useState<string>(
    value !== null ? formatForInput(value) : ""
  );
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) {
      setInputValue(value !== null ? formatForInput(value) : "");
    }
  }, [value]);

  return (
    <input
      {...props}
      type="text"
      inputMode="decimal"
      className={twMerge(
        "border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors text-sm px-3 py-1.5",
        className
      )}
      value={inputValue}
      onFocus={(e) => {
        focused.current = true;
        onFocus?.(e);
      }}
      onBlur={(e) => {
        focused.current = false;
        setInputValue(value !== null ? formatForInput(value) : "");
        onBlur?.(e);
      }}
      onChange={(e) => {
        const raw = e.target.value;
        setInputValue(raw);
        onChange(parseAmountInput(raw));
      }}
    />
  );
}
