import { clsx } from "clsx";

type Props = {
  count: number;
  className?: string;
};

/**
 * Member count for settlement groups. Zero uses muted styling (empty group), not an error.
 */
export function SettlementGroupBadge({ count, className }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex min-w-[1.5rem] justify-center rounded-full px-1.5 py-0.5 text-xs font-medium",
        count === 0
          ? "bg-gray-100 text-gray-500"
          : "bg-violet-100 text-violet-800",
        className
      )}
      title="Liczba operacji w zestawie"
    >
      {count}
    </span>
  );
}
