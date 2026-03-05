"use client";

import React, { useRef, useEffect, useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { clsx } from "clsx";

export interface ThreeDotsMenuItem {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
  separator?: boolean; // render a separator line before this item
  disabled?: boolean;
}

interface ThreeDotsMenuProps {
  items: ThreeDotsMenuItem[];
  /** "inline" – compact icon for table rows; "outlined" – bordered button for page headers */
  variant?: "inline" | "outlined";
  title?: string;
  align?: "right" | "left";
  className?: string;
}

export function ThreeDotsMenu({
  items,
  variant = "inline",
  title = "Więcej opcji",
  align = "right",
  className,
}: ThreeDotsMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className={clsx("relative", className)}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        title={title}
        className={clsx(
          "transition-colors",
          variant === "outlined"
            ? "px-2.5 py-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50"
            : "p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
        )}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>

      {open && (
        <div
          className={clsx(
            "absolute top-full mt-1 z-40 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[160px]",
            align === "right" ? "right-0" : "left-0"
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {items.map((item, i) => (
            <React.Fragment key={i}>
              {item.separator && (
                <div className="border-t border-gray-100 my-1" />
              )}
              <button
                onClick={() => {
                  item.onClick();
                  setOpen(false);
                }}
                disabled={item.disabled}
                className={clsx(
                  "w-full text-left text-sm px-4 py-2 transition-colors disabled:opacity-50",
                  item.variant === "danger"
                    ? "text-red-600 hover:bg-red-50"
                    : "text-gray-700 hover:bg-gray-50"
                )}
              >
                {item.label}
              </button>
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
