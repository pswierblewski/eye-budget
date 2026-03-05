import React from "react";
import { clsx } from "clsx";

type InputSize = "xs" | "sm" | "md";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  inputSize?: InputSize;
}

const sizeClasses: Record<InputSize, string> = {
  xs: "text-xs px-2 py-1",
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-3 py-1.5",
};

export function Input({ inputSize = "md", className, ...props }: InputProps) {
  return (
    <input
      className={clsx(
        "border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors",
        sizeClasses[inputSize],
        className
      )}
      {...props}
    />
  );
}

interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  inputSize?: InputSize;
}

export function Textarea({
  inputSize = "md",
  className,
  ...props
}: TextareaProps) {
  return (
    <textarea
      className={clsx(
        "border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors resize-none",
        sizeClasses[inputSize],
        className
      )}
      {...props}
    />
  );
}
