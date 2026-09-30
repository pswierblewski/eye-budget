import type { AutoConfirmReason } from "@/lib/types";
import { clsx } from "clsx";

export function AutoConfirmReasonsPanel({ reasons }: { reasons: AutoConfirmReason[] }) {
  if (!reasons.some((r) => r.blocking)) return null;
  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50/80 p-4 text-sm text-orange-900">
      <p className="font-semibold mb-2">Dlaczego nie potwierdzono automatycznie</p>
      <ul className="list-disc pl-5 space-y-1">
        {reasons.map((r, i) => (
          <li key={`${r.code}-${i}`} className={clsx(!r.blocking && "text-orange-700/70")}>
            {r.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
