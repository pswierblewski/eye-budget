"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getBudgetSimulation } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { SimulationResultView } from "@/components/budget/SimulationResultView";
import { getPusher } from "@/lib/pusher";
import { QueryState } from "@/components/QueryState";

export default function SimulationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const simId = parseInt(id, 10);
  const queryClient = useQueryClient();

  const simulationQuery = useQuery({
    queryKey: ["budget-simulation", simId],
    queryFn: () => getBudgetSimulation(simId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 3000;
    },
  });

  useEffect(() => {
    const pusher = getPusher();
    const channel = pusher.subscribe("budget-channel");

    channel.bind("budget.simulation.done", (data: { simulation_id: number }) => {
      if (data.simulation_id === simId) {
        queryClient.invalidateQueries({ queryKey: ["budget-simulation", simId] });
      }
    });

    return () => {
      channel.unbind("budget.simulation.done");
      pusher.unsubscribe("budget-channel");
    };
  }, [simId, queryClient]);

  return (
    <QueryState
      query={simulationQuery}
      errorTitle="Nie udało się pobrać symulacji."
      loadingFallback={
        <div className="flex items-center justify-center py-16">
          <p className="text-sm text-gray-400">Ładowanie…</p>
        </div>
      }
    >
      {(simulation) =>
        simulation ? (
          <div className="max-w-3xl mx-auto w-full space-y-6">
            <PageHeader title={simulation.name} />
            <div className="text-xs text-gray-400 space-x-3">
              <span>Wydatek: {simulation.expense_name}</span>
              <span>·</span>
              <span>
                {simulation.expense_amount_pln.toLocaleString("pl-PL")} PLN
              </span>
              <span>·</span>
              <span>
                {simulation.expense_type === "one_time"
                  ? "Jednorazowy"
                  : "Cykliczny"}
              </span>
              <span>·</span>
              <span>od {simulation.expense_start_date}</span>
            </div>
            <SimulationResultView simulation={simulation} />
          </div>
        ) : (
          <div className="text-sm text-gray-400 py-8 text-center">
            Symulacja nie została znaleziona.
          </div>
        )
      }
    </QueryState>
  );
}
