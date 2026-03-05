import React from "react";
import Link from "next/link";
import { ArrowRight, ArrowLeft } from "lucide-react";
import { clsx } from "clsx";

interface NavLinkProps {
  href: string;
  label: string;
  variant: "forward" | "back";
  className?: string;
  onClick?: (e: React.MouseEvent) => void;
  size?: "xs" | "sm";
}

export function NavLink({
  href,
  label,
  variant,
  className,
  onClick,
  size = "xs",
}: NavLinkProps) {
  const baseClasses = "inline-flex items-center gap-1 transition-colors";

  if (variant === "forward") {
    return (
      <Link
        href={href}
        onClick={onClick}
        className={clsx(
          baseClasses,
          size === "xs"
            ? "text-xs text-accent hover:underline"
            : "text-sm text-accent hover:underline",
          className
        )}
      >
        {label}
        <ArrowRight className="h-3 w-3" />
      </Link>
    );
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      className={clsx(
        baseClasses,
        "text-sm text-gray-500 hover:text-gray-700",
        className
      )}
    >
      <ArrowLeft className="h-4 w-4" />
      {label}
    </Link>
  );
}
