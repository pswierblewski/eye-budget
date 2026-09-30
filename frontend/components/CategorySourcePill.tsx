import { Pill } from "@/components/ui";
import { categorySourceLabel, type CategorySourceInfo } from "@/lib/categorySource";

export function CategorySourcePill(props: CategorySourceInfo) {
  const label = categorySourceLabel(props);
  if (!label) return null;
  return (
    <Pill variant={props.source === "history" ? "category-primary" : "category-secondary"} size="sm">
      {label}
    </Pill>
  );
}
