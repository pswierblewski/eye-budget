"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  getBankTransaction,
  listBankTransactions,
  saveBankTransactionCategory,
  getReceiptCandidates,
  linkBankToReceipt,
  unlinkBankTransaction,
  updateBankTransactionTags,
  deleteBankTransaction,
  getAllTags,
} from "@/lib/api";
import { ReceiptCandidateItem } from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import TagsEditor from "@/components/TagsEditor";
import { CandidateBar } from "@/components/BankHelpers";
import { isoToDisplay } from "@/lib/utils";
import {
  MatchBadge,
  Pill,
  PageHeader,
  SectionLabel,
  NavLink,
  Button,
  Amount,
  Card,
  PrevNextNav,
  ThreeDotsMenu,
  ConfirmDeleteModal,
} from "@/components/ui";

// ─── Detail field ───────────────────────────────────────────────────
function Field({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
        {label}
      </span>
      <span className="text-sm text-gray-800 break-all">{value}</span>
    </div>
  );
}

export default function BankTransactionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const txId = Number(params.id);
  const queryClient = useQueryClient();
  const router = useRouter();

  // ── Main data ────────────────────────────────────────────────────
  const { data: tx, isLoading } = useQuery({
    queryKey: ["bank-transaction", txId],
    queryFn: () => getBankTransaction(txId),
  });

  // ── Navigation ──────────────────────────────────────────────────
  const { data: allTxs } = useQuery({
    queryKey: ["bank-transactions", "all", "nav"],
    queryFn: () => listBankTransactions({ limit: 2000, sort_by: "booking_date", sort_dir: "desc" }),
  });

  const { prevId, nextId } = (() => {
    if (!allTxs) return { prevId: null, nextId: null };
    const ids = allTxs.items.map((t) => t.id);
    const idx = ids.indexOf(txId);
    return {
      prevId: idx > 0 ? ids[idx - 1] : null,
      nextId: idx !== -1 && idx < ids.length - 1 ? ids[idx + 1] : null,
    };
  })();

  // ── Tags all ────────────────────────────────────────────────────
  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  // ── Category state ───────────────────────────────────────────────
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>(
    tx?.category_id ?? undefined
  );

  useEffect(() => {
    if (!tx) return;
    if (tx.category_id != null) {
      setSelectedCategory(tx.category_id);
      return;
    }
    const candidates = tx.category_candidates ?? [];
    if (candidates.length === 0) return;
    const top = [...candidates].sort((a, b) => b.category_score - a.category_score)[0];
    setSelectedCategory(top.category_id);
  }, [tx?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Receipt linking state ────────────────────────────────────────
  const [showCandidates, setShowCandidates] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // ── Mutations ───────────────────────────────────────────────────
  const saveCategoryMutation = useMutation({
    mutationFn: (categoryId: number | null) => saveBankTransactionCategory(txId, categoryId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["bank-transaction", txId], updated);
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
    },
  });

  const tagsMutation = useMutation({
    mutationFn: (tags: string[]) => updateBankTransactionTags(txId, tags),
    onSuccess: (updated) => {
      queryClient.setQueryData(["bank-transaction", txId], updated);
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const { data: candidates = [], isFetching: candidatesLoading } = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["bank-tx-receipt-candidates", txId],
    queryFn: () => getReceiptCandidates(txId),
    enabled: showCandidates,
  });

  const linkMutation = useMutation({
    mutationFn: (receiptTxId: number) => linkBankToReceipt(txId, receiptTxId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["bank-transaction", txId], updated);
      queryClient.invalidateQueries({ queryKey: ["bank-tx-receipt-candidates", txId] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkBankTransaction(txId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["bank-transaction", txId], updated);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteBankTransaction(txId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      router.push("/bank-transactions");
    },
  });

  // ── Loading / error states ───────────────────────────────────────
  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-400 text-sm animate-pulse">
        Ładowanie…
      </div>
    );
  }

  if (!tx) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-500 text-sm">Nie znaleziono transakcji.</p>
        <Link href="/bank-transactions" className="mt-4 inline-block text-accent text-sm hover:underline">
          ← Wróć do listy
        </Link>
      </div>
    );
  }

  const candidates2 = tx.category_candidates ?? [];
  const receiptLink = tx.receipt_link ?? null;

  return (
    <div className="h-full flex flex-col">
      {/* ConfirmDeleteModal */}
      <ConfirmDeleteModal
        open={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Usuń transakcję"
        description="Transakcja zostanie trwale usunięta."
        loading={deleteMutation.isPending}
      />

      {/* Top bar */}
      <PageHeader
        variant="detail"
        title={tx.counterparty ?? tx.description ?? `#${tx.id}`}
        subtitle={
          <NavLink href="/bank-transactions" label="Transakcje bankowe" variant="back" size="xs" />
        }
        actions={
          <div className="flex items-center gap-2">
            <PrevNextNav
              hasPrev={!!prevId}
              hasNext={!!nextId}
              onPrev={() => prevId && router.push(`/bank-transactions/${prevId}`)}
              onNext={() => nextId && router.push(`/bank-transactions/${nextId}`)}
            />
            <ThreeDotsMenu
              variant="outlined"
              items={[
                { label: "Usuń transakcję", variant: "danger", onClick: () => setShowDeleteModal(true) },
              ]}
            />
          </div>
        }
      />

      {/* ── Summary row ──────────────────────────────────────────── */}
      <div className="flex items-center gap-4 mb-6">
        <Amount value={tx.amount} currency={tx.currency} className="text-2xl" />
        {tx.category_name && (
          <Pill variant="category-secondary" size="md">{tx.category_name}</Pill>
        )}
      </div>

      {/* ── Main grid ─────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-4 pb-6">
        {/* Details card */}
        <Card padding="md" className="space-y-3">
          <SectionLabel>Szczegóły transakcji</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Field label="Data księgowania" value={isoToDisplay(tx.booking_date)} />
            {tx.value_date && <Field label="Data waluty" value={isoToDisplay(tx.value_date)} />}
            {tx.counterparty && <Field label="Kontrahent" value={tx.counterparty} />}
            {tx.counterparty_address && (
              <Field label="Adres kontrahenta" value={tx.counterparty_address} />
            )}
            {tx.description && <Field label="Opis" value={tx.description} />}
            {tx.operation_type && <Field label="Typ operacji" value={tx.operation_type} />}
            {tx.source_account && <Field label="Konto źródłowe" value={tx.source_account} />}
            {tx.target_account && <Field label="Konto docelowe" value={tx.target_account} />}
            <Field label="Waluta" value={tx.currency} />
            <Field
              label="Nr referencyjny"
              value={
                <span className="font-mono text-xs">{tx.reference_number}</span>
              }
            />
          </div>
        </Card>
        {/* Category card */}
        <Card padding="md" className="space-y-3">
          <SectionLabel>Kategoria</SectionLabel>

          {receiptLink ? (
            /* Receipt-linked: categories come from receipt items */
            <div className="space-y-3">
              <div className="flex flex-col gap-1.5">
                {(tx.receipt_categories ?? []).length > 0 ? (
                  (tx.receipt_categories ?? []).map((cat, idx) => (
                    <Pill
                      key={cat.id}
                      variant={idx === 0 ? "category-primary" : "category-secondary"}
                      size="md"
                    >
                      {cat.name}
                      <span className="ml-1.5 text-xs text-gray-400">({cat.product_count} prod.)</span>
                    </Pill>
                  ))
                ) : (
                  <p className="text-sm text-gray-400 italic">Paragon bez potwierdzonych kategorii</p>
                )}
              </div>
              <NavLink
                href={`/receipts/${receiptLink.scan_id}`}
                label="Zarządzaj kategoriami w paragonie"
                variant="forward"
              />
            </div>
          ) : (
            <>
              {candidates2.length > 0 && (
                <div className="space-y-1.5 mb-3">
                  <p className="text-xs text-gray-400 mb-1">Propozycje AI</p>
                  {[...candidates2]
                    .sort((a, b) => b.category_score - a.category_score)
                    .map((c) => (
                      <CandidateBar
                        key={c.category_id}
                        name={c.category_name}
                        score={c.category_score}
                      />
                    ))}
                </div>
              )}

              <div className="flex items-end gap-3">
                <div className="flex-1 max-w-sm">
                  <CategoryDropdown
                    value={selectedCategory}
                    onChange={setSelectedCategory}
                    candidates={candidates2.map((c) => ({
                      category_id: c.category_id,
                      category_name: c.category_name,
                      category_score: c.category_score,
                    }))}
                  />
                </div>
                <Button
                  variant="primary"
                  size="md"
                  disabled={!selectedCategory || saveCategoryMutation.isPending}
                  onClick={() => selectedCategory && saveCategoryMutation.mutate(selectedCategory)}
                >
                  {saveCategoryMutation.isPending ? "Zapisywanie…" : "Zapisz kategorię"}
                </Button>
              </div>
            </>
          )}
        </Card>
        {/* Tags card */}
        <Card padding="md" className="space-y-3">
          <SectionLabel>Tagi</SectionLabel>
          <TagsEditor
            tags={tx.tags ?? []}
            onChange={(tags) => tagsMutation.mutate(tags)}
            allTags={allTags}
          />
        </Card>
        {/* Receipt link card */}
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
            candidatesLoading ? (
              <p className="text-xs text-gray-400 animate-pulse">Szukanie…</p>
            ) : candidates.length === 0 ? (
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
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowCandidates(true)}
            >
              Znajdź pasujące paragony
            </Button>
          )}
        </Card>
      </div>
    </div>
  );
}
