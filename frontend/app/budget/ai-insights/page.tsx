"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getAIRecommendations } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { AIRecommendationsList } from "@/components/budget/AIRecommendationsList";
import { getPusher } from "@/lib/pusher";

export default function AIInsightsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["budget-ai-recommendations"],
    queryFn: getAIRecommendations,
  });

  useEffect(() => {
    const pusher = getPusher();
    const channel = pusher.subscribe("budget-channel");

    channel.bind("budget.recommendations.done", () => {
      queryClient.invalidateQueries({ queryKey: ["budget-ai-recommendations"] });
    });

    return () => {
      channel.unbind("budget.recommendations.done");
      pusher.unsubscribe("budget-channel");
    };
  }, [queryClient]);

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      <PageHeader title="Rekomendacje AI" />
      {isLoading ? (
        <p className="text-sm text-gray-400">Ładowanie rekomendacji…</p>
      ) : data ? (
        <AIRecommendationsList data={data} />
      ) : (
        <p className="text-sm text-gray-400">Brak danych.</p>
      )}
    </div>
  );
}
