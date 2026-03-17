"use client";

import { AlertTriangle } from "lucide-react";
import { CyclicalAlertItem } from "@/lib/types";
import { Amount } from "@/components/ui";

interface Props {
  alerts: CyclicalAlertItem[];
}

export function CyclicalAlertBanner({ alerts }: Props) {
  if (alerts.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
        <span className="text-sm font-semibold text-amber-800">
          Nadchodzące wydatki cykliczne ({alerts.length})
        </span>
      </div>
      <div className="space-y-2">
        {alerts.map((alert, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div>
              <span className="font-medium text-amber-900">{alert.vendor_name}</span>
              {alert.category_name && (
                <span className="text-amber-600 ml-2 text-xs">· {alert.category_name}</span>
              )}
            </div>
            <div className="flex items-center gap-3 text-right">
              <span className="text-amber-700 text-xs">
                za {alert.days_until} {alert.days_until === 1 ? "dzień" : "dni"}
              </span>
              <span className="text-xs text-amber-600">{alert.amount_range_pln}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
