"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FinancialGoalListItem } from "@/lib/types";
import { Amount, ThreeDotsMenu, ConfirmDeleteModal } from "@/components/ui";
import { deleteGoal } from "@/lib/api";
import { useState } from "react";

interface Props {
  goal: FinancialGoalListItem;
  onEdit: (goal: FinancialGoalListItem) => void;
}

export function GoalCard({ goal, onEdit }: Props) {
  const queryClient = useQueryClient();
  const [showConfirm, setShowConfirm] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteGoal(goal.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budget-goals"] });
    },
  });

  const progressPct = Math.min(100, goal.progress_pct);

  return (
    <>
      <div className="border border-gray-200 rounded-lg p-4 bg-white">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-800">{goal.name}</h3>
            {goal.target_date && (
              <p className="text-xs text-gray-400 mt-0.5">Termin: {goal.target_date}</p>
            )}
          </div>
          <ThreeDotsMenu
            items={[
              { label: "Edytuj", onClick: () => onEdit(goal) },
              {
                label: "Usuń",
                onClick: () => setShowConfirm(true),
                variant: "danger",
              },
            ]}
          />
        </div>

        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Postęp</span>
            <span>{progressPct.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#635bff] rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-gray-400">Cel</p>
            <Amount value={goal.target_amount_pln} className="font-semibold text-sm" />
          </div>
          <div>
            <p className="text-gray-400">Zebrano</p>
            <Amount value={goal.accumulated_progress_pln} className="font-semibold text-sm" />
          </div>
          <div>
            <p className="text-gray-400">Mies. alokacja</p>
            <Amount value={goal.monthly_allocation_amount_pln} className="font-semibold text-sm" />
          </div>
        </div>

        {goal.projected_completion_date && (
          <p className="text-xs text-gray-400 mt-2">
            Przewidywane ukończenie: {goal.projected_completion_date}
            {goal.months_to_completion !== null && goal.months_to_completion !== undefined && (
              <span className="ml-1">
                ({goal.months_to_completion} {goal.months_to_completion === 1 ? "miesiąc" : "miesięcy"})
              </span>
            )}
          </p>
        )}
      </div>

      <ConfirmDeleteModal
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          deleteMutation.mutate();
          setShowConfirm(false);
        }}
        title="Usuń cel"
        description={`Czy na pewno chcesz usunąć cel "${goal.name}"?`}
      />
    </>
  );
}
