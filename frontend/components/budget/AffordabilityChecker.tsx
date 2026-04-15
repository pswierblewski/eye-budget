"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { AmountInput, Button, Amount } from "@/components/ui";
import { checkAffordability } from "@/lib/api";
import { AffordabilityCheckResponse } from "@/lib/types";

const VERDICT_CONFIG = {
  green: {
    label: "Tak, możesz sobie pozwolić",
    bg: "bg-green-50 border-green-200",
    text: "text-green-800",
    badge: "bg-green-100 text-green-700",
  },
  yellow: {
    label: "Ostrożnie – naruszysz bufor",
    bg: "bg-amber-50 border-amber-200",
    text: "text-amber-800",
    badge: "bg-amber-100 text-amber-700",
  },
  red: {
    label: "Nie stać Cię na to teraz",
    bg: "bg-red-50 border-red-200",
    text: "text-red-800",
    badge: "bg-red-100 text-red-700",
  },
};

export function AffordabilityChecker() {
  const [amount, setAmount] = useState<number | null>(null);
  const [result, setResult] = useState<AffordabilityCheckResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => checkAffordability(amount!),
    onSuccess: (data) => setResult(data),
  });

  const canSubmit = amount !== null && amount > 0;

  const cfg = result ? VERDICT_CONFIG[result.verdict] : null;

  return (
    <div>
      <div className="flex gap-2">
        <AmountInput
          value={amount}
          onChange={setAmount}
          placeholder="Kwota w PLN"
          className="max-w-[160px]"
        />
        <Button
          onClick={() => mutation.mutate()}
          disabled={!canSubmit || mutation.isPending}
        >
          {mutation.isPending ? "Sprawdzam…" : "Sprawdź"}
        </Button>
      </div>

      {mutation.isError && (
        <p className="text-red-500 text-sm mt-2">
          Błąd: {(mutation.error as Error).message}
        </p>
      )}

      {result && cfg && (
        <div className={clsx("mt-3 rounded-lg border p-4", cfg.bg)}>
          <div className="flex items-center gap-2 mb-2">
            <span className={clsx("text-xs font-semibold px-2 py-1 rounded", cfg.badge)}>
              {cfg.label}
            </span>
            {result.financial_focus_label && (
              <span className="text-xs text-gray-500">· {result.financial_focus_label}</span>
            )}
          </div>
          <p className={clsx("text-sm mb-3", cfg.text)}>{result.narrative}</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-gray-400">Dostępne w miesiącu</p>
              <Amount value={result.available_this_month_pln} className="font-semibold text-sm" />
            </div>
            <div>
              <p className="text-gray-400">Nadchodzące zobowiązania (30d)</p>
              <Amount value={result.upcoming_obligations_30d_pln} className="font-semibold text-sm" />
            </div>
            <div>
              <p className="text-gray-400">Alokacje na cele</p>
              <Amount value={result.active_goal_allocations_pln} className="font-semibold text-sm" />
            </div>
            <div>
              <p className="text-gray-400">Swobodne środki</p>
              <Amount
                value={result.freely_available_pln}
                className={clsx(
                  "font-semibold text-sm",
                  result.freely_available_pln >= 0 ? "text-green-600" : "text-red-600"
                )}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
