"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listUnifiedTransactions, createSettlementGroup } from "@/lib/api";
import type { UnifiedTransaction } from "@/lib/types";
import { Modal } from "@/components/ui/Modal";
import { Button, Input } from "@/components/ui";
import { Amount, SourceBadge } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Current row (bank or cash) — always included in the new group. */
  current: { source_type: "bank" | "cash"; id: number };
  onCreated: (groupId: number) => void;
};

function keyOf(t: Pick<UnifiedTransaction, "source_type" | "id">) {
  return `${t.source_type}:${t.id}`;
}

/**
 * Create a settlement group from the current transaction + at least one other
 * bank/cash row (≥2 total). Uses the unified list search.
 */
export function LinkOperationsModal({ open, onClose, current, onCreated }: Props) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSubmitError(null);
  }, [open]);

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", "link-ops", search],
    queryFn: () =>
      listUnifiedTransactions({
        limit: 40,
        search: search || undefined,
        source_type: undefined,
        sort_by: "date",
        sort_dir: "desc",
      }),
    enabled: open,
  });

  const rows = useMemo(() => {
    const list = data?.items ?? [];
    return list.filter(
      (r) =>
        (r.source_type === "bank" || r.source_type === "cash") &&
        !(r.source_type === current.source_type && r.id === current.id)
    );
  }, [data?.items, current.id, current.source_type]);

  const toggle = (r: UnifiedTransaction) => {
    const k = keyOf(r);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  };

  const membersPayload = useMemo(() => {
    const m: { source_type: "bank" | "cash"; id: number }[] = [
      { source_type: current.source_type, id: current.id },
    ];
    for (const k of Array.from(selected)) {
      const [st, idStr] = k.split(":");
      if (st !== "bank" && st !== "cash") continue;
      m.push({ source_type: st, id: Number(idStr) });
    }
    return m;
  }, [current, selected]);

  const canSubmit = membersPayload.length >= 2;

  const handleCreate = async () => {
    if (!canSubmit || isSubmitting) return;
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const g = await createSettlementGroup({ members: membersPayload });
      onCreated(g.id);
      setSelected(new Set());
      setSearch("");
      onClose();
    } catch (e) {
      const raw = e instanceof Error ? e.message : "";
      if (raw.includes("API 409:")) {
        setSubmitError(
          "Jedna z wybranych transakcji jest już w innym zestawie powiązanych operacji."
        );
      } else if (raw.includes("API 400:")) {
        setSubmitError(
          "Co najmniej jedna z wybranych operacji nie istnieje lub jest nieprawidłowa."
        );
      } else {
        setSubmitError("Nie udało się utworzyć grupy. Spróbuj ponownie.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} className="max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
      <div className="p-4 space-y-3 flex flex-col min-h-0 flex-1">
        <h2 className="text-lg font-semibold text-gray-900">
          Utwórz powiązane operacje
        </h2>
        <p className="text-sm text-gray-600">
          Zaznacz co najmniej jedną dodatkową operację (obok bieżącej). Łącznie
          muszą być co najmniej dwie.
        </p>
        <div className="rounded-lg border border-violet-100 bg-violet-50/40 p-2 text-sm">
          <span className="text-gray-600">Przypięta (bieżąca): </span>
          <span className="font-medium">
            {current.source_type === "bank" ? "Bank" : "Gotówka"} #{current.id}
          </span>
        </div>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Szukaj po opisie lub sklepie…"
        />
        <div className="border rounded-lg overflow-y-auto flex-1 min-h-[200px]">
          {isLoading && (
            <p className="p-3 text-sm text-gray-500">Ładowanie…</p>
          )}
          {!isLoading && rows.length === 0 && (
            <p className="p-3 text-sm text-gray-500">Brak wyników.</p>
          )}
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="text-left p-2 w-10" />
                <th className="text-left p-2">Data</th>
                <th className="text-left p-2">Źródło</th>
                <th className="text-left p-2">Opis</th>
                <th className="text-right p-2">Kwota</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const k = keyOf(r);
                const on = selected.has(k);
                return (
                  <tr
                    key={k}
                    className={on ? "bg-violet-50" : "hover:bg-gray-50"}
                  >
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(r)}
                        aria-label="Wybierz"
                      />
                    </td>
                    <td className="p-2 font-mono text-xs whitespace-nowrap">
                      {isoToDisplay(r.date)}
                    </td>
                    <td className="p-2">
                      <SourceBadge source={r.source_type} />
                    </td>
                    <td className="p-2 max-w-xs truncate">
                      {r.vendor_name ?? r.description ?? "—"}
                    </td>
                    <td className="p-2 text-right whitespace-nowrap">
                      <Amount value={r.amount} currency={r.currency} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {submitError && (
          <p className="text-sm text-red-600" role="alert">
            {submitError}
          </p>
        )}
        <div className="flex justify-end items-center gap-2 flex-wrap">
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
              Anuluj
            </Button>
            <Button
              variant="primary"
              disabled={!canSubmit || isSubmitting}
              onClick={() => void handleCreate()}
            >
              {isSubmitting ? "Tworzenie…" : "Utwórz grupę"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
