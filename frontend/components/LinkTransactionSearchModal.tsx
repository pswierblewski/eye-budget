"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listUnifiedTransactions, linkBankToReceipt, linkCashToReceipt } from "@/lib/api";
import type { UnifiedTransaction } from "@/lib/types";
import { Modal } from "@/components/ui/Modal";
import { Button, Input, Amount, SourceBadge } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";
import { QueryState, MutationErrorNotice } from "@/components/QueryState";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Paragon (scan) id from the current receipt context. */
  scanId: number;
  /** receipt_transactions.id for POST link body */
  receiptTransactionId: number;
  /** Confirmed paragon total (positive). */
  receiptTotal: number;
  onLinked: () => void;
};

/**
 * Search bank + cash rows (unified) to link the current paragon to a transaction.
 */
export function LinkTransactionSearchModal({
  open,
  onClose,
  scanId,
  receiptTransactionId,
  receiptTotal,
  onLinked,
}: Props) {
  const queryClient = useQueryClient();
  const absTotal = Math.abs(receiptTotal);
  const [search, setSearch] = useState(absTotal.toFixed(2));

  useEffect(() => {
    if (!open) return;
    setSearch(absTotal.toFixed(2));
  }, [open, absTotal]);

  const listQuery = useQuery({
    queryKey: [
      "transactions",
      "link-tx-search",
      search,
      absTotal,
      open,
      scanId,
    ],
    queryFn: () =>
      listUnifiedTransactions({
        search: search.trim() || undefined,
        exclude_receipt: true,
        abs_amount: absTotal,
        limit: 40,
        sort_by: "date",
        sort_dir: "desc",
      }),
    enabled: open && receiptTransactionId > 0,
  });

  const linkMutation = useMutation<unknown, Error, Pick<UnifiedTransaction, "id" | "source_type">>({
    mutationFn: async (row) => {
      if (row.source_type === "bank") {
        return linkBankToReceipt(row.id, receiptTransactionId);
      }
      return linkCashToReceipt(row.id, receiptTransactionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      onLinked();
      onClose();
    },
  });

  const rowAction = (row: UnifiedTransaction) => {
    if (row.source_type === "receipt") return { kind: "skip" as const };
    if (!row.has_receipt) {
      return { kind: "link" as const, row };
    }
    if (row.receipt_scan_id === scanId) {
      return { kind: "current" as const };
    }
    return { kind: "foreign" as const };
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
          Wyszukaj transakcję
        </h2>
        <p className="text-sm text-gray-600">
          Tylko bank i gotówka, kwota ~{absTotal.toFixed(2)} PLN. Dopasuj po
          opisie lub sklepie poniżej.
        </p>
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
              const rows = data.items.filter((r) => r.source_type !== "receipt");
              if (rows.length === 0) {
                return <p className="p-3 text-sm text-gray-500">Brak wyników.</p>;
              }
              return (
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left p-2">Data</th>
                      <th className="text-left p-2">Źródło</th>
                      <th className="text-left p-2">Opis</th>
                      <th className="text-right p-2">Kwota</th>
                      <th className="text-right p-2 w-32">Akcja</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => {
                      const act = rowAction(r);
                      const dim =
                        act.kind === "foreign" || act.kind === "current"
                          ? "opacity-50"
                          : "";
                      return (
                        <tr
                          key={`${r.source_type}-${r.id}`}
                          className={`border-b border-gray-100 ${dim}`}
                        >
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
                          <td className="p-2 text-right align-top">
                            {act.kind === "link" && (
                              <Button
                                type="button"
                                variant="primary"
                                size="sm"
                                disabled={linkMutation.isPending}
                                onClick={() => linkMutation.mutate(act.row)}
                              >
                                {linkMutation.isPending ? "…" : "Powiąż"}
                              </Button>
                            )}
                            {act.kind === "current" && (
                              <span className="text-xs text-gray-600">
                                Aktualne powiązanie
                              </span>
                            )}
                            {act.kind === "foreign" && (
                              <span className="text-xs text-amber-800">Już powiązane</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              );
            }}
          </QueryState>
        </div>
        <MutationErrorNotice
          mutation={linkMutation}
          title="Nie udało się powiązać."
        />
        <div className="flex justify-end">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Zamknij
          </Button>
        </div>
      </div>
    </Modal>
  );
}
