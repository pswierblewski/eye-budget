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

type Props = {
  reasons: AutoConfirmReason[];
  waivers?: AutoConfirmWaiverItem[];
  onAccept?: (payload: { code: string; product_name?: string | null }) => void;
  acceptPending?: boolean;
};

export function AutoConfirmReasonsPanel({ reasons, waivers, onAccept, acceptPending }: Props) {
  if (!reasons.some((r) => r.blocking || isWaived(r, waivers))) return null;
  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50/80 p-4 text-sm text-orange-900">
      <p className="font-semibold mb-2">Dlaczego nie potwierdzono automatycznie</p>
      <ul className="space-y-2">
        {reasons.map((r, i) => {
          const waived = isWaived(r, waivers);
          const showAccept = r.blocking && !waived && onAccept;
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
                  disabled={acceptPending}
                  onClick={() =>
                    onAccept({
                      code: r.code,
                      product_name: r.product_name ?? null,
                    })
                  }
                >
                  {acceptPending ? "Zapisuję…" : "Akceptuj"}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
