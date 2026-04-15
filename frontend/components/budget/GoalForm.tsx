"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Input, Button, DateInput, Tooltip, AmountInput } from "@/components/ui";
import { Info } from "lucide-react";
import { createGoal, updateGoal } from "@/lib/api";
import { FinancialGoalListItem } from "@/lib/types";

interface Props {
  goal?: FinancialGoalListItem;
  onSuccess?: () => void;
}

export function GoalForm({ goal, onSuccess }: Props) {
  const queryClient = useQueryClient();
  const isEdit = !!goal;

  const [name, setName] = useState(goal?.name ?? "");
  const [targetAmount, setTargetAmount] = useState<number | null>(
    goal?.target_amount_pln ?? null
  );
  const [monthlyAlloc, setMonthlyAlloc] = useState<number | null>(
    goal?.monthly_allocation_amount_pln ?? null
  );
  const [targetDate, setTargetDate] = useState(goal?.target_date ?? "");
  const [priorityRank, setPriorityRank] = useState(
    goal?.priority_rank?.toString() ?? "0"
  );

  const mutation = useMutation({
    mutationFn: () => {
      const data = {
        name,
        target_amount_pln: targetAmount ?? 0,
        target_date: targetDate || undefined,
        priority_rank: parseInt(priorityRank) || 0,
        monthly_allocation_amount_pln: monthlyAlloc ?? 0,
      };
      return isEdit ? updateGoal(goal!.id, data) : createGoal(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budget-goals"] });
      queryClient.invalidateQueries({ queryKey: ["budget-surplus"] });
      onSuccess?.();
    },
  });

  const canSubmit =
    name.trim() !== "" &&
    targetAmount !== null &&
    targetAmount > 0;

  return (
    <div className="space-y-4 p-1">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Nazwa celu</label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="np. Fundusz awaryjny"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Kwota docelowa (PLN)</label>
        <AmountInput
          value={targetAmount}
          onChange={setTargetAmount}
          placeholder="10000"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Miesięczna alokacja (PLN)
        </label>
        <AmountInput
          value={monthlyAlloc}
          onChange={setMonthlyAlloc}
          placeholder="500"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Data docelowa (opcjonalnie)
        </label>
        <DateInput value={targetDate} onChange={setTargetDate} />
      </div>
      <div>
        <label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">
          Priorytet
          <Tooltip content="Niższy numer oznacza wyższy priorytet. Priorytet 1 to cel najważniejszy, wyższe liczby oznaczają mniejsze znaczenie (np. 5 = cel drugorzędny).">
            <span tabIndex={0} className="inline-flex cursor-help focus:outline-none">
              <Info className="w-3.5 h-3.5 text-gray-400" />
            </span>
          </Tooltip>
        </label>
        <Input
          type="number"
          value={priorityRank}
          onChange={(e) => setPriorityRank(e.target.value)}
          placeholder="0"
        />
      </div>
      {mutation.isError && (
        <p className="text-red-500 text-sm">
          Błąd: {(mutation.error as Error).message}
        </p>
      )}
      <Button
        onClick={() => mutation.mutate()}
        disabled={!canSubmit || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending ? "Zapisuję…" : isEdit ? "Zapisz zmiany" : "Dodaj cel"}
      </Button>
    </div>
  );
}
