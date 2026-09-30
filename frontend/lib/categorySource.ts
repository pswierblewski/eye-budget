export type CategorySourceInfo = {
  source?: "history" | "ai" | null;
  history_count?: number | null;
  topScore?: number | null;
};

export function categorySourceLabel(info: CategorySourceInfo): string | null {
  if (info.source === "history") return `z historii (${info.history_count ?? 0}×)`;
  if (info.source === "ai") {
    if (info.topScore == null) return "AI";
    const percent = Math.round(info.topScore > 1 ? info.topScore : info.topScore * 100);
    return `AI · ${percent}%`;
  }
  return null;
}
