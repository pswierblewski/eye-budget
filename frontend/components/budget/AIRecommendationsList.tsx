"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AIRecommendationsResponse } from "@/lib/types";
import { Button, Amount, StatusBadge } from "@/components/ui";
import { refreshAIRecommendations } from "@/lib/api";
import { RefreshCw } from "lucide-react";

interface Props {
  data: AIRecommendationsResponse;
}

const INSIGHT_TYPE_LABEL: Record<string, string> = {
  saving_opportunity: "Oszczędność",
  goal_advice: "Cele",
  warning: "Uwaga",
  general: "Ogólne",
};

export function AIRecommendationsList({ data }: Props) {
  const queryClient = useQueryClient();

  const refreshMutation = useMutation({
    mutationFn: refreshAIRecommendations,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budget-ai-recommendations"] });
    },
  });

  if (!data.has_sufficient_data) {
    return (
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-6 text-center">
        <p className="text-sm text-blue-700 font-medium">Zbieramy dane</p>
        <p className="text-xs text-blue-600 mt-1">
          Potrzebujemy co najmniej 3 miesięcy transakcji ({data.months_of_data}/3 miesięcy).
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          {data.generated_at && (
            <p className="text-xs text-gray-400">
              Wygenerowano: {new Date(data.generated_at).toLocaleString("pl-PL")}
            </p>
          )}
          {data.data_through_date && (
            <p className="text-xs text-gray-400">Dane do: {data.data_through_date}</p>
          )}
        </div>
        <Button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          variant="secondary"
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          {refreshMutation.isPending ? "Odświeżam…" : "Odśwież"}
        </Button>
      </div>

      {data.insights.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">
          Brak rekomendacji. Kliknij Odśwież, aby wygenerować.
        </p>
      ) : (
        <div className="space-y-3">
          {data.insights.map((insight, i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-semibold text-gray-800 text-sm">{insight.title}</h3>
                <span className="shrink-0 text-xs bg-purple-50 text-purple-600 font-medium px-2 py-0.5 rounded">
                  {INSIGHT_TYPE_LABEL[insight.insight_type] ?? insight.insight_type}
                </span>
              </div>
              <p className="text-sm text-gray-600">{insight.body}</p>
              {insight.amount_pln != null && (
                <div className="mt-2">
                  <Amount value={insight.amount_pln} className="text-sm font-semibold text-[#635bff]" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
