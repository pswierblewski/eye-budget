"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getCashTransaction } from "@/lib/api";
import { isoToDisplay } from "@/lib/utils";
import {
  PageHeader,
  NavLink,
  Amount,
  Card,
  SectionLabel,
  Pill,
  SourceBadge,
} from "@/components/ui";
import { SettlementOperationsSection } from "@/components/SettlementOperationsSection";
import { QueryState } from "@/components/QueryState";

export default function CashTransactionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = Number(params.id);
  const txQuery = useQuery({
    queryKey: ["cash-transaction", id],
    queryFn: () => getCashTransaction(id),
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
        return (
    <div className="h-full flex flex-col pb-6">
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
        <SettlementOperationsSection sourceType="cash" transactionId={id} />
      </div>
    </div>
        );
      }}
    </QueryState>
  );
}
