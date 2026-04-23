"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listUnifiedTransactions, createSettlementGroup } from "@/lib/api";
import type { UnifiedTransaction } from "@/lib/types";
import { Modal } from "@/components/ui/Modal";
import { Button, Input } from "@/components/ui";
import { Amount, SourceBadge } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";
import { QueryState } from "@/components/QueryState";

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
  /** Extra members (not the anchor) — key → row snapshot for display. */
  const [extraPinned, setExtraPinned] = useState<Record<string, UnifiedTransaction>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSubmitError(null);
    setExtraPinned({});
    setSearch("");
  }, [open]);

  const listQuery = useQuery({
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

  const toggle = (r: UnifiedTransaction) => {
    const k = keyOf(r);
    setExtraPinned((prev) => {
      const next = { ...prev };
      if (k in next) delete next[k];
      else next[k] = r;
      return next;
    });
  };

  const unpin = (k: string) => {
    setExtraPinned((prev) => {
      const next = { ...prev };
      delete next[k];
      return next;
    });
  };

  const membersPayload = useMemo(() => {
    const m: { source_type: "bank" | "cash"; id: number }[] = [
      { source_type: current.source_type, id: current.id },
    ];
    for (const t of Object.values(extraPinned)) {
      if (t.source_type === "receipt") continue;
      m.push({ source_type: t.source_type, id: t.id });
    }
    const seen = new Set<string>();
    const out: typeof m = [];
    for (const x of m) {
      const s = `${x.source_type}:${x.id}`;
      if (seen.has(s)) continue;
      seen.add(s);
      out.push(x);
    }
    return out;
  }, [current, extraPinned]);

  const canSubmit = membersPayload.length >= 2;

  const handleCreate = async () => {
    if (!canSubmit || isSubmitting) return;
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const g = await createSettlementGroup({ members: membersPayload });
      onCreated(g.id);
      setExtraPinned({});
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
    <Modal
      open={open}
      onClose={onClose}
      maxWidth="4xl"
      className="max-h-[90vh] overflow-hidden flex flex-col w-full"
    >
      <div className="p-4 space-y-3 flex flex-col min-h-0 flex-1">
        <h2 className="text-lg font-semibold text-gray-900">
          Utwórz powiązane operacje
        </h2>
        <p className="text-sm text-gray-600">
          Zaznacz co najmniej jedną dodatkową operację (obok bieżącej). Łącznie
          muszą być co najmniej dwie.
        </p>
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">
            Przypięte
          </div>
          <div className="rounded-lg border border-violet-100 bg-violet-50/40 divide-y max-h-40 overflow-y-auto">
            <div className="p-2 flex flex-wrap items-center justify-between gap-2 text-sm">
              <span>
                <span className="text-gray-600">Bieżąca: </span>
                <span className="font-medium">
                  {current.source_type === "bank" ? "Bank" : "Gotówka"} #{current.id}
                </span>
              </span>
            </div>
            {Object.entries(extraPinned).map(([k, t]) => (
              <div
                key={k}
                className="p-2 flex flex-wrap items-center justify-between gap-2 text-sm"
              >
                <span>
                  {t.source_type === "bank" ? "Bank" : "Gotówka"} #{t.id}
                  {t.vendor_name || t.description
                    ? ` — ${t.vendor_name ?? t.description ?? ""}`
                    : ""}
                </span>
                <Button type="button" variant="secondary" size="sm" onClick={() => unpin(k)}>
                  Usuń z przypiętych
                </Button>
              </div>
            ))}
          </div>
        </div>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Szukaj po opisie lub sklepie…"
        />
        <div className="border rounded-lg overflow-x-auto overflow-y-auto flex-1 min-h-[200px]">
          <QueryState
            query={listQuery}
            errorTitle="Nie udało się pobrać transakcji."
            loadingFallback={
              <p className="p-3 text-sm text-gray-500">Ładowanie…</p>
            }
          >
            {(data) => {
              const rows = data.items.filter(
                (r) =>
                  (r.source_type === "bank" || r.source_type === "cash") &&
                  !(r.source_type === current.source_type && r.id === current.id)
              );
              return (
                <>
                  {rows.length === 0 && (
                    <p className="p-3 text-sm text-gray-500">Brak wyników.</p>
                  )}
                  <table className="w-full min-w-[640px] text-sm">
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
                        const on = k in extraPinned;
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
                </>
              );
            }}
          </QueryState>
        </div>
        {submitError && (
          <p className="text-sm text-red-600" role="alert">
            {submitError}
          </p>
        )}
        <div className="flex justify-end items-center gap-2 flex-wrap">
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Anuluj
            </Button>
            <Button
              variant="primary"
              size="sm"
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
