import React from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { clsx } from "clsx";

interface PrevNextNavProps {
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  prevTitle?: string;
  nextTitle?: string;
  className?: string;
}

export function PrevNextNav({
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  prevTitle = "Poprzedni",
  nextTitle = "Następny",
  className,
}: PrevNextNavProps) {
  return (
    <div className={clsx("flex items-center gap-1", className)}>
      <button
        onClick={onPrev}
        disabled={!hasPrev}
        title={prevTitle}
        className="p-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
      </button>
      <button
        onClick={onNext}
        disabled={!hasNext}
        title={nextTitle}
        className="p-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
