"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listReceipts, linkBankToReceipt, linkCashToReceipt } from "@/lib/api";
import type { ReceiptScanListItem } from "@/lib/types";
import { Modal } from "@/components/ui/Modal";
import { Button, Input } from "@/components/ui";
import { Amount } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";
import { QueryState, MutationErrorNotice } from "@/components/QueryState";
import Link from "next/link";

type Props = {
  open: boolean;
  onClose: () => void;
  anchorType: "bank" | "cash";
  transactionId: number;
  /** Signed amount from the bank/cash row; |amount| is used for list filters. */
  amount: number;
  onLinked: () => void;
};

/**
 * Search any receipt (with shop/vendor search + exact total filter) to link
 * to the current bank or cash transaction.
 */
export function LinkReceiptSearchModal({
  open,
  onClose,
  anchorType,
  transactionId,
  amount,
  onLinked,
}: Props) {
  const queryClient = useQueryClient();
  const absTotal = Math.abs(amount);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) return;
    setSearch("");
  }, [open, amount]);

  const listQuery = useQuery({
    queryKey: [
      "receipts",
      "link-receipt-search",
      search,
      absTotal,
      open,
    ],
    queryFn: () =>
      listReceipts({
        search: search.trim() || undefined,
        total_min: absTotal,
        total_max: absTotal,
        limit: 40,
        sort_by: "date",
        sort_dir: "desc",
      }),
    enabled: open,
  });

  const linkMutation = useMutation<unknown, Error, number>({
    mutationFn: async (receiptTransactionId) => {
      if (anchorType === "bank") {
        return linkBankToReceipt(transactionId, receiptTransactionId);
      }
      return linkCashToReceipt(transactionId, receiptTransactionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({
        queryKey: ["bank-transaction", transactionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["cash-transaction", transactionId],
      });
      onLinked();
      onClose();
    },
  });

  const rowState = (row: ReceiptScanListItem) => {
    if (row.receipt_transaction_id == null) {
      return { kind: "no_tx" as const };
    }
    if (row.has_transaction_link) {
      return { kind: "linked" as const };
    }
    return { kind: "ok" as const, receiptTransactionId: row.receipt_transaction_id };
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      maxWidth="4xl"
      className="max-h-[90vh] overflow-hidden flex flex-col w-full"
    >
      <div className="p-4 space-y-3 flex flex-col min-h-0 flex-1">
        <h2 className="text-lg font-semibold text-gray-900">Wyszukaj paragon</h2>
        <p className="text-sm text-gray-600">
          Filtrowanie po kwocie {absTotal.toFixed(2)} PLN. Możesz zawęzić po nazwie pliku
          lub sklepie w polu poniżej.
        </p>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Szukaj po nazwie pliku lub sklepie…"
        />
        <div className="border rounded-lg overflow-x-auto overflow-y-auto flex-1 min-h-[200px]">
          <QueryState
            query={listQuery}
            errorTitle="Nie udało się pobrać listy paragonów."
            loadingFallback={
              <p className="p-3 text-sm text-gray-500">Ładowanie…</p>
            }
          >
            {(data) => {
              const items = data.items;
              if (items.length === 0) {
                return <p className="p-3 text-sm text-gray-500">Brak wyników.</p>;
              }
              return (
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left p-2">Sklep / plik</th>
                      <th className="text-left p-2">Data</th>
                      <th className="text-right p-2">Suma</th>
                      <th className="text-right p-2 w-36">Akcja</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((row) => {
                      const st = rowState(row);
                      const dim =
                        st.kind === "linked" || st.kind === "no_tx"
                          ? "opacity-50"
                          : "";
                      return (
                        <tr key={row.id} className={`border-b border-gray-100 ${dim}`}>
                          <td className="p-2 align-top">
                            <div className="font-medium text-gray-800 truncate max-w-xs">
                              {row.vendor ?? row.filename}
                            </div>
                            <div className="text-xs text-gray-400 font-mono truncate">
                              {row.filename}
                            </div>
                          </td>
                          <td className="p-2 text-xs font-mono whitespace-nowrap">
                            {row.date ? isoToDisplay(row.date) : "—"}
                          </td>
                          <td className="p-2 text-right">
                            {row.total != null ? (
                              <Amount value={row.total} currency="PLN" />
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="p-2 text-right">
                            {st.kind === "no_tx" && (
                              <span className="text-xs text-gray-500">
                                Paragon wymaga potwierdzenia
                              </span>
                            )}
                            {st.kind === "linked" && (
                              <span className="text-xs text-amber-700">Już powiązane</span>
                            )}
                            {st.kind === "ok" && (
                              <Button
                                type="button"
                                variant="primary"
                                size="sm"
                                disabled={linkMutation.isPending}
                                onClick={() =>
                                  linkMutation.mutate(st.receiptTransactionId)
                                }
                              >
                                {linkMutation.isPending ? "…" : "Powiąż"}
                              </Button>
                            )}
                            <div className="mt-1">
                              <Link
                                href={`/receipts/${row.id}`}
                                className="text-xs text-violet-600 hover:underline"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Otwórz
                              </Link>
                            </div>
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
        <MutationErrorNotice mutation={linkMutation} title="Nie udało się powiązać." />
        <div className="flex justify-end">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Zamknij
          </Button>
        </div>
      </div>
    </Modal>
  );
}
