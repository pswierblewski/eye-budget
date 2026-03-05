import React from "react";
import { clsx } from "clsx";

type Variant = "primary" | "secondary" | "danger" | "ghost" | "dashed";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover disabled:opacity-50 border border-transparent",
  secondary:
    "border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50",
  danger:
    "bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 border border-transparent",
  ghost:
    "text-gray-500 hover:text-gray-700 bg-transparent border border-transparent disabled:opacity-50",
  dashed:
    "border border-dashed border-gray-300 text-gray-500 bg-white hover:border-accent hover:text-accent disabled:opacity-50",
};

const sizeClasses: Record<Size, string> = {
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-4 py-2",
  lg: "text-sm px-5 py-2.5",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
