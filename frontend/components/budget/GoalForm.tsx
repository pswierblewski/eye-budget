"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Input, Button, DateInput } from "@/components/ui";
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
  const [targetAmount, setTargetAmount] = useState(
    goal?.target_amount_pln?.toString() ?? ""
  );
  const [monthlyAlloc, setMonthlyAlloc] = useState(
    goal?.monthly_allocation_amount_pln?.toString() ?? ""
  );
  const [targetDate, setTargetDate] = useState(goal?.target_date ?? "");
  const [priorityRank, setPriorityRank] = useState(
    goal?.priority_rank?.toString() ?? "0"
  );

  const mutation = useMutation({
    mutationFn: () => {
      const data = {
        name,
        target_amount_pln: parseFloat(targetAmount),
        target_date: targetDate || undefined,
        priority_rank: parseInt(priorityRank) || 0,
        monthly_allocation_amount_pln: parseFloat(monthlyAlloc) || 0,
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
    !isNaN(parseFloat(targetAmount)) &&
    parseFloat(targetAmount) > 0;

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
        <Input
          type="number"
          value={targetAmount}
          onChange={(e) => setTargetAmount(e.target.value)}
          placeholder="10000"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Miesięczna alokacja (PLN)
        </label>
        <Input
          type="number"
          value={monthlyAlloc}
          onChange={(e) => setMonthlyAlloc(e.target.value)}
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
        <label className="block text-xs font-medium text-gray-600 mb-1">Priorytet</label>
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
