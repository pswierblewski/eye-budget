"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getBudgetSimulations } from "@/lib/api";
import { PageHeader, Button, Modal, Amount } from "@/components/ui";
import { SimulationForm } from "@/components/budget/SimulationForm";
import { Plus } from "lucide-react";
import clsx from "clsx";
import { QueryState } from "@/components/QueryState";

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  pending: { label: "Oczekuje", cls: "bg-yellow-50 text-yellow-700" },
  processing: { label: "W trakcie", cls: "bg-blue-50 text-blue-700" },
  done: { label: "Gotowe", cls: "bg-green-50 text-green-700" },
  failed: { label: "Błąd", cls: "bg-red-50 text-red-700" },
};

export default function SimulationsPage() {
  const [showForm, setShowForm] = useState(false);

  const listQuery = useQuery({
    queryKey: ["budget-simulations"],
    queryFn: getBudgetSimulations,
  });

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Symulacje budżetu" />
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Nowa symulacja
        </Button>
      </div>

      <QueryState
        query={listQuery}
        errorTitle="Nie udało się pobrać symulacji."
        loadingFallback={<p className="text-sm text-gray-400">Ładowanie…</p>}
      >
        {(simulations) =>
          simulations.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-sm">Brak symulacji.</p>
          <p className="text-xs mt-1">
            Utwórz pierwszą, aby zobaczyć wpływ dużego wydatku na Twój budżet.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {simulations.map((sim) => {
            const cfg = STATUS_CONFIG[sim.status] ?? STATUS_CONFIG.pending;
            return (
              <Link
                key={sim.id}
                href={`/budget/simulations/${sim.id}`}
                className="block rounded-lg border border-gray-200 p-4 hover:border-[#635bff]/40 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-800">{sim.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">{sim.expense_name}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Amount value={sim.expense_amount_pln} className="text-sm font-semibold" />
                    <span className={clsx("text-xs font-medium px-2 py-0.5 rounded", cfg.cls)}>
                      {cfg.label}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  <span>
                    {sim.expense_type === "one_time" ? "Jednorazowy" : "Cykliczny"}
                  </span>
                  <span>·</span>
                  <span>{sim.expense_start_date}</span>
                  <span>·</span>
                  <span>{new Date(sim.created_at).toLocaleDateString("pl-PL")}</span>
                </div>
              </Link>
            );
          })}
        </div>
        )
        }
      </QueryState>

      <Modal open={showForm} onClose={() => setShowForm(false)}>
        <div className="p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Nowa symulacja budżetu</h2>
          <SimulationForm onSuccess={() => setShowForm(false)} />
        </div>
      </Modal>
    </div>
  );
}
