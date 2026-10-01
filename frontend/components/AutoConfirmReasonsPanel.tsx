import type { AutoConfirmReason, AutoConfirmWaiverItem } from "@/lib/types";
import { Button } from "@/components/ui";
import { clsx } from "clsx";

function waiverMatches(reason: AutoConfirmReason, waiver: AutoConfirmWaiverItem): boolean {
  return (
    waiver.code === reason.code &&
    (waiver.product_name ?? null) === (reason.product_name ?? null)
  );
}

function isWaived(reason: AutoConfirmReason, waivers?: AutoConfirmWaiverItem[]): boolean {
  return waivers?.some((w) => waiverMatches(reason, w)) ?? false;
}

/** Stable key for per-row accept loading state (matches mutation variables). */
export function waiverAcceptPendingKey(payload: {
  code: string;
  product_name?: string | null;
}): string {
  return `${payload.code}\0${payload.product_name ?? ""}`;
}

type Props = {
  reasons: AutoConfirmReason[];
  waivers?: AutoConfirmWaiverItem[];
  onAccept?: (payload: { code: string; product_name?: string | null }) => void;
  /** Key of the row currently saving; other rows keep „Akceptuj”. */
  acceptPendingKey?: string | null;
};

export function AutoConfirmReasonsPanel({ reasons, waivers, onAccept, acceptPendingKey }: Props) {
  if (!reasons.some((r) => r.blocking || isWaived(r, waivers))) return null;
  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50/80 p-4 text-sm text-orange-900">
      <p className="font-semibold mb-2">Dlaczego nie potwierdzono automatycznie</p>
      <ul className="space-y-2">
        {reasons.map((r, i) => {
          const waived = isWaived(r, waivers);
          const showAccept = r.blocking && !waived && onAccept;
          const rowKey = waiverAcceptPendingKey({
            code: r.code,
            product_name: r.product_name ?? null,
          });
          const isRowPending = acceptPendingKey === rowKey;
          const anyAcceptPending = acceptPendingKey != null;
          return (
            <li
              key={`${r.code}-${r.product_name ?? ""}-${i}`}
              className={clsx(
                "flex flex-wrap items-center justify-between gap-2",
                (!r.blocking || waived) && "text-orange-700/70"
              )}
            >
              <span>{r.message}</span>
              {waived && (
                <span className="text-xs font-medium text-orange-800/80">Zaakceptowano</span>
              )}
              {showAccept && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={anyAcceptPending}
                  onClick={() =>
                    onAccept({
                      code: r.code,
                      product_name: r.product_name ?? null,
                    })
                  }
                >
                  {isRowPending ? "Zapisuję…" : "Akceptuj"}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
