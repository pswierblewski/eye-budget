"use client";

import { useEffect, useRef, useState } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  importBankCsv,
  recategorizeBankTransactions,
  listBankTransactions,
  listBankAccounts,
  saveBankTransactionCategory,
  getBankTransaction,
  getReceiptCandidates,
  linkBankToReceipt,
  unlinkBankTransaction,
  updateBankTransactionTags,
  getAllTags,
} from "@/lib/api";
import { shouldShowAiCategoryProposal } from "@/lib/bankTxCategoryListUi";
import { isoToDisplay } from "@/lib/utils";
import {
  BankTransactionListItem,
  BankTransactionDetail,
  BankImportResult,
  PaginatedResponse,
  ReceiptCandidateItem,
  BankAccountStats,
} from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { BankTransactionSplitEditor } from "@/components/BankTransactionSplitEditor";
import TagsEditor from "@/components/TagsEditor";
import { getPusher } from "@/lib/pusher";
import { Upload, ArrowRight, RefreshCw, Link2, Settings } from "lucide-react";
import { DataTable, Column } from "@/components/DataTable";
import { SettlementOperationsSection } from "@/components/SettlementOperationsSection";
import { LinkReceiptSearchModal } from "@/components/LinkReceiptSearchModal";
import Link from "next/link";
import { CandidateBar } from "@/components/BankHelpers";
import {
  MatchBadge,
  Pill,
  PageHeader,
  SectionLabel,
  NavLink,
  Button,
  Amount,
} from "@/components/ui";
import {
  QueryState,
  QueryErrorNotice,
  MutationErrorNotice,
} from "@/components/QueryState";
import { BankAccountsModal } from "@/components/BankAccountsModal";

type ExpandedRowProps = {
  tx: BankTransactionListItem;
  tagsQuery: UseQueryResult<string[], Error>;
};

