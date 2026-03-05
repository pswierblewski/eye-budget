import React from "react";
import { clsx } from "clsx";

interface SectionLabelProps {
  children: React.ReactNode;
  className?: string;
  as?: "p" | "span" | "div";
}

export function SectionLabel({
  children,
  className,
  as: Tag = "p",
}: SectionLabelProps) {
  return (
    <Tag
      className={clsx(
        "text-xs font-semibold text-gray-500 uppercase tracking-wide",
        className
      )}
    >
      {children}
    </Tag>
  );
}
