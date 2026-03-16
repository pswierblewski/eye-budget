"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBudgetGoals, getBudgetSurplus } from "@/lib/api";
import { PageHeader, SectionLabel, Button, Modal, Amount } from "@/components/ui";
import { GoalCard } from "@/components/budget/GoalCard";
import { GoalForm } from "@/components/budget/GoalForm";
import { FinancialGoalListItem } from "@/lib/types";
import { Plus } from "lucide-react";

export default function GoalsPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingGoal, setEditingGoal] = useState<FinancialGoalListItem | null>(null);

  const { data: goals = [], isLoading: loadingGoals } = useQuery({
    queryKey: ["budget-goals"],
    queryFn: getBudgetGoals,
  });

  const { data: surplus, isLoading: loadingSurplus } = useQuery({
    queryKey: ["budget-surplus"],
    queryFn: getBudgetSurplus,
  });

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Cele finansowe" />
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Nowy cel
        </Button>
      </div>

      {/* Surplus summary */}
      {surplus && (
        <div className="rounded-lg border border-gray-200 p-5">
          <SectionLabel>Miesięczna nadwyżka</SectionLabel>
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <p className="text-xs text-gray-400">Śr. nadwyżka (3 mies.)</p>
              <Amount
                value={surplus.avg_surplus_3m_pln}
                className={`text-lg font-bold ${surplus.avg_surplus_3m_pln >= 0 ? "text-green-600" : "text-red-500"}`}
              />
            </div>
            <div>
              <p className="text-xs text-gray-400">Nadwyżka w tym miesiącu</p>
              <Amount
                value={surplus.current_month_surplus_pln}
                className={`text-lg font-bold ${surplus.current_month_surplus_pln >= 0 ? "text-[#635bff]" : "text-red-500"}`}
              />
            </div>
            <div>
              <p className="text-xs text-gray-400">Łączne alokacje na cele</p>
              <Amount value={surplus.total_monthly_goal_allocations_pln} className="text-sm font-semibold" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Wolna nadwyżka</p>
              <Amount
                value={surplus.unallocated_surplus_pln}
                className={`text-sm font-semibold ${surplus.unallocated_surplus_pln >= 0 ? "text-green-600" : "text-red-500"}`}
              />
            </div>
          </div>
        </div>
      )}

      {/* Goals list */}
      {loadingGoals ? (
        <p className="text-sm text-gray-400">Ładowanie celów…</p>
      ) : goals.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-sm">Brak aktywnych celów.</p>
          <p className="text-xs mt-1">Dodaj swój pierwszy cel finansowy!</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} onEdit={setEditingGoal} />
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal open={showCreateModal} onClose={() => setShowCreateModal(false)}>
        <div className="p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Nowy cel finansowy</h2>
          <GoalForm onSuccess={() => setShowCreateModal(false)} />
        </div>
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editingGoal} onClose={() => setEditingGoal(null)}>
        <div className="p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Edytuj cel</h2>
          {editingGoal && (
            <GoalForm goal={editingGoal} onSuccess={() => setEditingGoal(null)} />
          )}
        </div>
      </Modal>
    </div>
  );
}