function ExpandedRowContent({ tx, tagsQuery }: ExpandedRowProps) {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>(
    tx.category_id ?? undefined
  );
  const [showCandidates, setShowCandidates] = useState(false);
  const [receiptSearchOpen, setReceiptSearchOpen] = useState(false);

  const detailQuery = useQuery<BankTransactionDetail>({
    queryKey: ["bank-transaction", tx.id],
    queryFn: () => getBankTransaction(tx.id),
  });
  const detail = detailQuery.data;

  const candidatesQuery = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["bank-tx-receipt-candidates", tx.id],
    queryFn: () => getReceiptCandidates(tx.id),
    enabled: showCandidates,
  });

  const saveCategoryMutation = useMutation({
    mutationFn: (categoryId: number | null) => saveBankTransactionCategory(tx.id, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
    },
  });

  const linkMutation = useMutation({
    mutationFn: (receiptTxId: number) => linkBankToReceipt(tx.id, receiptTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["bank-tx-receipt-candidates", tx.id] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkBankTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
    },
  });

  const tagsMutation = useMutation({
    mutationFn: (tags: string[]) => updateBankTransactionTags(tx.id, tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const candidates2: Array<{ category_id: number; category_name: string; category_score: number }> =
    detail?.category_candidates ?? [];

  const receiptLink = detail?.receipt_link ?? null;

  // Pre-select the highest-scoring candidate when detail loads and no category is confirmed yet
  useEffect(() => {
    if (tx.category_id != null) return; // already confirmed — don't override
    if (candidates2.length === 0) return;
    if (selectedCategory !== undefined) return; // user already picked something
    const top = [...candidates2].sort((a, b) => b.category_score - a.category_score)[0];
    setSelectedCategory(top.category_id);
  }, [candidates2.length]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
    <QueryErrorNotice
      query={detailQuery}
      errorTitle="Nie udało się pobrać szczegółów transakcji."
    />
    <MutationErrorNotice mutation={saveCategoryMutation} />
    <MutationErrorNotice mutation={tagsMutation} />
    <MutationErrorNotice mutation={linkMutation} />
    <MutationErrorNotice mutation={unlinkMutation} />
    <div className="flex gap-8">
          {/* Left: details */}
          <div className="flex-1 space-y-1 text-xs text-gray-600">
            {tx.counterparty && (
              <div>
                <span className="font-medium text-gray-700">Kontrahent: </span>
                {tx.counterparty}
              </div>
            )}
            {detail?.counterparty_address && (
              <div>
                <span className="font-medium text-gray-700">Adres: </span>
                {detail.counterparty_address}
              </div>
            )}
            {tx.description && (
              <div>
                <span className="font-medium text-gray-700">Opis: </span>
                {tx.description}
              </div>
            )}
            {detail?.source_account && (
              <div>
                <span className="font-medium text-gray-700">Konto źródłowe: </span>
                {detail.source_account}
              </div>
            )}
            {detail?.target_account && (
              <div>
                <span className="font-medium text-gray-700">Konto docelowe: </span>
                {detail.target_account}
              </div>
            )}
            <div>
                <span className="font-medium text-gray-700">Nr referencyjny: </span>
              <span className="font-mono">{tx.reference_number}</span>
            </div>
          </div>

          {/* Middle: candidates */}
          {candidates2.length > 0 && (
            <div className="w-80 space-y-1">
              <SectionLabel className="mb-2">Propozycje kategorii</SectionLabel>
              {candidates2.map((c) => (
                <CandidateBar
                  key={c.category_id}
                  name={c.category_name}
                  score={c.category_score}
                />
              ))}
            </div>
          )}

          {/* Right: category picker + actions */}
          <div className="w-96 space-y-3">
            <div>
              <SectionLabel className="mb-1">Kategoria</SectionLabel>
              {receiptLink ? (
                /* Receipt-linked: categories derived from receipt items */
                <div className="space-y-2">
                  <div className="flex flex-col gap-1">
                    {(detail?.receipt_categories ?? []).length > 0 ? (
                      (detail?.receipt_categories ?? []).map((cat: { id: number; name: string; product_count: number }, idx: number) => (
                        <Pill
                          key={cat.id}
                          variant={idx === 0 ? "category-primary" : "category-secondary"}
                          size="sm"
                        >
                          {cat.name}
                          <span className="ml-1 text-[10px] text-gray-400">({cat.product_count})</span>
                        </Pill>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400 italic">Paragon bez potwierdzonych kategorii</span>
                    )}
                  </div>
                  <NavLink
                    href={`/receipts/${receiptLink.scan_id}`}
                    label="Zarządzaj kategoriami w paragonie"
                    variant="forward"
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              ) : (
                <CategoryDropdown
                  value={selectedCategory}
                  onChange={setSelectedCategory}
                  candidates={candidates2.map((c) => ({
                    category_id: c.category_id,
                    category_name: c.category_name,
                    category_score: c.category_score,
                  }))}
                />
              )}
            </div>
            {!receiptLink && (
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!selectedCategory || saveCategoryMutation.isPending}
                  onClick={() => saveCategoryMutation.mutate(selectedCategory ?? null)}
                  className="flex-1"
                >
                  {saveCategoryMutation.isPending ? "Zapisywanie…" : "Zapisz kategorię"}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Tags section */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <SectionLabel className="mb-2">Tagi</SectionLabel>
          <QueryState
            query={tagsQuery}
            errorTitle="Nie udało się pobrać listy tagów."
            loadingFallback={
              <p className="text-xs text-gray-400">Ładowanie tagów…</p>
            }
          >
            {(allTags) => (
              <TagsEditor
                tags={detail?.tags ?? tx.tags ?? []}
                onChange={(tags) => tagsMutation.mutate(tags)}
                allTags={allTags}
              />
            )}
          </QueryState>
        </div>

        {/* Split editor section — only when not receipt-linked */}
        {!receiptLink && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <SectionLabel className="mb-2">Podział kategorii</SectionLabel>
            <BankTransactionSplitEditor
              key={
                detail?.category_splits
                  ? detail.category_splits.map((s) => `${s.id}:${s.amount}`).join(",")
                  : "none"
              }
              txId={tx.id}
              txAmount={Math.abs(tx.amount)}
              splits={detail?.category_splits ?? null}
              onSuccess={() => {
                queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
                queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
              }}
            />
          </div>
        )}

        {/* Linked receipt section */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <SectionLabel className="mb-2">Powiązany paragon</SectionLabel>

          {receiptLink ? (
            /* Existing link */
            <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
              <Link
                href={`/receipts/${receiptLink.scan_id}`}
                className="text-xs space-y-0.5 hover:underline min-w-0"
                onClick={(e) => e.stopPropagation()}
              >
                <p className="font-medium text-accent">{receiptLink.vendor_name}</p>
                <p className="text-gray-500">
                  {isoToDisplay(receiptLink.date)} · {receiptLink.total.toFixed(2)} PLN
                </p>
                <p className="text-gray-400 font-mono">{receiptLink.scan_filename}</p>
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
                            {c.date} · {c.total.toFixed(2)} PLN
                          </p>
                          <p className="text-gray-400 font-mono text-[10px] truncate">
                            {c.scan_filename}
                          </p>
                        </div>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={linkMutation.isPending}
                          onClick={() =>
                            linkMutation.mutate(c.receipt_transaction_id)
                          }
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
                Znajdź pasujące paragony
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
    </div>

        <div
          className="mt-4 pt-4 border-t border-gray-200"
          onClick={(e) => e.stopPropagation()}
        >
          <SettlementOperationsSection sourceType="bank" transactionId={tx.id} />
        </div>

        <LinkReceiptSearchModal
          open={receiptSearchOpen}
          onClose={() => setReceiptSearchOpen(false)}
          anchorType="bank"
          transactionId={tx.id}
          amount={tx.amount}
          onLinked={() => {
            queryClient.invalidateQueries({
              queryKey: ["bank-tx-receipt-candidates", tx.id],
            });
          }}
        />
    </>
  );
}

export default function BankTransactionsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("booking_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [importResult, setImportResult] = useState<BankImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ index: number; total: number } | null>(null);
  const [categorizingDone, setCategorizingDone] = useState(false);
  const [recategorizeInfo, setRecategorizeInfo] = useState<string | null>(null);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);
  const accountFileRef = useRef<HTMLInputElement>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<number | undefined>(undefined);
  const [showAccountsModal, setShowAccountsModal] = useState(false);
  const [pendingImportAccountId, setPendingImportAccountId] = useState<number | undefined>(undefined);
  const [importMenuOpen, setImportMenuOpen] = useState(false);
  const importMenuRef = useRef<HTMLDivElement>(null);

  const accountsQuery = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: listBankAccounts,
    staleTime: 60_000,
  });

  const ensureBankTransactionsChannel = () => {
    if (channelRef.current) return channelRef.current;

    const pusher = getPusher();
    const channel = pusher.subscribe("bank-transactions");
    channelRef.current = channel;
    return channel;
  };

  // Cleanup Pusher on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unsubscribe();
      channelRef.current = null;
    };
  }, []);

  // Close the "Import CSV" account menu when clicking outside of it
  useEffect(() => {
    if (!importMenuOpen) return;
    const onDocumentMouseDown = (e: MouseEvent) => {
      if (importMenuRef.current?.contains(e.target as Node)) return;
      setImportMenuOpen(false);
    };
    document.addEventListener("mousedown", onDocumentMouseDown);
    return () => document.removeEventListener("mousedown", onDocumentMouseDown);
  }, [importMenuOpen]);

  useEffect(() => {
    const channel = ensureBankTransactionsChannel();
    const onTransactionUpdated = (payload: {
      bank_transaction_id: number;
      ai_top_candidate?: {
        category_id: number;
        category_name: string;
        category_score: number;
      } | null;
    }) => {
      queryClient.setQueryData<PaginatedResponse<BankTransactionListItem>>(
        ["bank-transactions", page, sortBy, sortDir, selectedAccountId],
        (old) => {
          if (!old) return old;

          return {
            ...old,
            items: old.items.map((item) =>
              item.id === payload.bank_transaction_id
                ? {
                    ...item,
                    ai_top_candidate: payload.ai_top_candidate ?? undefined,
                  }
                : item
            ),
          };
        }
      );
    };

    channel.bind("categorization.transaction_updated", onTransactionUpdated);

    return () => {
      channel.unbind("categorization.transaction_updated", onTransactionUpdated);
    };
  }, [page, queryClient, sortBy, sortDir, selectedAccountId]);

  const listQuery = useQuery({
    queryKey: ["bank-transactions", page, sortBy, sortDir, selectedAccountId],
    queryFn: () =>
      listBankTransactions({
        page,
        limit: PAGE_SIZE,
        sort_by: sortBy,
        sort_dir: sortDir,
        account_id: selectedAccountId,
      }),
    staleTime: 30_000,
  });

  const tagsQuery = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const saveCategoryFromListMutation = useMutation({
    mutationFn: ({ id, categoryId }: { id: number; categoryId: number }) =>
      saveBankTransactionCategory(id, categoryId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", variables.id] });
    },
  });

  const importMutation = useMutation({
    mutationFn: ({ file, accountId }: { file: File; accountId: number }) =>
      importBankCsv(file, accountId),
    onSuccess: (result) => {
      setImportResult(result);
      setImportError(null);
      setCategorizingDone(false);
      setProgress(null);
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-accounts"] });

      if (result.task_id) {
        const channel = ensureBankTransactionsChannel();

        const onProgress = (data: { task_id: string; index: number; total: number }) => {
          if (data.task_id !== result.task_id) return;
          setProgress({ index: data.index, total: data.total });
        };

        const cleanupImportHandlers = () => {
          channel.unbind("categorization.progress", onProgress);
          channel.unbind("categorization.done", onDone);
          channel.unbind("categorization.error", onError);
        };

        const onDone = (data: { task_id: string; total: number }) => {
          if (data.task_id !== result.task_id) return;
          setProgress(null);
          setCategorizingDone(true);
          cleanupImportHandlers();
          queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
        };

        const onError = (data: { task_id: string; error: string }) => {
          if (data.task_id !== result.task_id) return;
          setProgress(null);
          setImportError(`Categorization error: ${data.error}`);
          cleanupImportHandlers();
        };

        channel.bind("categorization.progress", onProgress);
        channel.bind("categorization.done", onDone);
        channel.bind("categorization.error", onError);
      }
    },
    onError: (err: Error) => {
      setImportError(err.message);
      setImportResult(null);
    },
  });

  const recategorizeMutation = useMutation({
    mutationFn: recategorizeBankTransactions,
    onSuccess: (result) => {
      if (!result.task_id || result.count === 0) {
        setRecategorizeInfo("Brak transakcji do kategoryzacji.");
        return;
      }
      setRecategorizeInfo(`Kategoryzacja w toku… (${result.count} transakcji)`);
      setProgress(null);
      setCategorizingDone(false);

      const channel = ensureBankTransactionsChannel();

      const onProgress = (data: { task_id: string; index: number; total: number }) => {
        if (data.task_id !== result.task_id) return;
        setProgress({ index: data.index, total: data.total });
      };

      const cleanupRecategorizeHandlers = () => {
        channel.unbind("categorization.progress", onProgress);
        channel.unbind("categorization.done", onDone);
        channel.unbind("categorization.error", onError);
      };

      const onDone = (data: { task_id: string; total: number }) => {
        if (data.task_id !== result.task_id) return;
        setProgress(null);
        setCategorizingDone(true);
        setRecategorizeInfo(null);
        cleanupRecategorizeHandlers();
        queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      };

      const onError = (data: { task_id: string; error: string }) => {
        if (data.task_id !== result.task_id) return;
        setProgress(null);
        setRecategorizeInfo(`Błąd kategoryzacji: ${data.error}`);
        cleanupRecategorizeHandlers();
      };

      channel.bind("categorization.progress", onProgress);
      channel.bind("categorization.done", onDone);
      channel.bind("categorization.error", onError);
    },
    onError: (err: Error) => {
      setRecategorizeInfo(`Błąd: ${err.message}`);
    },
  });

  function handleImportClick(accountId: number) {
    setImportMenuOpen(false);
    setPendingImportAccountId(accountId);
    accountFileRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || pendingImportAccountId === undefined) return;
    setImportResult(null);
    setImportError(null);
    setProgress(null);
    setCategorizingDone(false);
    importMutation.mutate({ file, accountId: pendingImportAccountId });
    e.target.value = "";
    setPendingImportAccountId(undefined);
  }

  const pct = progress ? Math.round((progress.index / progress.total) * 100) : 0;

  const columns: Column<BankTransactionListItem>[] = [
    {
      header: "Data",
      accessor: (t) => (
        <span className="font-mono text-xs text-gray-600">{isoToDisplay(t.booking_date)}</span>
      ),
      serverSortKey: "booking_date",
      className: "whitespace-nowrap",
    },
    {
      header: "Kontrahent / Opis",
      accessor: (t) => (
        <div>
          <div className="font-medium text-gray-800 truncate max-w-xs">
            {t.counterparty || "—"}
          </div>
          {t.description && (
            <div className="text-xs text-gray-400 truncate mt-0.5 max-w-xs">
              {t.description}
            </div>
          )}
        </div>
      ),
      serverSortKey: "counterparty",
    },
    {
      header: "Typ operacji",
      accessor: (t) => (
        <span className="text-gray-500 text-xs truncate max-w-[160px] block">
          {t.operation_type || "—"}
        </span>
      ),
      serverSortKey: "operation_type",
    },
    {
      header: "Kwota",
      accessor: (t) => (
      <Amount value={t.amount} currency={t.currency} />
      ),
      serverSortKey: "amount",
      className: "text-right",
    },
    {
      header: "Kategoria",
      accessor: (t) => {
        if (t.receipt_category_name) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">
                {t.receipt_category_name}
              </span>
              {(t.receipt_category_count ?? 1) > 1 && (
                <span className="text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium shrink-0">
                  +{t.receipt_category_count! - 1}
                </span>
              )}
            </div>
          );
        }
        if (t.split_category_name && (t.split_count ?? 0) >= 2) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">
                {t.split_category_name}
              </span>
              {(t.split_count ?? 1) > 1 && (
                <span className="text-[10px] bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 font-medium shrink-0">
                  +{t.split_count! - 1}
                </span>
              )}
            </div>
          );
        }
        if (shouldShowAiCategoryProposal(t) && t.ai_top_candidate) {
          const aiTopCandidate = t.ai_top_candidate;
          const isSavingCurrentRow =
            saveCategoryFromListMutation.isPending &&
            saveCategoryFromListMutation.variables?.id === t.id;

          return (
            <div className="flex max-w-[220px] flex-col gap-1.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-medium text-gray-700">
                  {aiTopCandidate.category_name}
                </span>
                <span className="text-xs text-gray-400">
                  {aiTopCandidate.category_score.toLocaleString("pl-PL", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                disabled={isSavingCurrentRow}
                onClick={(e) => {
                  e.stopPropagation();
                  saveCategoryFromListMutation.mutate({
                    id: t.id,
                    categoryId: aiTopCandidate.category_id,
                  });
                }}
              >
                {isSavingCurrentRow ? "Zapisywanie…" : "Zapisz kategorię"}
              </Button>
            </div>
          );
        }
        return t.category_name ? (
          <span className="text-gray-700 text-xs truncate max-w-[160px] block">
            {t.category_name}
          </span>
        ) : (
          <span className="text-gray-400 italic text-xs">Nie przypisano</span>
        );
      },
      serverSortKey: "category_name",
    },
    {
      header: "Tagi",
      accessor: (t) =>
        t.tags && t.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {t.tags.map((tag) => (
              <Pill key={tag} variant="tag" size="sm">{tag}</Pill>
            ))}
          </div>
        ) : null,
    },
    {
      header: "",
      accessor: (t) =>
        t.settlement_group_id != null ? (
          <Link
            href={`/settlement-groups/${t.settlement_group_id}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 max-w-[10rem] p-1 rounded hover:bg-violet-50 text-violet-600 min-w-0"
            title={
              t.settlement_group_title?.trim()
                ? t.settlement_group_title
                : "Powiązane operacje"
            }
          >
            <Link2 className="h-4 w-4 shrink-0" />
            {t.settlement_group_title?.trim() ? (
              <span className="truncate text-xs font-medium text-violet-800">
                {t.settlement_group_title}
              </span>
            ) : null}
          </Link>
        ) : null,
      className: "w-36",
    },
    {
      header: "",
      accessor: (t) => (
        <Link
          href={`/bank-transactions/${t.id}`}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center justify-center p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-accent transition-colors"
          title="Otwórz szczegóły"
        >
          <ArrowRight className="h-4 w-4" />
        </Link>
      ),
      className: "w-8 text-center",
    },
  ];

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <PageHeader
        title="Transakcje bankowe"
        variant="list"
        actions={
          <div className="flex items-center gap-3">
          {/* Import feedback */}
          {importMutation.isPending && (
            <span className="text-sm text-gray-500">Importowanie…</span>
          )}
          {importResult && !importMutation.isPending && (
            <div className="flex flex-col gap-1 text-sm">
              <span className="text-gray-700">
                ✓ Zaimportowano: {importResult.imported}, duplikaty:{" "}
                {importResult.duplicates}
                {(importResult.auto_linked ?? 0) > 0 && (
                  <>, powiązano paragonów: {importResult.auto_linked}</>
                )}
                {(importResult.needs_manual_link ?? 0) > 0 && (
                  <>, wymaga ręcznego powiązania: {importResult.needs_manual_link}</>
                )}
              </span>
              {progress && (
                <div className="flex flex-col gap-0.5 min-w-[220px]">
                  <span className="text-xs text-accent animate-pulse">
                    Kategoryzacja… {progress.index}/{progress.total}
                  </span>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full bg-accent transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )}
              {categorizingDone && !progress && (
                <span className="text-xs text-green-600">
                  ✓ Kategoryzacja zakończona
                </span>
              )}
            </div>
          )}
          {importError && (
            <span className="text-sm text-red-600">Błąd: {importError}</span>
          )}

          {/* Recategorize feedback */}
          {recategorizeInfo && (
            <span className={`text-sm ${recategorizeInfo.startsWith("Błąd") ? "text-red-600" : "text-gray-500"}`}>
              {recategorizeInfo}
            </span>
          )}

          {/* CSV upload button */}
          <input
            ref={accountFileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            variant="secondary"
            size="md"
            onClick={() => {
              setRecategorizeInfo(null);
              recategorizeMutation.mutate();
            }}
            disabled={recategorizeMutation.isPending || !!progress}
            title="Ponów kategoryzację: transakcje bez zapisanej kategorii i bez paragonu — bez propozycji LLM albo z propozycją (jak przycisk Zapisz kategorię w wierszu)"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${recategorizeMutation.isPending ? "animate-spin" : ""}`} />
            Ponów kategoryzację
          </Button>
          <Button
            variant="secondary"
            size="md"
            onClick={() => setShowAccountsModal(true)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Zarządzaj kontami
          </Button>
          {accountsQuery.data && accountsQuery.data.length > 0 ? (
            <div className="relative group">
              <Button
                variant="primary"
                size="md"
                disabled={importMutation.isPending}
              >
                <Upload className="h-4 w-4 mr-2" />
                Import CSV
              </Button>
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 hidden group-hover:block min-w-[180px]">
                {accountsQuery.data.map((acc: BankAccountStats) => (
                  <button
                    key={acc.id}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                    onClick={() => handleImportClick(acc.id)}
                  >
                    {acc.name}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <Button
              variant="primary"
              size="md"
              disabled
              title="Najpierw dodaj konto bankowe"
            >
              <Upload className="h-4 w-4 mr-2" />
              Import CSV
            </Button>
          )}
        </div>
        }
      />

      {/* Account summary cards */}
      {accountsQuery.data && accountsQuery.data.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {accountsQuery.data.map((acc: BankAccountStats) => (
            <button
              key={acc.id}
              onClick={() => {
                setSelectedAccountId(selectedAccountId === acc.id ? undefined : acc.id);
                setPage(1);
              }}
              className={`flex flex-col gap-0.5 rounded-lg border px-4 py-3 text-left transition-colors min-w-[160px] ${
                selectedAccountId === acc.id
                  ? "border-blue-400 bg-blue-50"
                  : "border-gray-200 bg-white hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                    {
                      blue: "bg-blue-500",
                      green: "bg-green-500",
                      purple: "bg-purple-500",
                      orange: "bg-orange-500",
                      red: "bg-red-500",
                    }[acc.color] ?? "bg-gray-400"
                  }`}
                />
                <span className="text-sm font-semibold text-gray-800 truncate">{acc.name}</span>
              </div>
              <div className="text-xs text-green-600">+{acc.total_income.toFixed(0)} PLN</div>
              <div className="text-xs text-red-600">{acc.total_expense.toFixed(0)} PLN</div>
              <div className="text-xs text-gray-400">{acc.transaction_count} transakcji</div>
            </button>
          ))}
          {selectedAccountId !== undefined && (
            <button
              onClick={() => { setSelectedAccountId(undefined); setPage(1); }}
              className="self-start text-xs text-gray-500 hover:underline mt-1 px-2"
            >
              Pokaż wszystkie
            </button>
          )}
        </div>
      )}

      <BankAccountsModal
        open={showAccountsModal}
        onClose={() => {
          setShowAccountsModal(false);
          queryClient.invalidateQueries({ queryKey: ["bank-accounts"] });
        }}
      />

      <MutationErrorNotice mutation={saveCategoryFromListMutation} />
      <MutationErrorNotice mutation={importMutation} />
      <MutationErrorNotice mutation={recategorizeMutation} />

      {/* Table */}
      <QueryState
        query={listQuery}
        errorTitle="Nie udało się pobrać transakcji bankowych."
        loadingFallback={
          <div className="p-8 text-center text-gray-400 text-sm">Ładowanie…</div>
        }
      >
        {(data) => (
          <DataTable
            columns={columns}
            rows={data.items}
            emptyMessage="Brak transakcji. Zaimportuj plik CSV z banku."
            renderExpandedRow={(tx) => (
              <ExpandedRowContent tx={tx} tagsQuery={tagsQuery} />
            )}
            className="flex-1 min-h-0"
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total: data.total,
              onPageChange: setPage,
              sortBy,
              sortDir,
              onSortChange: (key, dir) => {
                setSortBy(key);
                setSortDir(dir);
                setPage(1);
              },
            }}
          />
        )}
      </QueryState>
    </div>
  );
}
