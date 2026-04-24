"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  getCashTransaction,
  getCashReceiptCandidates,
  linkCashToReceipt,
  unlinkCashTransaction,
} from "@/lib/api";
import { ReceiptCandidateItem } from "@/lib/types";
import { isoToDisplay } from "@/lib/utils";
import { LinkReceiptSearchModal } from "@/components/LinkReceiptSearchModal";
import {
  PageHeader,
  NavLink,
  Amount,
  Card,
  SectionLabel,
  Pill,
  SourceBadge,
  Button,
  MatchBadge,
} from "@/components/ui";
import { SettlementOperationsSection } from "@/components/SettlementOperationsSection";
import { QueryState, MutationErrorNotice } from "@/components/QueryState";

export default function CashTransactionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = Number(params.id);
  const queryClient = useQueryClient();
  const [showCandidates, setShowCandidates] = useState(false);
  const [receiptSearchOpen, setReceiptSearchOpen] = useState(false);

  const txQuery = useQuery({
    queryKey: ["cash-transaction", id],
    queryFn: () => getCashTransaction(id),
  });

  const candidatesQuery = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["cash-tx-receipt-candidates", id],
    queryFn: () => getCashReceiptCandidates(id),
    enabled: showCandidates,
  });

  const linkMutation = useMutation({
    mutationFn: (receiptTxId: number) => linkCashToReceipt(id, receiptTxId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["cash-transaction", id], updated);
      queryClient.invalidateQueries({ queryKey: ["cash-tx-receipt-candidates", id] });
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkCashTransaction(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(["cash-transaction", id], updated);
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
    },
  });

  return (
    <QueryState
      query={txQuery}
      errorTitle="Nie udało się pobrać transakcji gotówkowej."
      loadingFallback={
        <div className="p-8 text-center text-gray-400 text-sm animate-pulse">
          Ładowanie…
        </div>
      }
    >
      {(tx) => {
        const title = tx.vendor_name ?? tx.description ?? `Gotówka #${tx.id}`;
        const receiptLink = tx.receipt_link ?? null;
        return (
    <div className="h-full flex flex-col pb-6">
      <MutationErrorNotice mutation={linkMutation} />
      <MutationErrorNotice mutation={unlinkMutation} />
      <PageHeader
        variant="detail"
        title={title}
        subtitle={
          <NavLink href="/cash-transactions" label="Transakcje gotówkowe" variant="back" size="xs" />
        }
      />
      <div className="flex items-center gap-4 mb-6">
        <Amount value={tx.amount} currency={tx.currency} className="text-2xl" />
        {tx.category_name && (
          <Pill variant="category-secondary" size="md">{tx.category_name}</Pill>
        )}
      </div>
      <div className="space-y-4 flex-1 min-h-0 overflow-y-auto">
        <Card padding="md" className="space-y-3">
          <SectionLabel>Dane</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-[11px] font-medium text-gray-400 uppercase">Data</span>
              <p>{isoToDisplay(tx.booking_date)}</p>
            </div>
            <div>
              <span className="text-[11px] font-medium text-gray-400 uppercase">Źródło</span>
              <p>
                <SourceBadge source={tx.source} showLabel />
              </p>
            </div>
            <div className="sm:col-span-2">
              <span className="text-[11px] font-medium text-gray-400 uppercase">Opis / sklep</span>
              <p className="text-gray-800">
                {tx.vendor_name && <span className="font-medium">{tx.vendor_name}</span>}
                {tx.vendor_name && tx.description && (
                  <span className="block text-gray-600 text-sm mt-0.5">{tx.description}</span>
                )}
                {!tx.vendor_name && (tx.description ?? "—")}
              </p>
            </div>
            <div>
              <span className="text-[11px] font-medium text-gray-400 uppercase">Kategoria</span>
              <p>
                {tx.receipt_category_name ? (
                  <span>{tx.receipt_category_name}</span>
                ) : tx.category_name ? (
                  <span>{tx.category_name}</span>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </p>
            </div>
            <div className="sm:col-span-2">
              <span className="text-[11px] font-medium text-gray-400 uppercase">Tagi</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(tx.tags ?? []).length > 0 ? (
                  tx.tags!.map((t) => (
                    <Pill key={t} variant="tag" size="sm">{t}</Pill>
                  ))
                ) : (
                  <span className="text-gray-400 text-sm">—</span>
                )}
              </div>
            </div>
          </div>
        </Card>

        <Card padding="md" className="space-y-3">
          <SectionLabel>Powiązany paragon</SectionLabel>
          {receiptLink ? (
            <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
              <Link
                href={`/receipts/${receiptLink.scan_id}`}
                className="text-xs space-y-0.5 hover:underline min-w-0"
              >
                <p className="font-medium text-accent">{receiptLink.vendor_name}</p>
                <p className="text-gray-500">
                  {isoToDisplay(receiptLink.date)} · {receiptLink.total.toFixed(2)} PLN
                </p>
                <p className="text-gray-400 font-mono text-[10px]">
                  {receiptLink.scan_filename}
                </p>
              </Link>
              <Button
                variant="danger"
                size="sm"
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate()}
                className="shrink-0"
              >
                {unlinkMutation.isPending ? "…" : "Odepnij"}
              </Button>
            </div>
          ) : showCandidates ? (
            <QueryState
              query={candidatesQuery}
              errorTitle="Nie udało się pobrać propozycji paragonów."
              loadingFallback={
                <p className="text-xs text-gray-400 animate-pulse">Szukanie…</p>
              }
            >
              {(candidates) =>
                candidates.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">
                    Nie znaleziono pasujących paragonów.
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    {candidates.map((c) => (
                      <div
                        key={c.receipt_transaction_id}
                        className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2"
                      >
                        <div className="text-xs space-y-0.5 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-gray-800 truncate">
                              {c.vendor_name}
                            </p>
                            <MatchBadge score={c.match_score} />
                          </div>
                          <p className="text-gray-500">
                            {isoToDisplay(c.date)} · {c.total.toFixed(2)} PLN
                          </p>
                          <p className="text-gray-400 font-mono text-[10px] truncate">
                            {c.scan_filename}
                          </p>
                        </div>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={linkMutation.isPending}
                          onClick={() => linkMutation.mutate(c.receipt_transaction_id)}
                          className="shrink-0"
                        >
                          {linkMutation.isPending ? "…" : "Powiąż"}
                        </Button>
                      </div>
                    ))}
                  </div>
                )
              }
            </QueryState>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowCandidates(true)}
              >
                Znajdź pasujący paragon
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setReceiptSearchOpen(true)}
              >
                Wyszukaj paragon…
              </Button>
            </div>
          )}
        </Card>

        <SettlementOperationsSection sourceType="cash" transactionId={id} />
        <LinkReceiptSearchModal
          open={receiptSearchOpen}
          onClose={() => setReceiptSearchOpen(false)}
          anchorType="cash"
          transactionId={id}
          amount={tx.amount}
          onLinked={() => {
            queryClient.invalidateQueries({ queryKey: ["cash-tx-receipt-candidates", id] });
          }}
        />
      </div>
    </div>
        );
      }}
    </QueryState>
  );
}
