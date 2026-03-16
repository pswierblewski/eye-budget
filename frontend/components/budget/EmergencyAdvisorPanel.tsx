"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { Input, Button, Amount } from "@/components/ui";
import { getEmergencyAdvice } from "@/lib/api";
import { EmergencyAdvisorResponse } from "@/lib/types";

export function EmergencyAdvisorPanel() {
  const [amountStr, setAmountStr] = useState("");
  const [description, setDescription] = useState("");
  const [result, setResult] = useState<EmergencyAdvisorResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      getEmergencyAdvice(parseFloat(amountStr), description || undefined),
    onSuccess: (data) => setResult(data),
  });

  const amount = parseFloat(amountStr);
  const canSubmit = !isNaN(amount) && amount > 0;

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <Input
          type="number"
          placeholder="Kwota wydatku (PLN)"
          value={amountStr}
          onChange={(e) => setAmountStr(e.target.value)}
          className="max-w-[160px]"
        />
        <Input
          placeholder="Opis (opcjonalnie)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="flex-1"
        />
        <Button
          onClick={() => mutation.mutate()}
          disabled={!canSubmit || mutation.isPending}
        >
          {mutation.isPending ? "Analizuję…" : "Analizuj"}
        </Button>
      </div>

      {!result && !mutation.isPending && (
        <p className="text-sm text-gray-400">
          Podaj kwotę nieoczekiwanego wydatku, aby zobaczyć możliwe cięcia i wpływ na cele.
        </p>
      )}

      {mutation.isError && (
        <p className="text-red-500 text-sm">Błąd: {(mutation.error as Error).message}</p>
      )}

      {result && (
        <div className="mt-3 space-y-4">
          <div
            className={clsx(
              "rounded-lg border p-3 text-sm font-medium",
              result.fully_coverable_by_cuts
                ? "bg-green-50 border-green-200 text-green-800"
                : "bg-red-50 border-red-200 text-red-800"
            )}
          >
            {result.fully_coverable_by_cuts
              ? `Kwotę ${result.amount_pln.toFixed(0)} PLN można pokryć przez cięcia`
              : `Cięcia nie pokryją w pełni ${result.amount_pln.toFixed(0)} PLN`}
          </div>

          <p className="text-sm text-gray-700">{result.narrative}</p>

          {result.discretionary_cuts.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Możliwe cięcia wydatków uznaniowych
              </h4>
              <div className="space-y-2">
                {result.discretionary_cuts.map((cut, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-gray-100">
                    <span className="text-gray-700">{cut.category_name}</span>
                    <div className="flex items-center gap-4 text-right">
                      <div>
                        <Amount value={cut.avg_monthly_spend_pln} className="text-sm font-medium" />
                        <p className="text-xs text-gray-400">/mies.</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">{cut.months_to_cover} mies. cięcia</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-sm font-medium">
                <span>Łącznie możliwe do wycięcia</span>
                <Amount value={result.total_cuttable_pln} />
              </div>
            </div>
          )}

          {result.goal_impacts.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Wpływ na cele finansowe
              </h4>
              <div className="space-y-2">
                {result.goal_impacts.map((gi) => (
                  <div key={gi.goal_id} className="text-sm">
                    <span className="font-medium text-gray-700">{gi.goal_name}</span>
                    <p className="text-xs text-gray-500 mt-0.5">{gi.impact_description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.recovery_months !== null && (
            <p className="text-sm text-gray-600">
              Szacowany czas pokrycia wydatku przez cięcia:{" "}
              <span className="font-semibold">{result.recovery_months} miesięcy</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
